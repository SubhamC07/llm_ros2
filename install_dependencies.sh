#!/bin/bash
# Dependencies Installation Script for llm_ros2
# This script installs all necessary dependencies to reproduce the project

set -e

echo "=========================================="
echo "Installing llm_ros2 Dependencies"
echo "=========================================="

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Step 1: Update system packages
echo ""
echo "[1/4] Updating system package manager..."
sudo apt-get update
sudo apt-get upgrade -y

# Step 2: Install system-level dependencies
echo ""
echo "[2/4] Installing system dependencies..."
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    build-essential \
    git \
    cmake \
    libopencv-dev \
    python3-opencv

# Step 3: Install ROS 2 packages
echo ""
echo "[3/4] Installing ROS 2 packages..."
sudo apt-get install -y \
    ros-${ROS_DISTRO:-humble}-rclpy \
    ros-${ROS_DISTRO:-humble}-rclcpp \
    ros-${ROS_DISTRO:-humble}-sensor-msgs \
    ros-${ROS_DISTRO:-humble}-nav-msgs \
    ros-${ROS_DISTRO:-humble}-geometry-msgs \
    ros-${ROS_DISTRO:-humble}-visualization-msgs \
    ros-${ROS_DISTRO:-humble}-std-msgs \
    ros-${ROS_DISTRO:-humble}-nav2-msgs \
    ros-${ROS_DISTRO:-humble}-tf2-ros \
    ros-${ROS_DISTRO:-humble}-cv-bridge \
    ros-${ROS_DISTRO:-humble}-message-filters \
    ros-${ROS_DISTRO:-humble}-launch \
    ros-${ROS_DISTRO:-humble}-launch-ros \
    ros-${ROS_DISTRO:-humble}-ament-index-python \
    ros-${ROS_DISTRO:-humble}-ament-cmake \
    ros-${ROS_DISTRO:-humble}-ament-copyright \
    ros-${ROS_DISTRO:-humble}-ament-flake8 \
    ros-${ROS_DISTRO:-humble}-ament-pep257 \
    ros-${ROS_DISTRO:-humble}-nav2-core

# Step 4: Install Python packages
echo ""
echo "[4/4] Installing Python packages..."
pip3 install --upgrade pip
pip3 install -r "${SCRIPT_DIR}/requirements.txt"

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "To use the workspace, run:"
echo "  cd ${SCRIPT_DIR}"
echo "  source /opt/ros/${ROS_DISTRO:-humble}/setup.bash"
echo "  colcon build"
echo "  source install/setup.bash"
echo ""
