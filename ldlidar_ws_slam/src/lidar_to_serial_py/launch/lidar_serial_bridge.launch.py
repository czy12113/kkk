#!/usr/bin/env python3
"""
雷达串口桥接启动文件
用途：启动雷达数据转发节点，将雷达数据通过串口发送到飞控
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # 声明启动参数
    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/ttyS1',
        description='飞控串口，板载UART如 /dev/ttyS1, /dev/ttyAMA1'
    )
    
    baudrate_arg = DeclareLaunchArgument(
        'baudrate',
        default_value='115200',
        description='串口波特率 (常用: 9600, 57600, 115200, 230400)'
    )
    
    send_rate_arg = DeclareLaunchArgument(
        'send_rate',
        default_value='10.0',
        description='数据发送频率 (Hz)'
    )
    
    data_format_arg = DeclareLaunchArgument(
        'data_format',
        default_value='directions_8',
        description='数据格式: directions_8(8方向), nearest(最近障碍物), full(完整扫描)'
    )
    
    enable_heartbeat_arg = DeclareLaunchArgument(
        'enable_heartbeat',
        default_value='true',
        description='是否启用心跳包'
    )
    
    max_distance_arg = DeclareLaunchArgument(
        'max_distance',
        default_value='12.0',
        description='最大有效距离 (米)'
    )
    
    # 创建节点
    lidar_serial_bridge_node = Node(
        package='lidar_to_serial_py',
        executable='lidar_serial_bridge',
        name='lidar_serial_bridge',
        output='screen',
        parameters=[{
            'serial_port': LaunchConfiguration('serial_port'),
            'baudrate': LaunchConfiguration('baudrate'),
            'send_rate': LaunchConfiguration('send_rate'),
            'data_format': LaunchConfiguration('data_format'),
            'enable_heartbeat': LaunchConfiguration('enable_heartbeat'),
            'max_distance': LaunchConfiguration('max_distance'),
        }],
        emulate_tty=True
    )
    
    return LaunchDescription([
        serial_port_arg,
        baudrate_arg,
        send_rate_arg,
        data_format_arg,
        enable_heartbeat_arg,
        max_distance_arg,
        lidar_serial_bridge_node
    ])
