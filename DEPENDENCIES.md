# llm_ros2 - Complete Dependencies Guide

## Overview
This document provides a comprehensive list of all dependencies required to reproduce the llm_ros2 robotics project. The project consists of four ROS 2 packages (LLM-based navigation and control system).

## Installation Methods

### Method 1: Using Python Script (Recommended)
The most flexible and feature-rich approach:

```bash
# View all dependencies without installing
python3 install_dependencies.py --list

# Full installation
python3 install_dependencies.py

# Skip system updates (faster if already updated)
python3 install_dependencies.py --skip-system

# Use different ROS distribution
python3 install_dependencies.py --ros-distro humble
```

### Method 2: Using Bash Script
Simple one-line installation:

```bash
chmod +x install_dependencies.sh
./install_dependencies.sh
```

### Method 3: Manual Installation with pip
If you prefer only Python packages:

```bash
pip3 install -r requirements.txt
```

## Complete Dependency List

### System Dependencies
- **Build Tools:**
  - `build-essential` - C/C++ compiler and build utilities
  - `cmake` - Build system
  - `git` - Version control

- **Python Development:**
  - `python3-pip` - Python package manager
  - `python3-dev` - Python development headers

- **Computer Vision:**
  - `libopencv-dev` - OpenCV development libraries
  - `python3-opencv` - Python OpenCV bindings

### ROS 2 Packages (Humble Distribution)
ROS 2 core messaging and control packages:

**Core ROS:**
- `ros-humble-rclpy` - Python ROS 2 client library
- `ros-humble-rclcpp` - C++ ROS 2 client library

**Message Types:**
- `ros-humble-sensor-msgs` - Sensor messages (Image, PointCloud2, etc.)
- `ros-humble-nav-msgs` - Navigation messages (OccupancyGrid, Odometry)
- `ros-humble-geometry-msgs` - Geometry messages (Twist, Pose, PoseStamped)
- `ros-humble-std-msgs` - Standard messages (Bool, String, etc.)
- `ros-humble-visualization-msgs` - RViz visualization markers

**Navigation & TF:**
- `ros-humble-nav2-msgs` - Nav2 action messages
- `ros-humble-tf2-ros` - Transform library
- `ros-humble-nav2-core` - Nav2 framework core

**Bridges & Filters:**
- `ros-humble-cv-bridge` - OpenCV to ROS Image bridge
- `ros-humble-message-filters` - Time synchronization filters

**Launch & Index:**
- `ros-humble-launch` - Launch file system
- `ros-humble-launch-ros` - ROS 2 launch extensions
- `ros-humble-ament-index-python` - Package path lookup

**Build & Testing:**
- `ros-humble-ament-cmake` - CMake build system wrapper
- `ros-humble-ament-copyright` - Copyright checker
- `ros-humble-ament-flake8` - Python linter
- `ros-humble-ament-pep257` - Python docstring checker

### Python Packages (pip)

| Package | Version | Purpose |
|---------|---------|---------|
| numpy | ≥1.21.0 | Numerical computing |
| opencv-python | ≥4.5.0 | Computer vision library |
| Pillow | ≥8.0.0 | Image processing |
| pydantic | ≥2.0.0 | Data validation |
| langchain-google-genai | ≥0.1.0 | Google Generative AI integration |
| langchain-core | ≥0.1.0 | LangChain core framework |
| ultralytics | ≥8.0.0 | YOLOv8 object detection |
| roboflow | ≥1.0.0 | Dataset management & download |
| PyYAML | ≥5.4.0 | YAML file handling |
| pytest | ≥7.0.0 | Testing framework |
| setuptools | ≥65.0.0 | Package building tools |

## Package Descriptions

### llm_navigation
Navigation package with frontier exploration and person detection:
- `frontier_explorer.py` - Local frontier detection using occupancy grid
- `frontier_selection.py` - Intelligent frontier goal selection
- `nav2_goal.py` - Navigation to goal implementation
- `person_detection_yolo.py` - YOLO-based person detection in camera feed
- `save_image.py` - Image capture and processing

**Key Dependencies:**
- `nav_msgs`, `geometry_msgs`, `visualization_msgs`
- `cv2`, `ultralytics` (YOLO)
- `numpy`, `rclpy`

### llm_prompt
LLM-based robot control and planning:
- `autonomous_mapping.py` - Autonomous mapping controller with LLM
- `llm_robot_controller.py` - LLM-based robot command generation
- `vision_controller.py` - Vision-based control system
- `execute.py` - Command execution interface
- `vision_functions.py` - Vision processing functions

**Key Dependencies:**
- `langchain-google-genai` - LLM integration
- `pydantic` - Data modeling
- `nav_msgs`, `geometry_msgs`
- `numpy`, `rclpy`

### llm_description
URDF and mesh definitions for robot models:
- Robot descriptions (ROSBOT, TurtleBot3)
- URDF/Xacro files
- Mesh files

**Key Dependencies:**
- `ament_cmake` (build only)

### llm_simulation
Gazebo simulation environment:
- Launch files for Gazebo simulation
- Robot models and world files
- Physics simulation configuration

**Key Dependencies:**
- `launch`, `launch_ros`
- `ament_cmake` (build only)

## Post-Installation Setup

After running the installation script:

```bash
# Navigate to workspace
cd /home/subham/llm_ros2

# Source ROS 2
source /opt/ros/humble/setup.bash

# Build the workspace
colcon build

# Source the install space
source install/setup.bash

# Run a node
ros2 run llm_navigation nav2_goal
```

## Environment Variables

Ensure the following are set:

```bash
# ROS 2 setup
source /opt/ros/humble/setup.bash

# Workspace setup
source ~/llm_ros2/install/setup.bash

# Optional: Set ROS_DOMAIN_ID to avoid conflicts
export ROS_DOMAIN_ID=42

# Set simulation time (if using gazebo)
export ROS_PARAM_USE_SIM_TIME=true
```

## Hardware Requirements

- **CPU:** Dual-core minimum, quad-core recommended
- **RAM:** 4GB minimum, 8GB recommended
- **Storage:** 5GB free space
- **GPU:** Optional (recommended for YOLO inference)

## Troubleshooting

### Issue: ROS packages not found
**Solution:** Verify ROS 2 installation:
```bash
dpkg -l | grep ros-humble
source /opt/ros/humble/setup.bash
```

### Issue: YOLO model download fails
**Solution:** Ensure internet connection and verify Roboflow API key

### Issue: CUDA/GPU errors with ultralytics
**Solution:** Install CUDA and cudnn:
```bash
pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Issue: OpenCV import errors
**Solution:** Reinstall cv2:
```bash
pip install --force-reinstall opencv-python
```

## References

- [ROS 2 Documentation](https://docs.ros.org/en/humble/)
- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [LangChain Documentation](https://python.langchain.com/)
- [Gazebo Documentation](https://gazebosim.org/docs)

## Notes

- This project requires ROS 2 Humble. Other distributions may require dependency adjustments.
- Python 3.8+ is required
- Ubuntu 22.04 LTS is the recommended host OS
- GPU support for YOLO is optional but recommended for real-time performance
