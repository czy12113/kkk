#!/usr/bin/env python3
"""
雷达数据串口转发节点
功能：订阅雷达的/scan话题，提取关键方向的距离数据，通过串口发送到飞控
架构：雷达 -> RDK X5 (本节点) -> 串口 -> 飞控
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
import serial
import math
import time
import threading
import glob
from ..protocol import FlightControllerProtocol

class LidarSerialBridge(Node):
    def __init__(self):
        super().__init__('lidar_serial_bridge')
        
        # 声明参数
        self.declare_parameter('serial_port', '/dev/ttyCH343USB0')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('send_rate', 10.0)  # Hz
        self.declare_parameter('data_format', 'directions_8')  # directions_8, nearest, full
        self.declare_parameter('enable_heartbeat', True)  # 心跳包
        self.declare_parameter('max_distance', 12.0)  # 最大有效距离（米）
        
        # 获取参数
        self.serial_port = self.get_parameter('serial_port').value
        self.baudrate = self.get_parameter('baudrate').value
        self.send_rate = self.get_parameter('send_rate').value
        self.data_format = self.get_parameter('data_format').value
        self.enable_heartbeat = self.get_parameter('enable_heartbeat').value
        self.max_distance = self.get_parameter('max_distance').value
        
        # 数据缓存和状态
        self.latest_scan = None
        self.last_send_time = time.time()
        self.last_heartbeat_time = time.time()
        self.packet_count = 0
        self.error_count = 0
        self.scan_count = 0
        self.serial_lock = threading.Lock()
        
        # 初始化串口
        self.ser = None
        self.init_serial()
        
        # 订阅雷达话题
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10
        )
        
        # 创建定时器用于心跳和状态监控
        if self.enable_heartbeat:
            self.heartbeat_timer = self.create_timer(1.0, self.send_heartbeat)
        
        self.status_timer = self.create_timer(5.0, self.print_status)
        
        self.get_logger().info('=' * 60)
        self.get_logger().info('雷达串口桥接节点已启动')
        self.get_logger().info(f'串口设备: {self.serial_port} @ {self.baudrate} bps')
        self.get_logger().info(f'数据格式: {self.data_format}')
        self.get_logger().info(f'发送频率: {self.send_rate} Hz')
        self.get_logger().info(f'最大距离: {self.max_distance} m')
        self.get_logger().info(f'心跳包: {"启用" if self.enable_heartbeat else "禁用"}')
        self.get_logger().info('=' * 60)
    
    def init_serial(self):
        """初始化串口连接，自动扫描板载串口（排除雷达占用的 ttyCH343USB*）"""
        requested_port = str(self.serial_port).strip()
        seen = set()
        candidate_ports = []
        # 优先用户指定端口，再兜底扫描板载串口
        for p in ([requested_port] +
                  sorted(glob.glob('/dev/ttyS[1-9]')) +
                  sorted(glob.glob('/dev/ttyAMA*')) +
                  sorted(glob.glob('/dev/ttyUSB*'))):
            if p and p not in seen:
                seen.add(p)
                candidate_ports.append(p)

        last_exc = None
        for port in candidate_ports:
            try:
                self.ser = serial.Serial(
                    port=port,
                    baudrate=self.baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1,
                    write_timeout=1
                )
                self.serial_port = port
                self.get_logger().info(f'✓ 串口已打开: {self.serial_port}')
                # 清空缓冲区，避免刚插拔的“脏数据”
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                return
            except Exception as e:
                last_exc = e
                self.get_logger().warn(f'串口打开失败 {port}: {e}')

        self.get_logger().error(f'✗ 无法打开串口。候选端口: {candidate_ports}')
        self.get_logger().error(f'最后一个错误: {last_exc}')
        self.get_logger().warn('提示: 请检查串口设备是否存在，权限是否正确')
        self.get_logger().warn('      可以运行: ls -l /dev/tty* 查看可用串口')
        self.ser = None
    
    def send_heartbeat(self):
        """发送心跳包到飞控"""
        if self.ser is None or not self.ser.is_open:
            return
        
        # 心跳包：飞控协议格式，DATA为空（LEN=0）
        data = bytearray([0xAA, 0xFF, 0xFF, 0x00])
        sum_check, add_check = FlightControllerProtocol.calculate_checksums(data)
        data.extend([sum_check, add_check])
        
        try:
            with self.serial_lock:
                self.ser.write(data)
        except Exception as e:
            self.get_logger().warn(f'心跳包发送失败: {e}')
    
    def print_status(self):
        """打印运行状态"""
        serial_ok = self.ser is not None and self.ser.is_open
        success_rate = ((self.packet_count - self.error_count) / self.packet_count * 100) if self.packet_count > 0 else 0.0
        self.get_logger().info(
            f'状态: 串口{"✓" if serial_ok else "✗"} | '
            f'收到scan {self.scan_count}帧 | '
            f'已发送 {self.packet_count}包 | '
            f'错误 {self.error_count}次 | '
            f'成功率 {success_rate:.1f}%'
        )
    
    def scan_callback(self, msg):
        """接收雷达扫描数据"""
        self.latest_scan = msg
        self.scan_count += 1
        
        # 控制发送频率
        current_time = time.time()
        if current_time - self.last_send_time >= 1.0 / self.send_rate:
            self.process_and_send()
            self.last_send_time = current_time
    
    def process_and_send(self):
        """处理雷达数据并发送"""
        if self.latest_scan is None or self.ser is None or not self.ser.is_open:
            return
        
        if self.data_format == 'directions_8':
            self.send_8_directions()
        elif self.data_format == 'nearest':
            self.send_nearest_obstacle()
        elif self.data_format == 'full':
            self.send_full_scan()
    
    def send_8_directions(self):
        """发送8个方向的距离数据（飞控协议格式）"""
        scan = self.latest_scan
        angles = [0, 45, 90, 135, 180, 225, 270, 315]
        measurements = []
        for angle_deg in angles:
            dist_m = self.get_distance_at_angle(scan, angle_deg)
            dist_cm = int(dist_m * 100) if dist_m > 0 else FlightControllerProtocol.INVALID_DISTANCE
            measurements.append((FlightControllerProtocol.DIRECTION_HORIZONTAL, angle_deg, dist_cm))

        data = FlightControllerProtocol.pack_multiple_directions(measurements)
        try:
            with self.serial_lock:
                self.ser.write(data)
            self.packet_count += 1
            self.get_logger().debug(f'[{self.packet_count}] 8方向飞控协议: {len(data)}字节')
        except Exception as e:
            self.error_count += 1
            self.get_logger().error(f'串口发送失败 [{self.error_count}]: {e}')
            if self.error_count % 10 == 0:
                self.reconnect_serial()
    
    def send_nearest_obstacle(self):
        """发送最近障碍物的角度和距离"""
        scan = self.latest_scan
        
        # 找到最近的有效距离
        min_distance = float('inf')
        min_angle = 0.0
        
        for i, distance in enumerate(scan.ranges):
            if scan.range_min < distance < scan.range_max:
                if distance < min_distance:
                    min_distance = distance
                    min_angle = scan.angle_min + i * scan.angle_increment
        
        # 转换角度为度
        angle_deg = math.degrees(min_angle)
        if angle_deg < 0:
            angle_deg += 360
        
        # 构建数据包
        # 格式: 帧头(2) + 长度(1,=6) + 角度(2) + 距离(4) + 校验和(1) + 帧尾(2)
        data = bytearray()
        data.append(0xAA)  # 帧头1
        data.append(0x55)  # 帧头2
        data.append(6)     # 数据长度（2+4）
        
        # 角度（uint16，0-360度，精度0.1度）
        angle_int = int(angle_deg * 10) & 0xFFFF
        data.extend(struct.pack('<H', angle_int))
        
        # 距离（float，米）
        data.extend(struct.pack('<f', min_distance if min_distance != float('inf') else 0.0))
        
        # 校验和（对角度+距离6字节求和）
        checksum = sum(data[3:]) & 0xFF
        data.append(checksum)
        
        # 帧尾
        data.append(0x0D)
        data.append(0x0A)
        
        # 发送
        try:
            with self.serial_lock:
                self.ser.write(data)
            self.packet_count += 1
            self.get_logger().debug(
                f'[{self.packet_count}] 最近障碍物: 角度={angle_deg:.1f}°, 距离={min_distance:.2f}m'
            )
        except Exception as e:
            self.error_count += 1
            self.get_logger().error(f'串口发送失败 [{self.error_count}]: {e}')
            if self.error_count % 10 == 0:
                self.reconnect_serial()
    
    def send_full_scan(self):
        """发送完整扫描数据（数据量大）"""
        scan = self.latest_scan
        
        # 简化：每隔10度发送一个点
        step = 10  # 度
        
        data = bytearray()
        data.append(0xAA)  # 帧头1
        data.append(0x55)  # 帧头2
        
        points_data = bytearray()
        point_count = 0
        
        for angle_deg in range(0, 360, step):
            distance = self.get_distance_at_angle(scan, angle_deg)
            if distance > 0:
                # 角度（uint16）+ 距离（float）
                points_data.extend(struct.pack('<H', angle_deg * 10))
                points_data.extend(struct.pack('<f', distance))
                point_count += 1
        
        # 数据长度
        data.append(len(points_data) & 0xFF)
        data.extend(points_data)
        
        # 校验和
        checksum = sum(data[3:]) & 0xFF
        data.append(checksum)
        
        # 帧尾
        data.append(0x0D)
        data.append(0x0A)
        
        # 发送
        try:
            with self.serial_lock:
                self.ser.write(data)
            self.packet_count += 1
            self.get_logger().debug(f'[{self.packet_count}] 完整扫描: {point_count}个点')
        except Exception as e:
            self.error_count += 1
            self.get_logger().error(f'串口发送失败 [{self.error_count}]: {e}')
            if self.error_count % 10 == 0:
                self.reconnect_serial()
    
    def get_distance_at_angle(self, scan, angle_deg):
        """获取指定角度的距离（带平均滤波）"""
        # 转换角度为弧度
        angle_rad = math.radians(angle_deg)
        
        # 计算中心索引
        center_index = int((angle_rad - scan.angle_min) / scan.angle_increment)
        
        # 取周围5个点的平均值（简单滤波）
        valid_distances = []
        for offset in range(-2, 3):
            index = center_index + offset
            if 0 <= index < len(scan.ranges):
                distance = scan.ranges[index]
                # 检查有效性
                if scan.range_min < distance < min(scan.range_max, self.max_distance):
                    valid_distances.append(distance)
        
        if valid_distances:
            return sum(valid_distances) / len(valid_distances)
        
        return 0.0  # 无效距离返回0
    
    def reconnect_serial(self):
        """重新连接串口"""
        try:
            if self.ser is not None and self.ser.is_open:
                self.ser.close()
            time.sleep(0.5)
            self.init_serial()
        except Exception as e:
            self.get_logger().error(f'重连失败: {e}')
    
    def destroy_node(self):
        """清理资源"""
        self.get_logger().info('正在关闭节点...')
        if self.ser is not None and self.ser.is_open:
            with self.serial_lock:
                self.ser.close()
            self.get_logger().info('✓ 串口已关闭')
        self.get_logger().info(f'总计发送: {self.packet_count} 包, 错误: {self.error_count} 次')
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = LidarSerialBridge()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
