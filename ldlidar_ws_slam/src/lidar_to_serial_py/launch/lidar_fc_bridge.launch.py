#!/usr/bin/env python3
"""
雷达到飞控协议桥接启动文件
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # 声明启动参数
    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/ttyCH343USB0',
        description='飞控 USB-TTL 串口 (CH343 常见为 /dev/ttyCH343USB0)'
    )
    
    baud_rate_arg = DeclareLaunchArgument(
        'baud_rate',
        default_value='115200',
        description='串口波特率'
    )
    
    num_directions_arg = DeclareLaunchArgument(
        'num_directions',
        default_value='8',
        description='发送方向数 (8或36)'
    )
    
    max_distance_arg = DeclareLaunchArgument(
        'max_distance_m',
        default_value='12.0',
        description='最大有效距离(米)'
    )
    
    min_distance_arg = DeclareLaunchArgument(
        'min_distance_m',
        default_value='0.1',
        description='最小有效距离(米)'
    )
    
    # 创建节点
    lidar_fc_bridge_node = Node(
        package='lidar_to_serial_py',
        executable='lidar_fc_bridge',
        name='lidar_fc_bridge',
        output='screen',
        parameters=[{
            'serial_port': LaunchConfiguration('serial_port'),
            'baud_rate': LaunchConfiguration('baud_rate'),
            'num_directions': LaunchConfiguration('num_directions'),
            'max_distance_m': LaunchConfiguration('max_distance_m'),
            'min_distance_m': LaunchConfiguration('min_distance_m'),
        }],
        emulate_tty=True
    )
    
    return LaunchDescription([
        serial_port_arg,
        baud_rate_arg,
        num_directions_arg,
        max_distance_arg,
        min_distance_arg,
        lidar_fc_bridge_node
    ])
