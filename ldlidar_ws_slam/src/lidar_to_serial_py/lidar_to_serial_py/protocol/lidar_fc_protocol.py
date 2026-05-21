#!/usr/bin/env python3
"""
飞控通信协议实现
实现自定义串口协议的数据打包和校验
"""
import struct
from typing import List, Tuple

class FlightControllerProtocol:
    """飞控通信协议类"""
    
    # 协议常量
    FRAME_HEAD = 0xAA
    TARGET_ADDR = 0xFF
    ID_RANGING_SENSOR = 0x34
    DATA_LENGTH = 0x07
    
    # 方向定义
    DIRECTION_HORIZONTAL = 0
    DIRECTION_VERTICAL = 1
    
    # 无效距离标记
    INVALID_DISTANCE = 0xFFFFFFFF
    
    @staticmethod
    def calculate_checksums(data: bytes) -> Tuple[int, int]:
        """
        计算和校验和附加校验
        
        Args:
            data: 从帧头到数据内容的所有字节
            
        Returns:
            (sum_check, add_check): 和校验值和附加校验值
        """
        sum_check = 0
        add_check = 0
        
        for byte in data:
            sum_check = (sum_check + byte) & 0xFF  # 只取低8位
            add_check = (add_check + sum_check) & 0xFF  # 累加sum_check
            
        return sum_check, add_check
    
    @staticmethod
    def pack_ranging_data(direction: int, angle: int, distance_cm: int) -> bytes:
        """
        打包测距传感器数据（ID 0x34）
        
        Args:
            direction: 0=水平，1=垂直
            angle: 角度 0-359
            distance_cm: 距离(厘米)，如果无效则传入 INVALID_DISTANCE
            
        Returns:
            完整的数据帧（包含校验）
        """
        # 限制参数范围
        direction = direction & 0xFF
        angle = angle % 360
        
        # 如果距离无效或超出范围，使用无效标记
        if distance_cm < 0 or distance_cm > 0xFFFFFFFE:
            distance_cm = FlightControllerProtocol.INVALID_DISTANCE
        
        # 构建数据部分（不含校验）
        frame_data = bytearray()
        frame_data.append(FlightControllerProtocol.FRAME_HEAD)  # 帧头
        frame_data.append(FlightControllerProtocol.TARGET_ADDR)  # 目标地址
        frame_data.append(FlightControllerProtocol.ID_RANGING_SENSOR)  # 功能码
        frame_data.append(FlightControllerProtocol.DATA_LENGTH)  # 数据长度
        
        # DATA区域：DIRECTION(1) + ANGLE(2) + DIST(4)
        frame_data.append(direction)  # DIRECTION
        frame_data.extend(struct.pack('<H', angle))  # ANGLE (小端序)
        frame_data.extend(struct.pack('<I', distance_cm))  # DIST (小端序)
        
        # 计算校验
        sum_check, add_check = FlightControllerProtocol.calculate_checksums(frame_data)
        
        # 添加校验
        frame_data.append(sum_check)
        frame_data.append(add_check)
        
        return bytes(frame_data)
    
    @staticmethod
    def pack_multiple_directions(measurements: List[Tuple[int, int, int]]) -> bytes:
        """
        打包多个方向的测距数据
        
        Args:
            measurements: [(direction, angle, distance_cm), ...]
            
        Returns:
            所有帧拼接的字节流
        """
        all_frames = bytearray()
        
        for direction, angle, distance_cm in measurements:
            frame = FlightControllerProtocol.pack_ranging_data(direction, angle, distance_cm)
            all_frames.extend(frame)
        
        return bytes(all_frames)
    
    @staticmethod
    def verify_frame(frame: bytes) -> bool:
        """
        验证接收到的帧是否正确
        
        Args:
            frame: 完整的数据帧
            
        Returns:
            True if valid, False otherwise
        """
        if len(frame) < 6:  # 最小帧长度
            return False
        
        # 检查帧头
        if frame[0] != FlightControllerProtocol.FRAME_HEAD:
            return False
        
        # 获取数据长度
        data_len = frame[3]
        expected_len = 4 + data_len + 2  # HEAD + ADDR + ID + LEN + DATA + 2校验
        
        if len(frame) != expected_len:
            return False
        
        # 计算校验
        data_part = frame[:-2]  # 除去最后两个校验字节
        sum_check, add_check = FlightControllerProtocol.calculate_checksums(data_part)
        
        # 验证校验
        return frame[-2] == sum_check and frame[-1] == add_check


# 测试代码
if __name__ == '__main__':
    print("飞控协议测试")
    print("=" * 50)
    
    # 测试1：水平向前 100cm
    frame1 = FlightControllerProtocol.pack_ranging_data(
        direction=FlightControllerProtocol.DIRECTION_HORIZONTAL,
        angle=0,
        distance_cm=100
    )
    print(f"水平向前100cm: {frame1.hex(' ').upper()}")
    print(f"验证结果: {FlightControllerProtocol.verify_frame(frame1)}")
    
    # 测试2：水平向后 200cm
    frame2 = FlightControllerProtocol.pack_ranging_data(
        direction=FlightControllerProtocol.DIRECTION_HORIZONTAL,
        angle=180,
        distance_cm=200
    )
    print(f"\n水平向后200cm: {frame2.hex(' ').upper()}")
    print(f"验证结果: {FlightControllerProtocol.verify_frame(frame2)}")
    
    # 测试3：垂直向下 150cm
    frame3 = FlightControllerProtocol.pack_ranging_data(
        direction=FlightControllerProtocol.DIRECTION_VERTICAL,
        angle=270,
        distance_cm=150
    )
    print(f"\n垂直向下150cm: {frame3.hex(' ').upper()}")
    print(f"验证结果: {FlightControllerProtocol.verify_frame(frame3)}")
    
    # 测试4：无效数据
    frame4 = FlightControllerProtocol.pack_ranging_data(
        direction=FlightControllerProtocol.DIRECTION_HORIZONTAL,
        angle=90,
        distance_cm=FlightControllerProtocol.INVALID_DISTANCE
    )
    print(f"\n无效数据: {frame4.hex(' ').upper()}")
    print(f"验证结果: {FlightControllerProtocol.verify_frame(frame4)}")
    
    # 测试5：8方向数据
    print("\n" + "=" * 50)
    print("8方向测距数据:")
    directions_8 = [
        (0, 0, 100),      # 前
        (0, 45, 120),     # 右前
        (0, 90, 150),     # 右
        (0, 135, 130),    # 右后
        (0, 180, 200),    # 后
        (0, 225, 140),    # 左后
        (0, 270, 160),    # 左
        (0, 315, 110),    # 左前
    ]
    
    all_frames = FlightControllerProtocol.pack_multiple_directions(directions_8)
    print(f"总长度: {len(all_frames)} 字节")
    print(f"数据: {all_frames.hex(' ').upper()}")
