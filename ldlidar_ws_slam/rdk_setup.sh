#!/bin/bash
########################################
# RDK X5 上的自动化设置脚本
# 在RDK上运行此脚本完成解压、编译、配置
########################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}========================================"
echo "  RDK X5 SLAM环境自动配置"
echo "========================================${NC}"
echo ""

# 检查是否在RDK上
if [ ! -f "/etc/version" ]; then
    echo -e "${YELLOW}警告: 可能不在RDK设备上${NC}"
fi

# 检查打包文件
PACKAGE_NAME="ldlidar_slam.tar.gz"
if [ ! -f ~/"$PACKAGE_NAME" ]; then
    echo -e "${RED}错误: 找不到 $PACKAGE_NAME${NC}"
    echo "请先从本地电脑传输文件到RDK"
    exit 1
fi

# 解压文件
echo -e "${YELLOW}[1/5] 解压工作空间...${NC}"
cd ~
tar -xzf "$PACKAGE_NAME"
echo -e "${GREEN}解压完成${NC}"

# 创建工作空间
echo ""
echo -e "${YELLOW}[2/5] 设置工作空间...${NC}"
mkdir -p ~/ldlidar_ws_slam
if [ -d "src" ]; then
    mv src ~/ldlidar_ws_slam/
    echo -e "${GREEN}工作空间创建完成: ~/ldlidar_ws_slam${NC}"
else
    echo -e "${RED}错误: 找不到src目录${NC}"
    exit 1
fi

# 安装依赖
echo ""
echo -e "${YELLOW}[3/5] 检查依赖包...${NC}"

# 检查slam_toolbox
echo "检查slam_toolbox..."
if ! dpkg -l | grep -q ros-humble-slam-toolbox; then
    echo -e "${YELLOW}slam_toolbox未安装${NC}"
    echo "尝试安装slam_toolbox..."
    
    # 尝试更新并安装
    if sudo apt update 2>/dev/null && sudo apt install ros-humble-slam-toolbox -y 2>/dev/null; then
        echo -e "${GREEN}slam_toolbox安装完成${NC}"
    else
        echo -e "${RED}警告: apt安装失败（可能是网络问题）${NC}"
        echo -e "${YELLOW}请手动安装: sudo apt install ros-humble-slam-toolbox${NC}"
        echo "继续执行其他步骤..."
    fi
else
    echo -e "${GREEN}slam_toolbox已安装${NC}"
fi

# 检查其他依赖（不强制要求）
echo "检查其他ROS2依赖..."
MISSING_DEPS=""

if ! dpkg -l | grep -q ros-humble-tf2-ros; then
    MISSING_DEPS="$MISSING_DEPS ros-humble-tf2-ros"
fi
if ! dpkg -l | grep -q ros-humble-tf2-tools; then
    MISSING_DEPS="$MISSING_DEPS ros-humble-tf2-tools"
fi
if ! dpkg -l | grep -q ros-humble-nav2-map-server; then
    MISSING_DEPS="$MISSING_DEPS ros-humble-nav2-map-server"
fi
if ! dpkg -l | grep -q python3-serial; then
    MISSING_DEPS="$MISSING_DEPS python3-serial"
fi

if [ -n "$MISSING_DEPS" ]; then
    echo -e "${YELLOW}缺少以下依赖:$MISSING_DEPS${NC}"
    echo "尝试安装..."
    if sudo apt install -y $MISSING_DEPS 2>/dev/null; then
        echo -e "${GREEN}依赖安装完成${NC}"
    else
        echo -e "${YELLOW}部分依赖安装失败，请稍后手动安装:${NC}"
        echo "sudo apt install$MISSING_DEPS"
    fi
else
    echo -e "${GREEN}所有依赖已安装${NC}"
fi

# 编译工作空间
echo ""
echo -e "${YELLOW}[4/5] 编译工作空间...${NC}"
cd ~/ldlidar_ws_slam

# Source ROS2环境
source /opt/ros/humble/setup.bash

echo "开始编译（可能需要几分钟）..."
colcon build --symlink-install

if [ $? -eq 0 ]; then
    echo -e "${GREEN}编译成功！${NC}"
else
    echo -e "${RED}编译失败！请检查错误信息${NC}"
    exit 1
fi

# 配置环境
echo ""
echo -e "${YELLOW}[5/5] 配置环境...${NC}"

# 添加到bashrc（如果还没有）
if ! grep -q "ldlidar_ws_slam" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# LD14P SLAM工作空间" >> ~/.bashrc
    echo "source ~/ldlidar_ws_slam/install/setup.bash" >> ~/.bashrc
    echo -e "${GREEN}已添加到~/.bashrc${NC}"
else
    echo -e "${GREEN}环境变量已配置${NC}"
fi

# 检查串口设备
echo ""
echo -e "${YELLOW}检查串口设备...${NC}"
if ls /dev/ttyCH343USB* 1> /dev/null 2>&1; then
    echo -e "${GREEN}找到串口设备:${NC}"
    ls -l /dev/ttyCH343USB*
    
    # 设置串口权限
    echo "设置串口权限..."
    sudo chmod 666 /dev/ttyCH343USB*
    echo -e "${GREEN}串口权限已设置${NC}"
else
    echo -e "${YELLOW}警告: 未找到CH343串口设备${NC}"
    echo "请检查雷达是否已连接"
fi

# 完成
echo ""
echo -e "${GREEN}========================================"
echo "  配置完成！"
echo "========================================${NC}"
echo ""
echo -e "${BLUE}快速启动命令:${NC}"
echo ""
echo "1. 启动SLAM建图:"
echo "   source ~/ldlidar_ws_slam/install/setup.bash"
echo "   ros2 launch ldlidar slam_mapping.launch.py"
echo ""
echo "2. 查看雷达数据:"
echo "   ros2 topic echo /scan"
echo ""
echo "3. 保存地图:"
echo "   ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap \"{name: {data: '/home/sunrise/maps/my_map'}}\""
echo ""
echo -e "${YELLOW}提示: 重新登录或执行 'source ~/.bashrc' 以加载环境变量${NC}"
echo ""
