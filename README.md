# LD14P LiDAR SLAM 工作空间

基于 ROS2 Humble 的 LD14P 激光雷达 SLAM 建图与数据桥接工作空间，支持在 **RDK X5** 等 ARM 开发板上运行。

## 📁 目录结构

```
ldlidar_ws_slam/
├── README.md                 # 本文件
├── deploy.sh                 # 一键打包部署到 RDK X5
├── rdk_setup.sh              # RDK X5 端自动配置脚本
├── my_map/                   # 预建地图（PGM + YAML）
│   ├── my_map.pgm / .yaml
│   └── map_20260510_192911.pgm / .yaml
└── src/                      # ROS2 功能包源码
    ├── ldlidar_ros2/         # LD14P 雷达驱动 + SLAM 启动文件
    └── lidar_to_serial_py/   # 雷达数据串口桥接飞控
```

## 🚀 功能包概览

### 1. ldlidar_ros2 — LD14P 雷达驱动与 SLAM 建图

LDROBOT LD14P 激光雷达的 ROS2 驱动节点，集成多种 SLAM 算法启动文件。

| 启动文件 | 说明 |
|---------|------|
| `ld14p.launch.py` | 单独启动雷达驱动节点 |
| `slam_mapping.launch.py` | **slam_toolbox** 在线异步建图 (推荐) |
| `cartographer_mapping.launch.py` | **Cartographer** 纯激光 SLAM |
| `cartographer_handheld.launch.py` | Cartographer 手持建图模式 |
| `hector_mapping.launch.py` | **Hector SLAM** 建图 (无需里程计) |
| `gmapping.launch.py` | **Gmapping** 粒子滤波 SLAM |
| `rviz_view.launch.py` | 仅启动 RViz2 可视化 |

**核心特性：**

- 自动检测 `/dev/ttyCH343USB*` 设备号，无需手动指定串口
- 支持扫描方向设置（顺时针/逆时针）和角度裁剪
- 兼容 slam_toolbox、Cartographer、Hector、Gmapping 等主流 SLAM 算法
- 无需里程计，手持建图即可

**依赖项：**

```bash
ros-humble-slam-toolbox
ros-humble-cartographer-ros
ros-humble-nav2-map-server
ros-humble-tf2-ros ros-humble-tf2-tools
python3-serial
```

### 2. lidar_to_serial_py — 激光雷达串口桥接

将 LiDAR 扫描数据通过串口转发到飞控的 ROS2 功能包。

**数据流向：**

```
雷达 (/dev/ttyACM0) → RDK X5 (ROS2节点) → 串口 (/dev/ttyS0) → 飞控
```

**支持的协议格式：**

- 8 方向 / 36 方向障碍物距离
- 最近障碍物距离与角度
- 完整扫描数据

**核心特性：**

- 可配置串口参数（设备、波特率）
- 可配置发送频率
- 心跳包机制
- 数据平均滤波
- 自动重连与线程安全

## 🔧 快速开始

### 环境要求

- **操作系统**：Ubuntu 22.04 (RDK X5 / x86)
- **ROS2 发行版**：Humble
- **硬件**：LD14P 激光雷达、CH343 USB 转串口模块

### 1. 编译工作空间

```bash
cd ~/ldlidar_ws_slam
colcon build --symlink-install
source install/setup.bash
```

### 2. 启动 SLAM 建图

**slam_toolbox 建图（推荐）：**

```bash
ros2 launch ldlidar slam_mapping.launch.py
```

**Cartographer 建图：**

```bash
ros2 launch ldlidar cartographer_mapping.launch.py
```

### 3. 启动雷达串口桥接

```bash
ros2 launch lidar_to_serial_py lidar_fc_bridge.launch.py
```

### 4. 保存地图

```bash
ros2 run nav2_map_server map_saver_cli -f ~/my_map
```

## 📦 一键部署到 RDK X5

本地执行打包和传输脚本：

```bash
cd ~/ldlidar_ws_slam
./deploy.sh
```

> 脚本会打包 `src/` 目录并通过 SCP 传输到 RDK X5（默认 IP: `192.168.128.10`，用户 `sunrise`）。

在 RDK X5 上执行自动配置：

```bash
ssh sunrise@192.168.128.10
chmod +x ~/rdk_setup.sh
./rdk_setup.sh
```

`rdk_setup.sh` 会完成：
1. 解压工作空间
2. 安装依赖包 (slam_toolbox, tf2, nav2_map_server 等)
3. 编译工作空间
4. 添加环境变量到 `.bashrc`

## 🗺️ 预建地图

`my_map/` 目录包含已构建的地图文件，可在导航中直接使用：

| 文件 | 分辨率 | 说明 |
|------|--------|------|
| `my_map.pgm` / `my_map.yaml` | 0.05 m/pixel | 最近构建的地图 |
| `map_20260510_192911.pgm` / `.yaml` | 0.05 m/pixel | 2026-05-10 备份 |

> YAML 文件中定义了地图原点 `origin: [-46, -9.78, 0]`（左下角偏移，单位为米）。

## 🔌 串口说明

| 设备路径 | 用途 |
|---------|------|
| `/dev/ttyCH343USB0` | LD14P 雷达数据（CH343 USB 转 TTL） |
| `/dev/ttyS0` 或其他 | 飞控通信串口（雷达桥接用） |

> 雷达节点会自动检测 `/dev/ttyCH343USB*`，若设备号变化无需手动修改。

## 📄 License

MIT License

## 🙏 致谢

- LDROBOT LD14P LiDAR 驱动
- [slam_toolbox](https://github.com/SteveMacenski/slam_toolbox)
- [Cartographer](https://github.com/cartographer-project/cartographer_ros)
