# RDK S100 智能机器人上位机系统

基于 FastAPI + Vue3 的 Web 上位机，部署在 RDK S100 设备上，通过局域网浏览器访问，无需安装客户端。

## 功能模块

| 模块 | 说明 |
|------|------|
| 综合监控 | CPU/内存/温度实时曲线、机器人状态、日志 |
| 视频监控 | RGB + 深度图像实时显示、截图、全屏（v6.0 D435i 真实相机 + YOLO 检测标注） |
| 激光雷达 | Livox Mid-360S 3D 点云实时显示（PointCloud2） |
| IMU 姿态 | Three.js 3D 姿态展示、加速度(g)/角速度(rad/s)曲线、互补滤波姿态解算（v5.0 真实接入） |
| 机器人控制 | 虚拟摇杆、WASD 键盘、长按/点按双模式、速度调节、急停、里程计实时显示 |
| 目标检测 | YOLOv5 目标检测 + D435i 深度测距，带框+距离标注视频推送（v6.0 新增） |
| SLAM 建图 | 占据栅格地图、轨迹、地图保存/加载 |
| 导航规划 | Nav2 目标点设置、多点巡逻（预留） |
| 设备管理 | 设备信息、传感器状态、参数配置 |

## 目录结构

```
rdks100_slam/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py     # 全局宏定义（修改此文件配置参数）
│   │   │   └── websocket_manager.py
│   │   ├── services/
│   │   │   ├── mock_data.py  # 模拟数据生成器
│   │   │   ├── ros2_bridge.py
│   │   │   └── data_pusher.py
│   │   └── api/
│   │       ├── control.py    # 速度控制（线速度+角速度双斜坡加速度限幅）
│   │       ├── slam.py
│   │       ├── navigation.py
│   │       └── device.py
│   ├── main.py
│   ├── requirements.txt
│   └── static/dist/          # 前端构建产物（自动生成）
├── frontend/                 # Vue3 前端
│   ├── src/
│   │   ├── config/index.ts   # 前端宏定义
│   │   ├── views/            # 各功能页面
│   │   ├── stores/robot.ts   # Pinia 全局状态
│   │   └── api/              # HTTP + WebSocket 封装
│   └── package.json
├── ros2_ws/                  # ROS2 工作空间（统一管理所有 ROS2 包）
│   └── src/
│       ├── ldlidar_ros2/          # LD14/14P 激光雷达驱动
│       ├── livox_ros_driver2/     # Livox Mid-360S 驱动
│       ├── d435i_bringup/         # D435i 相机启动包（v6.0 新增）
│       │   └── launch/d435i_camera.launch.py # 启动 realsense2_camera_node
│       ├── d435i_detection/       # YOLOv5 目标检测+深度测距（v6.0 新增）
│       │   ├── d435i_detection/detection_node.py      # CPU 检测节点（yolov5s，已修复 NMS）
│       │   ├── d435i_detection/detection_node_bpu.py  # BPU 检测节点（hbm_runtime）
│       │   └── launch/detection.launch.py              # 一键启动相机+检测
│       └── czybot_navigation2/    # 机器人运动控制（STM32 串口桥接 + 终端键盘控制）
│           └── scripts/
│               ├── stm32_bridge.py           # STM32 串口桥接节点（三层防抖）
│               └── ackermann_teleop_key.py   # 终端键盘遥控（select 非阻塞读取）
├── d435i_ros2/               # YOLOv5 源码 + 权重文件（v6.0 新增，随 deploy.sh 打包）
├── deploy.sh                 # 部署到 RDK 脚本
├── build_ros2_ws.sh          # ROS2 工作空间编译脚本
├── MID360S_RVIZ_SETUP.md     # Livox Mid-360S RViz2 远程可视化配置指南
├── LIVOX_MID360_MIGRATION.md # LD14P → Mid-360S 迁移方案
├── MODULE_PLAN.txt           # 模块化迭代演进方案
├── start.sh                  # 一键启动脚本
└── README.md
```

## 快速开始

### 环境要求

- Python 3.8+
- Node.js 18+（仅构建前端时需要）
- ROS2 Humble（可选，无 ROS2 时自动使用模拟数据）

### 方式一：一键启动（推荐）

```bash
cd /home/sunrise/rdks100_slam
chmod +x start.sh

# 生产模式（构建前端 + 启动后端）
./start.sh prod

# 开发模式（后端 + 前端热重载）
./start.sh dev
```

