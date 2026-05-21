#!/usr/bin/env python3
"""
雷达数据转飞控协议桥接节点
将雷达扫描数据转换为飞控协议格式并通过串口发送
支持定时发送和文本信息输出
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
import serial
import math
import time
from typing import List, Tuple
import glob
import re
from ..protocol import FlightControllerProtocol


class LidarFCBridge(Node):
    """雷达到飞控协议桥接节点"""
    
    def __init__(self):
        super().__init__('lidar_fc_bridge')
        
        # 声明参数
        self.declare_parameter('serial_port', '/dev/ttyCH343USB0')
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('num_directions', 8)  # 发送方向数：8或36
        self.declare_parameter('max_distance_m', 12.0)  # 最大有效距离(米)
        self.declare_parameter('min_distance_m', 0.1)  # 最小有效距离(米)
        self.declare_parameter('send_interval', 2.0)  # 发送间隔(秒)
        self.declare_parameter('send_text_info', True)  # 是否发送文本信息
        
        # 获取参数
        self.serial_port = self.get_parameter('serial_port').value
        self.baud_rate = self.get_parameter('baud_rate').value
        self.num_directions = self.get_parameter('num_directions').value
        self.max_distance_m = self.get_parameter('max_distance_m').value
        self.min_distance_m = self.get_parameter('min_distance_m').value
        self.send_interval = self.get_parameter('send_interval').value
        self.send_text_info = self.get_parameter('send_text_info').value
        
        # 用于控制发送频率
        self.last_send_time = 0.0
        self.latest_scan = None
        
        # 初始化串口
        requested_port = str(self.serial_port).strip()
        candidate_ports = []
        ch343_match = re.match(r'^/dev/ttyCH343USB(\d+)$', requested_port)
        if ch343_match:
            candidate_ports.extend(sorted(glob.glob('/dev/ttyCH343USB*')))
        candidate_ports.append(requested_port)
        if not ch343_match:
            candidate_ports.extend(sorted(glob.glob('/dev/ttyUSB*')))
            candidate_ports.extend(sorted(glob.glob('/dev/ttyACM*')))

        seen = set()
        candidate_ports = [p for p in candidate_ports if p and not (p in seen or seen.add(p))]

        last_exc = None
        for port in candidate_ports:
            try:
                self.serial = serial.Serial(
                    port=port,
                    baudrate=self.baud_rate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1
                )
                self.serial_port = port
                self.get_logger().info(f'串口 {self.serial_port} 打开成功，波特率: {self.baud_rate}')
                break
            except Exception as e:
                last_exc = e
                self.get_logger().warn(f'串口打开失败 {port}: {e}')
        else:
            self.get_logger().error(f'✗ 无法打开串口。候选端口: {candidate_ports}')
            self.get_logger().error(f'最后一个错误: {last_exc}')
            raise
        
        # 订阅雷达话题
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10
        )
        
        # 创建定时器，按照设定的间隔发送数据
        self.timer = self.create_timer(self.send_interval, self.send_data)
        
        self.get_logger().info(f'开始监听 /scan 话题')
        self.get_logger().info(f'发送方向数: {self.num_directions}')
        self.get_logger().info(f'发送间隔: {self.send_interval}秒')
        self.get_logger().info(f'有效距离范围: {self.min_distance_m}m - {self.max_distance_m}m')
        
        # 统计信息
        self.frame_count = 0
        
    def scan_callback(self, msg: LaserScan):
        """接收雷达扫描数据，保存最新的一帧"""
        self.latest_scan = msg
    
    def send_data(self):
        """定时发送数据"""
        if self.latest_scan is None:
            self.get_logger().warn('还没有接收到雷达数据')
            return
        
        try:
            # 提取指定方向的距离数据
            measurements = self.extract_directions(self.latest_scan)
            
            # 1. 发送二进制协议数据（给飞控用）
            frame_data = FlightControllerProtocol.pack_multiple_directions(measurements)
            self.serial.write(frame_data)
            
            # 2. 发送文本信息（方便人类阅读）
            if self.send_text_info:
                text_info = self.format_text_info(measurements, frame_data)
                self.serial.write(text_info.encode('utf-8'))
            
            self.frame_count += 1
            self.get_logger().info(
                f'已发送第 {self.frame_count} 帧：'
                f'{len(measurements)} 个方向，'
                f'协议数据 {len(frame_data)} 字节'
            )
                
        except Exception as e:
            self.get_logger().error(f'数据处理错误: {e}')
    
    def format_text_info(self, measurements: List[Tuple[int, int, int]], frame_data: bytes) -> str:
        """
        格式化文本信息
        
        Returns:
            格式化的文本字符串
        """
        lines = []
        
        # 第一行：十六进制数据
        hex_str = ' '.join(f'{b:02X}' for b in frame_data)
        lines.append(f"\n[HEX] {hex_str}\n")
        
        # 后续行：每个方向的详细信息
        lines.append("=" * 60)
        lines.append(f"{'Direction':<12} {'Angle':<8} {'Dist(cm)':<12} {'Dist(m)':<10}")
        lines.append("-" * 60)
        
        direction_names = {
            0: "Forward",
            45: "Fwd-Right",
            90: "Right",
            135: "Back-Right",
            180: "Backward",
            225: "Back-Left",
            270: "Left",
            315: "Fwd-Left"
        }
        
        for direction, angle, distance_cm in measurements:
            # 获取方向名称
            dir_name = direction_names.get(angle, f"{angle}°")
            
            # 格式化距离
            if distance_cm == FlightControllerProtocol.INVALID_DISTANCE:
                dist_str = "INVALID"
                dist_m_str = "---"
            else:
                dist_str = f"{distance_cm}"
                dist_m_str = f"{distance_cm/100:.2f}"
            
            lines.append(f"{dir_name:<12} {angle:>3}deg    {dist_str:<12} {dist_m_str:<10}")
        
        lines.append("=" * 60)
        lines.append(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("\n")
        
        return '\n'.join(lines)
    
    def extract_directions(self, msg: LaserScan) -> List[Tuple[int, int, int]]:
        """
        从雷达扫描数据中提取指定方向的距离
        
        Returns:
            [(direction, angle, distance_cm), ...]
        """
        measurements = []
        angle_step = 360 // self.num_directions
        
        for i in range(self.num_directions):
            target_angle = i * angle_step
            distance_m = self.get_distance_at_angle(msg, target_angle)
            
            # 转换为厘米
            if distance_m is not None:
                distance_cm = int(distance_m * 100)
            else:
                distance_cm = FlightControllerProtocol.INVALID_DISTANCE
            
            measurements.append((
                FlightControllerProtocol.DIRECTION_HORIZONTAL,
                target_angle,
                distance_cm
            ))
        
        return measurements
    
    def get_distance_at_angle(self, msg: LaserScan, target_angle_deg: float) -> float:
        """
        获取指定角度的距离值
        
        Args:
            msg: LaserScan消息
            target_angle_deg: 目标角度(度)，0为前方，顺时针
            
        Returns:
            距离(米)，如果无效返回None
        """
        # 将目标角度转换为弧度
        target_angle_rad = math.radians(target_angle_deg)
        
        # 计算对应的索引
        # LaserScan的angle_min通常是0，angle_max是2π
        if target_angle_rad < msg.angle_min or target_angle_rad > msg.angle_max:
            return None
        
        index = int((target_angle_rad - msg.angle_min) / msg.angle_increment)
        
        # 确保索引在范围内
        if index < 0 or index >= len(msg.ranges):
            return None
        
        distance = msg.ranges[index]
        
        # 检查距离是否有效
        if (math.isnan(distance) or math.isinf(distance) or
            distance < self.min_distance_m or distance > self.max_distance_m):
            return None
        
        return distance
    
    def __del__(self):
        """析构函数，关闭串口"""
        if hasattr(self, 'serial') and self.serial.is_open:
            self.serial.close()
            self.get_logger().info('串口已关闭')


def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = LidarFCBridge()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'节点错误: {e}')
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
