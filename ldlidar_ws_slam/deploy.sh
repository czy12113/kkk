#!/bin/bash
########################################
# LD14P SLAM工作空间打包和部署脚本
########################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置参数
WORKSPACE_DIR="/home/kkk/ldlidar_ws_slam"
RDK_USER="sunrise"
RDK_IP="192.168.128.10"
RDK_PASS="sunrise"
PACKAGE_NAME="ldlidar_slam.tar.gz"

echo ""
echo "========================================"
echo "  LD14P SLAM 打包部署工具"
echo "========================================"
echo ""

# 检查工作空间
echo -e "${YELLOW}[1/4] 检查工作空间...${NC}"
if [ ! -d "$WORKSPACE_DIR/src" ]; then
    echo -e "${RED}错误: 找不到src目录！${NC}"
    exit 1
fi

cd "$WORKSPACE_DIR"
echo -e "${GREEN}工作空间: $WORKSPACE_DIR${NC}"

# 编译工作空间（可选）
echo ""
echo -e "${YELLOW}[2/4] 编译工作空间...${NC}"
read -p "是否需要编译工作空间？(y/n，默认n): " compile_choice
compile_choice=${compile_choice:-n}

if [ "$compile_choice" = "y" ] || [ "$compile_choice" = "Y" ]; then
    echo "正在编译，请稍候..."
    colcon build --symlink-install
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}编译完成！${NC}"
    else
        echo -e "${RED}编译失败！请检查错误信息。${NC}"
        exit 1
    fi
else
    echo "跳过编译步骤"
fi

# 打包工作空间
echo ""
echo -e "${YELLOW}[3/4] 打包工作空间...${NC}"

# 删除旧的打包文件
if [ -f "$PACKAGE_NAME" ]; then
    rm -f "$PACKAGE_NAME"
    echo "已删除旧的打包文件"
fi

# 打包src目录（在RDK上重新编译）
echo "正在打包src目录..."
tar -czf "$PACKAGE_NAME" src

if [ $? -eq 0 ]; then
    PACKAGE_SIZE=$(du -h "$PACKAGE_NAME" | cut -f1)
    echo -e "${GREEN}打包完成: $PACKAGE_NAME (大小: $PACKAGE_SIZE)${NC}"
else
    echo -e "${RED}打包失败！${NC}"
    exit 1
fi

# 传输到RDK X5
echo ""
echo -e "${YELLOW}[4/5] 传输到RDK X5...${NC}"
echo "目标: $RDK_USER@$RDK_IP"
echo "正在传输打包文件..."

# 使用scp传输打包文件
scp "$PACKAGE_NAME" "$RDK_USER@$RDK_IP:~/"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 打包文件传输完成${NC}"
    
    # 传输配置脚本
    echo ""
    echo -e "${YELLOW}[5/5] 传输配置脚本...${NC}"
    scp rdk_setup.sh "$RDK_USER@$RDK_IP:~/"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 配置脚本传输完成${NC}"
    else
        echo -e "${YELLOW}! 配置脚本传输失败（可手动传输）${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}========================================"
    echo "  打包部署完成！"
    echo "========================================${NC}"
    echo ""
    echo "文件已传输到: /home/$RDK_USER/"
    echo "  - $PACKAGE_NAME"
    echo "  - rdk_setup.sh"
    echo ""
    echo -e "${YELLOW}下一步操作（推荐）:${NC}"
    echo ""
    echo "1. SSH连接到RDK:"
    echo "   ssh $RDK_USER@$RDK_IP"
    echo ""
    echo "2. 运行自动配置脚本:"
    echo "   chmod +x rdk_setup.sh"
    echo "   ./rdk_setup.sh"
    echo ""
    echo "3. 启动SLAM建图:"
    echo "   source ~/ldlidar_ws_slam/install/setup.bash"
    echo "   ros2 launch ldlidar slam_mapping.launch.py"
    echo ""
    echo -e "${YELLOW}或者手动配置（参考: 手动安装指南.md）${NC}"
    echo ""
    
    # 询问是否自动SSH连接
    read -p "是否现在SSH连接到RDK？(y/n): " ssh_choice
    if [ "$ssh_choice" = "y" ] || [ "$ssh_choice" = "Y" ]; then
        ssh "$RDK_USER@$RDK_IP"
    fi
else
    echo ""
    echo -e "${RED}传输失败！请检查:${NC}"
    echo "1. RDK是否开机并连接网络"
    echo "2. IP地址是否正确: $RDK_IP"
    echo "3. SSH服务是否运行"
    echo "4. 网络是否互通: ping $RDK_IP"
    exit 1
fi