### 方式二：手动启动

**后端：**
```bash
cd /home/sunrise/rdks100_slam/backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 加载 ROS2 环境（可选）
source /opt/ros/humble/setup.bash

# 启动
python3 main.py
```

**前端（开发模式）：**
```bash
cd /home/sunrise/rdks100_slam/frontend
npm install
npm run dev
```

**前端（生产构建）：**
```bash
cd /home/sunrise/rdks100_slam/frontend
npm run build
# 构建产物自动输出到 backend/static/dist/
```

### Livox Mid-360S 雷达驱动启动（3D 点云 + IMU 数据源）

在独立终端中启动 Livox 雷达驱动，提供 `/livox/lidar`（PointCloud2）和 `/livox/imu` 两个 topic：

```bash
# 加载 ROS2 工作空间环境
source /home/sunrise/rdks100_slam/ros2_ws/install/setup.bash

# 启动 Mid-360S 雷达驱动（PointCloud2 + IMU）
ros2 launch livox_ros_driver2 msg_MID360s_launch.py
```

> **说明**：`msg_MID360s_launch.py` 使用 `MID360s_config.json` 配置，xfer_format=0（PointCloud2 格式），
> 与后端 `_parse_pointcloud2()` 匹配。另有一个 `msg_MID360_launch.py`（使用 `MID360_config.json`），
> 内含特定设备 bd_code，一般使用 `msg_MID360s_launch.py` 即可。
>
> 启动后可用以下命令验证数据是否正常：
> ```bash
> ros2 topic list | grep livox    # 应看到 /livox/lidar 和 /livox/imu
> ros2 topic hz /livox/imu        # 约 200 Hz
> ros2 topic hz /livox/lidar      # 约 10 Hz
> ```

### STM32 串口桥接节点（真实机器人运动控制）

在独立终端中启动 ROS2 STM32 桥接节点，用于将 `/cmd_vel` 指令转发给底盘 STM32：

```bash
# 首次编译 ROS2 工作空间
bash /home/sunrise/rdks100_slam/build_ros2_ws.sh

# 加载工作空间环境
source /home/sunrise/rdks100_slam/ros2_ws/install/setup.bash

# 启动 STM32 桥接节点
ros2 run czybot_navigation2 stm32_bridge
```

> **注意**：默认串口为 `/dev/ttyUSB0`，波特率 `115200`。如需修改，编辑
> `ros2_ws/src/czybot_navigation2/scripts/stm32_bridge.py` 中的 `SERIAL_PORT` 和 `BAUD_RATE`。

### 终端键盘遥控（调试用）

```bash
source /home/sunrise/rdks100_slam/ros2_ws/install/setup.bash
ros2 run czybot_navigation2 ackermann_teleop_key
```

> 使用 WASD 控制小车，Q 键退出。已优化为非阻塞读取，按键响应灵敏。最大线速度 0.5 m/s，最大角速度 0.8 rad/s。

### D435i 相机启动（v6.0 新增）

在独立终端中启动 D435i 相机驱动：

```bash
cd ~/rdks100_slam/ros2_ws
colcon build --packages-select d435i_bringup
source install/setup.bash
ros2 launch d435i_bringup d435i_camera.launch.py
```

> **说明**：发布 `/camera/camera/color/image_raw`（RGB8 30Hz）和 `/camera/camera/aligned_depth_to_color/image_raw`（Z16 对齐深度）。
> 验证：`ros2 topic hz /camera/camera/color/image_raw` → 约 30 Hz。

### YOLOv5 目标检测 + 深度测距（v6.0 新增）

相机启动后，启动检测节点：

```bash
cd ~/rdks100_slam/ros2_ws
colcon build --packages-select d435i_detection
source install/setup.bash

# CPU 版（yolov5s ~2FPS，已修复 NMS）
ros2 launch d435i_detection detection.launch.py camera:=false

# BPU 版（yolov5x_672x672_nv12.hbm，板端推荐）
ros2 run d435i_detection detection_node_bpu
```

> **说明**：CPU 版 yolov5s ~2FPS，BPU 版使用 hbm_runtime 硬件加速。
> 发布 `/detection/results`（JSON）和 `/detection/annotated_image`（BGR8 带框+距离）。
> **话题分离**：`video_rgb`（纯原图）/ `video_annotated`（标注图）/ `detection_results`（结构化数据）独立推送。

