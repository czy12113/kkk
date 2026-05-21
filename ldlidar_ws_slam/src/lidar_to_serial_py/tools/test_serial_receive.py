#!/usr/bin/env python3
"""
串口接收测试工具
用于测试和验证从RDK X5发送的雷达数据
可以在飞控或另一台设备上运行此脚本来验证数据传输
"""

import serial
import struct
import sys
import time

class SerialReceiver:
    def __init__(self, port='/dev/ttyCH343USB0', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.packet_count = 0
        self.error_count = 0
        
    def connect(self):
        """连接串口"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            print(f"✓ 串口已打开: {self.port} @ {self.baudrate}")
            return True
        except Exception as e:
            print(f"✗ 无法打开串口: {e}")
            return False
    
    def find_frame_header(self):
        """查找帧头 0xAA 0x55"""
        while True:
            byte = self.ser.read(1)
            if not byte:
                return False
            if byte[0] == 0xAA:
                byte2 = self.ser.read(1)
                if byte2 and byte2[0] == 0x55:
                    return True
        return False
    
    def parse_8_directions(self, data):
        """解析8方向数据"""
        if len(data) < 32:
            return None
        
        directions = ['前', '右前', '右', '右后', '后', '左后', '左', '左前']
        distances = []
        
        for i in range(8):
            offset = i * 4
            distance = struct.unpack('<f', data[offset:offset+4])[0]
            distances.append(distance)
        
        return dict(zip(directions, distances))
    
    def parse_nearest(self, angle_data, distance_data):
        """解析最近障碍物数据"""
        angle_raw = struct.unpack('<H', angle_data)[0]
        angle = angle_raw / 10.0  # 转换为度
        distance = struct.unpack('<f', distance_data)[0]
        return angle, distance
    
    def verify_checksum(self, data, checksum):
        """验证校验和"""
        calculated = sum(data) & 0xFF
        return calculated == checksum
    
    def receive_loop(self):
        """接收循环"""
        print("\n开始接收数据...")
        print("=" * 70)
        
        try:
            while True:
                # 查找帧头
                if not self.find_frame_header():
                    continue
                
                # 读取数据长度或类型标识
                length_byte = self.ser.read(1)
                if not length_byte:
                    continue
                
                length = length_byte[0]
                
                # 心跳包
                if length == 0xFF:
                    flag = self.ser.read(1)
                    checksum = self.ser.read(1)
                    footer = self.ser.read(2)
                    if footer == b'\x0D\x0A':
                        print("💓 心跳包")
                    continue
                
                # 8方向数据包
                if length == 32:
                    data = self.ser.read(32)
                    checksum = self.ser.read(1)
                    footer = self.ser.read(2)
                    
                    if len(data) == 32 and footer == b'\x0D\x0A':
                        if self.verify_checksum(data, checksum[0]):
                            self.packet_count += 1
                            distances = self.parse_8_directions(data)
                            
                            print(f"\n[包 #{self.packet_count}] 8方向数据:")
                            print(f"  前方: {distances['前']:.2f}m  |  后方: {distances['后']:.2f}m")
                            print(f"  左侧: {distances['左']:.2f}m  |  右侧: {distances['右']:.2f}m")
                            print(f"  左前: {distances['左前']:.2f}m  |  右前: {distances['右前']:.2f}m")
                            print(f"  左后: {distances['左后']:.2f}m  |  右后: {distances['右后']:.2f}m")
                        else:
                            self.error_count += 1
                            print(f"✗ 校验和错误 (错误计数: {self.error_count})")
                    continue
                
                # 最近障碍物数据包 (长度为6: 2字节角度 + 4字节距离)
                if length == 6:
                    angle_data = self.ser.read(2)
                    distance_data = self.ser.read(4)
                    checksum = self.ser.read(1)
                    footer = self.ser.read(2)
                    
                    if footer == b'\x0D\x0A':
                        data = angle_data + distance_data
                        if self.verify_checksum(data, checksum[0]):
                            self.packet_count += 1
                            angle, distance = self.parse_nearest(angle_data, distance_data)
                            print(f"[包 #{self.packet_count}] 最近障碍物: 角度={angle:.1f}°, 距离={distance:.2f}m")
                        else:
                            self.error_count += 1
                            print(f"✗ 校验和错误 (错误计数: {self.error_count})")
                    continue
                
                # 其他数据包
                print(f"收到未知数据包，长度: {length}")
                
        except KeyboardInterrupt:
            print("\n\n接收已停止")
            print(f"总计接收: {self.packet_count} 包")
            print(f"错误次数: {self.error_count} 次")
            if self.packet_count > 0:
                success_rate = ((self.packet_count - self.error_count) / self.packet_count) * 100
                print(f"成功率: {success_rate:.1f}%")
    
    def close(self):
        """关闭串口"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("串口已关闭")

def main():
    print("=" * 70)
    print("雷达数据串口接收测试工具")
    print("=" * 70)
    
    # 解析命令行参数
    port = '/dev/ttyCH343USB0'
    baudrate = 115200
    
    if len(sys.argv) > 1:
        port = sys.argv[1]
    if len(sys.argv) > 2:
        baudrate = int(sys.argv[2])
    
    print(f"\n配置:")
    print(f"  串口: {port}")
    print(f"  波特率: {baudrate}")
    print(f"\n提示: 按 Ctrl+C 停止接收\n")
    
    receiver = SerialReceiver(port, baudrate)
    
    if receiver.connect():
        try:
            receiver.receive_loop()
        finally:
            receiver.close()
    else:
        print("\n使用方法:")
        print(f"  python3 {sys.argv[0]} [串口设备] [波特率]")
        print(f"\n示例:")
        print(f"  python3 {sys.argv[0]} /dev/ttyCH343USB0 115200")
        print(f"  python3 {sys.argv[0]} /dev/ttyUSB0 57600")
        sys.exit(1)

if __name__ == '__main__':
    main()
