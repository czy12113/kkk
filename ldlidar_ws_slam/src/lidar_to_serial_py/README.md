# Lidar to Serial Bridge (雷达串口桥接)

## 📖 项目简介

这个ROS2包用于将激光雷达数据通过串口转发到飞控。

**数据流向：**
```
雷达 (/dev/ttyACM0) → RDK X5 (ROS2节点) → 串口 (/dev/ttyS0等) → 飞控
```

## 目录结构

```
lidar_to_serial_py/
├── package.xml
├── setup.py
├── README.md
├── resource/lidar_to_serial_py
├── config/                    # 节点参数示例
├── launch/                    # ROS2 launch 文件
├── lidar_to_serial_py/        # Python 包
│   ├── nodes/                 # 可执行节点（console_scripts 入口）
│   └── protocol/              # 飞控二进制协议实现
├── examples/cpp/              # 飞控端 C 语言解析示例（参考代码，非 ROS 构建）
└── tools/                     # 独立调试脚本（串口接收自测）
```

安装后，示例与工具位于 `share/lidar_to_serial_py/examples/cpp/` 与 `share/lidar_to_serial_py/tools/`。

## ✨ 功能特性

- ✅ 支持3种数据格式：8方向、最近障碍物、完整扫描
- ✅ 可配置串口参数（设备、波特率）
- ✅ 可配置发送频率
- ✅ 心跳包机制（可选）
- ✅ 数据平均滤波
- ✅ 自动重连机制
- ✅ 线程安全的串口操作
- ✅ 实时状态监控

## 📦 依赖项

- ROS2 Humble
- Python 3
- pyserial

安装依赖：
```bash
sudo apt install python3-serial
```

## 🚀 快速开始

### 1. 编译包

```bash
cd ~/ldlidar_ros_ws
colcon build --packages-select lidar_to_serial_py
source install/setup.bash
```

### 2. 查找飞控串口

```bash
# 查看所有串口设备
ls -l /dev/tty*

# 常见的串口设备：
# /dev/ttyS0, /dev/ttyS1  - 板载串口
# /dev/ttyUSB0, /dev/ttyUSB1 - USB转串口
# /dev/ttyAMA0 - ARM串口
```

### 3. 配置串口权限

```bash
# 将当前用户添加到dialout组
sudo usermod -aG dialout $USER

# 或者直接修改权限（临时）
sudo chmod 666 /dev/ttyS0
```

### 4. 启动节点

**方式1：使用默认参数**
```bash
ros2 launch lidar_to_serial_py lidar_serial_bridge.launch.py
```

**方式2：自定义参数**
```bash
ros2 launch lidar_to_serial_py lidar_serial_bridge.launch.py \
  serial_port:=/dev/ttyS0 \
  baudrate:=115200 \
  data_format:=directions_8 \
  send_rate:=10.0
```

**方式3：直接运行节点**
```bash
ros2 run lidar_to_serial_py lidar_serial_bridge \
  --ros-args \
  -p serial_port:=/dev/ttyS0 \
  -p baudrate:=115200 \
  -p data_format:=directions_8
```

## ⚙️ 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `serial_port` | string | `/dev/ttyS0` | 飞控串口设备路径 |
| `baudrate` | int | `115200` | 串口波特率 |
| `send_rate` | float | `10.0` | 数据发送频率(Hz) |
| `data_format` | string | `directions_8` | 数据格式 |
| `enable_heartbeat` | bool | `true` | 是否启用心跳包 |
| `max_distance` | float | `12.0` | 最大有效距离(米) |

### 数据格式选项

1. **directions_8** (推荐)
   - 发送8个方向的距离：前、后、左、右、左前、右前、左后、右后
   - 数据量适中，易于飞控处理
   - 包大小：38字节

2. **nearest**
   - 只发送最近障碍物的角度和距离
   - 数据量最小
   - 包大小：11字节

3. **full**
   - 发送完整扫描数据（每10度一个点）
   - 数据量大但信息完整
   - 包大小：约220字节

## 📡 通信协议

### 数据包格式

**8方向格式 (directions_8):**
```
帧头(2) + 长度(1) + 数据(32) + 校验和(1) + 帧尾(2) = 38字节

0xAA 0x55 0x20 [8个float距离] CS 0x0D 0x0A

数据顺序：前、右前、右、右后、后、左后、左、左前
每个距离：4字节 float (小端序)
```

**最近障碍物格式 (nearest):**
```
帧头(2) + 角度(2) + 距离(4) + 校验和(1) + 帧尾(2) = 11字节

0xAA 0x55 [角度uint16] [距离float] CS 0x0D 0x0A

角度：0-3600 (实际角度×10，精度0.1度)
距离：float (米)
```

**心跳包格式:**
```
0xAA 0x55 0xFF 0x00 CS 0x0D 0x0A
每秒发送一次
```

### 校验和计算

简单累加校验：
```python
checksum = sum(data[3:]) & 0xFF
```

## 🔍 测试和调试

### 串口接收自测（tools）

在源码目录下：

```bash
python3 tools/test_serial_receive.py /dev/ttyCH343USB0 115200
```

### 1. 检查雷达数据

```bash
# 查看雷达话题
ros2 topic list | grep scan

# 查看雷达数据
ros2 topic echo /scan
```

### 2. 监控串口数据

```bash
# 使用minicom监控串口
sudo minicom -D /dev/ttyS0 -b 115200

# 或使用hexdump查看原始数据
sudo cat /dev/ttyS0 | hexdump -C
```

### 3. 查看节点日志

```bash
# 实时查看日志
ros2 run lidar_to_serial_py lidar_serial_bridge

# 查看详细调试信息
ros2 run lidar_to_serial_py lidar_serial_bridge --ros-args --log-level debug
```

## 🛠️ 常见问题

### 问题1：串口打开失败

**错误信息：** `无法打开串口 /dev/ttyS0: Permission denied`

**解决方案：**
```bash
# 方法1：添加用户到dialout组
sudo usermod -aG dialout $USER
# 注销后重新登录

# 方法2：临时修改权限
sudo chmod 666 /dev/ttyS0
```

### 问题2：找不到串口设备

**解决方案：**
```bash
# 查看所有串口
ls -l /dev/tty*

# 查看USB串口
ls -l /dev/ttyUSB*

# 查看串口信息
dmesg | grep tty
```

### 问题3：数据发送失败

**检查步骤：**
1. 确认串口设备正确
2. 确认波特率匹配
3. 检查串口线连接
4. 查看节点日志

### 问题4：飞控收不到数据

**检查步骤：**
1. 使用minicom测试串口是否有数据输出
2. 确认飞控串口配置正确
3. 确认数据格式与飞控期望一致
4. 检查TX/RX线是否接反

## 📊 性能指标

- 发送频率：1-20 Hz (可配置)
- 延迟：< 10ms
- CPU占用：< 5%
- 内存占用：< 50MB

## 🔗 相关文档

- [RDK X5移植指南](../../01_RDK_X5_移植指南.md)
- [雷达数据串口转发](../../22_雷达数据串口转发到飞控.md)
- [ROS2官方文档](https://docs.ros.org/en/humble/)

## 📝 开发者信息

- 维护者：sunrise
- 许可证：MIT
- 版本：1.0.0

## 🤝 贡献

欢迎提交Issue和Pull Request！