### 访问

启动后在局域网内任意浏览器访问：

```
http://<设备IP>:8000
```

例如：`http://10.21.1.145:8000`

## IMU 真实接入（v5.0）

### 硬件特性

系统使用 Livox Mid-360S 内置 IMU，发布到 `/livox/imu`（`sensor_msgs/Imu`），频率 200Hz。

| 特性 | 参数 |
|------|------|
| 加速度量程 | ±8g |
| 陀螺仪量程 | ±2000°/s |
| 输出频率 | 200 Hz |
| 姿态四元数 | 恒为单位四元数 (0,0,0,1)，IMU 不输出姿态 |
| 加速度单位 | g（不是 m/s²） |
| 角速度单位 | rad/s |

### 互补滤波姿态解算

后端 `ros2_bridge._parse_imu()` 使用互补滤波从原始 6 轴数据解算姿态：

- **Roll/Pitch**：α=0.98 互补滤波，0.98×(陀螺仪积分) + 0.02×(加速度计修正)
- **Yaw**：纯陀螺仪积分（无磁力计，长时间漂移）
- **dt**：用 ROS2 消息时间戳计算，异常时默认 0.01s

### 数据格式

`_parse_imu()` 输出与 `mock_data.get_imu_data()` 一致：

```json
{
  "timestamp": 1234567890.123,
  "orientation": {
    "roll": 1.5,
    "pitch": -0.3,
    "yaw": 45.0,
    "quaternion": {"x": 0, "y": 0, "z": 0, "w": 1}
  },
  "angular_velocity": {"x": 0.01, "y": -0.02, "z": 0.05},
  "linear_acceleration": {"x": 0.01, "y": -0.02, "z": 0.98},
  "temperature": 0.0
}
```

> **注意**：`linear_acceleration` 单位为 g（1g ≈ 9.81 m/s²），`angular_velocity` 单位为 rad/s。
> `quaternion` 为 Livox 原始值，始终为单位四元数；姿态角（roll/pitch/yaw）由互补滤波计算。

### 已知局限

- **Yaw 漂移**：无磁力计或外部参考，Yaw 角会随时间累积漂移，需要 SLAM（LIO-SAM/FAST-LIO）或磁力计修正
- **精度限制**：互补滤波适合姿态展示和基本状态监控，不适合精确导航定位
- **加速度单位**：Livox IMU 输出单位为 g，前端已适配显示；mock 数据也使用相同单位

> **⚠ 重要：以上局限仅影响前端 IMU 页面展示，不影响后续 SLAM 建图。**
> SLAM（LIO-SAM/FAST-LIO）不依赖互补滤波输出的姿态角，而是直接使用 IMU 原始 6 轴数据
>（200Hz 角速度 + 加速度）与 LiDAR 点云做紧耦合融合：
> - IMU 提供 200Hz 高频运动预测 → 解决帧间运动估计
> - LiDAR 提供低频绝对位置修正 → 消除 IMU 积分漂移
> - 因子图优化 / 迭代卡尔曼滤波自动估计并补偿 IMU bias
>
> 原始 IMU 数据（200Hz、±8g、±2000°/s）质量完全满足 LIO-SAM/FAST-LIO 的输入要求。

## 相机与目标检测（v6.0 新增）

### 硬件特性

系统使用 Intel RealSense D435i 深度相机，通过 `d435i_bringup` 包启动驱动。

| 特性 | 参数 |
|------|------|
| 分辨率 | 640×480 |
| 帧率 | 30 fps |
| RGB Topic | `/camera/camera/color/image_raw` (RGB8) |
| 深度 Topic | `/camera/camera/aligned_depth_to_color/image_raw` (Z16，对齐) |
| 内置 IMU | 已启用（6 轴加速度+陀螺仪） |

### 视频推送话题分离（v6.0）

三个 WebSocket topic 独立推送，前端 VideoView.vue 分离显示：

| topic | 内容 | 数据来源 |
|-------|------|----------|
| `video_rgb` | 纯原始 RGB 图像（不含检测框） | ros2 → mock 降级 |
| `video_annotated` | 带检测框+距离标注的图像 | ros2_annotated（无数据时不推占位帧） |
| `detection_results` | 结构化检测结果 JSON，10Hz | ros2_bridge._parse_detection_results() → mock 降级 |

### YOLOv5 目标检测 + 深度测距（d435i_detection）

**双版本节点：**

| 版本 | 节点名 | 模型 | 推理方式 |
|------|--------|------|----------|
| CPU | `detection_node` | yolov5s.pt | torch CPU ~2FPS，已修复 NMS + frame_count 拼写 |
| BPU | `detection_node_bpu` | yolov5x_672x672_nv12.hbm | hbm_runtime.HB_HBMRuntime，需 /app/pydev_demo/utils |

**数据流：**
```
D435i → /camera/camera/color/image_raw (30Hz)
      → d435i_detection (CPU/BPU) → /detection/annotated_image (BGR8 带框+距离)
                                  → /detection/results (JSON 结构化数据)
      → ros2_bridge → data_pusher → WebSocket:
           video_rgb        ← 纯原图 JPEG
           video_annotated  ← 标注图 JPEG
           detection_results ← JSON 结构化数据 10Hz
```

**检测结果格式（`/detection/results`，JSON）：**
```json
{
  "detections": [
    {
      "class": "person",
      "confidence": 0.87,
      "bbox": {"x1": 120, "y1": 80, "x2": 380, "y2": 450},
      "distance_m": 2.35
    }
  ],
  "num_detections": 1
}
```

**线程架构：**
- **spin 线程**：订阅图像 → 写入双缓冲（不阻塞推理）
- **推理线程**：读取双缓冲 → YOLOv5 推理 → 深度采样中值滤波 → 发布结果

**深度测距（`get_mid_pos`）：**
- 对每个检测框中心区域随机采样 24 个深度点
- 中值滤波去除离群值，得到稳定距离估计（单位：米）

### 部署说明

```bash
# 1. 下载 YOLOv5 权重（部署前执行一次）
wget -P /home/sunrise/d435i_ros2/weights \
  https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5s.pt
cp -r /home/sunrise/d435i_ros2 /home/sunrise/rdks100_slam/d435i_ros2

# 2. 部署到 RDK
bash /home/sunrise/rdks100_slam/deploy.sh

# 3. RDK 上编译新包
cd ~/rdks100_slam/ros2_ws
colcon build --packages-select d435i_bringup d435i_detection
source install/setup.bash

# 4. 安装 image_transport 插件（首次）
sudo apt install -y ros-humble-image-transport-plugins

# 5. 启动相机
ros2 launch d435i_bringup d435i_camera.launch.py

# 6. 启动检测（CPU 或 BPU）
ros2 launch d435i_detection detection.launch.py camera:=false   # CPU
ros2 run d435i_detection detection_node_bpu                      # BPU
```

### RealSense 相机常见问题

| 问题 | 解决方案 |
|------|----------|
| `No plugins found image_transport` | `sudo apt install ros-humble-image-transport-plugins` |
| `errno=16 Device busy` | `pkill -9 -f realsense2_camera_node && sleep 2` 后重启 |
| 启动顺序 | 先 source 双环境 → d435i_camera.launch.py → detection_node / detection_node_bpu |

### 依赖说明

```
# requirements.txt 关键变更（v6.0）
opencv-python-headless==4.9.0.80   # 替换 opencv-python（避免 GUI 依赖冲突）
numpy==1.26.4                      # 固定版本保证兼容性
```

# 5. 启动检测节点
ros2 launch d435i_detection detection.launch.py camera:=false
```

## 机器人控制说明

### 控制方式

| 方式 | 说明 |
|------|------|
| 虚拟摇杆 | 触屏/鼠标拖拽，支持死区过滤（8%）和 smoothStep 自适应滤波 |
| WASD 键盘 | W/S 控制线速度，A/D 控制角速度，支持 smoothStep 平滑 |
| 方向 D-pad | 屏幕方向按钮，支持多点触控防误触 |

### 控制模式

| 模式 | 说明 |
|------|------|
| 长按模式（默认） | 按键/摇杆松开后小车立即停止，适合精确控制 |
| 点按模式 | 每次按键速度递增/递减（步进 0.05 m/s / 0.1 rad/s），松开不归零，适合长距离匀速行驶 |

点击控制页面右上角的 **长按 / 点按** 按钮切换模式。急停按钮在两种模式下均立即清零所有速度。

### 控制优化参数（防抖专项 v5）

前端 → 后端 → STM32 桥接 → 底盘，四层防抖链路逐级兜底：

| 层级 | 参数 | 值 | 说明 |
|------|------|----|------|
| **前端** | 摇杆死区 | 8% | 消除手指抖动引起的误触 |
| | 自适应滤波（加速） | α=0.30 | 加速阶段响应更快，更跟手 |
| | 自适应滤波（减速/归零/反向） | α=0.40 | 减速/松手快速响应，防舵机抖动 |
| | 发送间隔 | 50 ms (20 Hz) | 节流，避免 HTTP 请求堆积 |
| | 线速度零阈值 | 0.01 m/s | 低于此值归零，与 STM32 8mm/s 死区对齐 |
| | 角速度零阈值 | 0.02 rad/s | 低于此值归零，与 STM32 20mrad/s 死区对齐 |
| **后端** | 线速度加速度限幅 | 2.0 m/s² | 防止速度突变冲击底盘 |
| | 角速度加速度限幅 | 4.0 rad/s² | 防止舵机急转抖动 |
| **STM32桥接** | 线速度死区 | 8 mm/s | 硬件层消除微小速度指令 |
| | 角速度死区 | 20 mrad/s | 硬件层消除舵机抖动 |
| | 去重阈值（线速度） | 5 mm/s | 变化量低于此值不重复发送 |
| | 去重阈值（角速度） | 10 mrad/s | 变化量低于此值不重复发送 |
| | 超时保护 | 0.3 s | 无新指令自动发送停车帧，松手即停 |

### 防抖链路

```
前端 smoothStep(加速α=0.30/减速α=0.40) + 死区 0.02rad/s + 变化检测
  → 后端 线速度2.0m/s² + 角速度4.0rad/s² 双斜坡限幅
    → STM32桥接 死区20mrad/s + 去重10mrad/s + 0.3s超时自动停车
      → STM32 舵机
```

## 激光雷达可视化

支持两种方式查看 Livox Mid-360S 3D 点云：

| 方式 | 说明 | 文档 |
|------|------|------|
| RViz2 (X11) | SSH -X 远程 RViz2，原生 3D 点云 | [MID360S_RVIZ_SETUP.md](MID360S_RVIZ_SETUP.md) |
| Web UI (Three.js) | 浏览器访问 `:8000`，实时 3D 点云可旋转 | 见下方说明 |

### Web UI 3D 点云特性

- **Three.js + OrbitControls**：左键旋转、右键平移、滚轮缩放
- **10000 点/帧 @ 10Hz**：保留约 50% 原始密度，流畅推送
- **3 种着色模式**：高度 / 强度 / 距离，5 段渐变色表
- **AdditiveBlending**：密集区域自然变亮，增强立体感
- **高度过滤**：Z 轴滑块实时过滤，聚焦感兴趣区域
- **视角预设**：俯视 / 正视 / 侧视 / 等轴一键切换
- **FPS + 点数 overlay**：实时监控渲染性能

### ROS2 诊断接口

```bash
# 检查 ROS2 桥接状态（排查数据不通问题）
curl http://<设备IP>:8000/api/device/ros2/diag
```

## 配置说明

### 后端配置（`backend/app/core/config.py`）

```python
ROS2_ENABLED = True                    # 默认 true，rclpy 不存在时自动降级模拟
DEVICE_PORT = 8000                     # 后端端口
PUSH_RATE_LIDAR = 0.1                  # 点云推送间隔（秒，10Hz）

# ROS2 Topic 名称（按实际修改）
ROS2_TOPIC_LIDAR3D = "/livox/lidar"    # Livox Mid-360S PointCloud2
ROS2_TOPIC_IMU = "/livox/imu"          # Livox 内置 IMU
ROS2_TOPIC_CMD_VEL = "/cmd_vel"
ROS2_TOPIC_ODOM = "/odom"
ROS2_TOPIC_RGB_IMAGE: str = "/camera/camera/color/image_raw"              # RGB 图像（D435i 实际 topic）
ROS2_TOPIC_DEPTH_IMAGE: str = "/camera/camera/aligned_depth_to_color/image_raw"  # 对齐深度
ROS2_TOPIC_ANNOTATED_IMAGE: str = "/detection/annotated_image"   # YOLO 检测标注图（v6.0）
```

### 前端配置（`frontend/src/config/index.ts`）

```typescript
// WebSocket 地址自动从 window.location 推断，无需手动配置
// 如需固定地址，设置环境变量 VITE_WS_BASE_URL
export const LIDAR_MAX_POINTS = 10000  // 前端最大渲染点数
export const LIDAR_Z_MIN = -0.5        // 高度过滤下限
export const LIDAR_Z_MAX = 2.0         // 高度过滤上限
```

## ROS2 集成

当 `MOCK_MODE = False` 且 `ROS2_ENABLED = True` 时，系统自动订阅以下 Topic：

| Topic | 消息类型 | 说明 |
|-------|---------|------|
| `/livox/lidar` | `sensor_msgs/PointCloud2` | 激光雷达（Mid-360S） |
| `/livox/imu` | `sensor_msgs/Imu` | 雷达内置 IMU（v5.0 真实接入，互补滤波解算） |
| `/scan` | `sensor_msgs/LaserScan` | 激光雷达（LD14P 兼容，已废弃） |
| `/odom` | `nav_msgs/Odometry` | 里程计（由 STM32 桥接节点发布） |
| `/map` | `nav_msgs/OccupancyGrid` | SLAM 地图 |
| `/battery_state` | `sensor_msgs/BatteryState` | 电池 |
| `/camera/camera/color/image_raw` | `sensor_msgs/Image` | RGB 图像（v6.0 D435i 真实接入，30Hz） |
| `/camera/camera/aligned_depth_to_color/image_raw` | `sensor_msgs/Image` | 对齐深度图像（v6.0 真实接入） |
| `/detection/results` | `std_msgs/String` | YOLOv5 检测结果 JSON（v6.0 新增） |
| `/detection/annotated_image` | `sensor_msgs/Image` | 检测标注图像 BGR8（v6.0） |

**WebSocket 推送 Topic（v6.0 新增）：**

| WebSocket Topic | 说明 |
|-----------------|------|
| `video_annotated` | 带检测框+距离标注的 JPEG 图像（无数据时不推送占位帧） |
| `detection_results` | 结构化检测结果 JSON，10Hz 推送 |

发布 Topic：

| Topic | 消息类型 | 说明 |
|-------|---------|------|
| `/cmd_vel` | `geometry_msgs/Twist` | 速度控制（由 STM32 桥接节点消费） |
| `/goal_pose` | `geometry_msgs/PoseStamped` | 导航目标 |

### STM32 桥接节点（`czybot_navigation2`）

`stm32_bridge.py` 是连接 ROS2 与底盘 STM32 的核心节点：

- 订阅 `/cmd_vel`，将 Twist 消息转换为 STM32 串口协议帧发送
- 接收 STM32 上报的里程计数据，发布到 `/odom`
- 内置死区滤波：线速度 < 5 mm/s 或角速度 < 15 mrad/s 时置零，消除舵机抖动

## WebSocket 协议

连接地址：`ws://<host>:8000/ws` 或 `ws://<host>:8000/ws/lidar,imu`

消息格式：
```json
{
  "topic": "robot_status",
  "data": { ... },
  "timestamp": 1234567890.123
}
```

支持的 Topic：`system`, `robot_status`, `lidar`, `imu`, `slam_map`, `video_rgb`, `video_depth`, `video_annotated`, `detection_results`, `navigation`, `log`, `heartbeat`, `odom`

> **v6.0 话题分离**：`video_rgb` 仅推纯原图，`video_annotated` 推标注图，`detection_results` 推结构化 JSON。前端 VideoView.vue 三区独立显示。

## 网络配置

| 设备 | IP | 说明 |
|------|-----|------|
| RDK S100 Wi-Fi | `10.21.1.145` | PC 通过此 IP 访问 |
| RDK S100 eth1 | `192.168.1.50/24` | 连接雷达的网口 |
| Livox Mid-360S | `192.168.1.138` | 雷达固定 IP |

## 开发说明

- 所有可配置参数集中在 `config.py`（后端）和 `config/index.ts`（前端），修改后重启生效
- 模拟数据模式下无需任何硬件即可完整体验所有功能
- 前端构建产物由 FastAPI 作为静态文件服务，生产环境只需启动后端一个进程
- 控制优化采用三层死区方案：前端零阈值 → 后端线速度加速度限幅 → STM32 硬件死区，彻底消除舵机抖动
