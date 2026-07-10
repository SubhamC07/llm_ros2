# omokai_ws Installation Files Summary

This document summarizes all the dependency and installation files generated for the omokai_ws robotics project.

## 📋 Generated Files

### 1. **requirements.txt** 
- **Purpose:** Python pip packages only
- **Usage:** `pip3 install -r requirements.txt`
- **Use when:** You only need Python packages or ROS is already installed

### 2. **install_dependencies.py** ⭐ RECOMMENDED
- **Purpose:** Complete Python-based installation script
- **Usage:** 
  ```bash
  python3 install_dependencies.py          # Full installation
  python3 install_dependencies.py --list   # View dependencies only
  python3 install_dependencies.py --skip-system  # Faster if updated
  ```
- **Features:** 
  - Color-coded output
  - Step-by-step installation
  - Error handling
  - Modular (skip steps if needed)
  - Dependency verification

### 3. **install_dependencies.sh**
- **Purpose:** Bash script for quick installation
- **Usage:** `./install_dependencies.sh`
- **Features:**
  - Simple one-liner
  - Good for CI/CD
  - Auto-detects ROS distro
  - Concise logging

### 4. **Dockerfile**
- **Purpose:** Docker container with all dependencies
- **Usage:**
  ```bash
  docker build -t omokai:humble .
  docker run -it omokai:humble bash
  ```
- **Features:**
  - Completely isolated environment
  - Reproducible across machines
  - GPU support optional
  - No system pollution

### 5. **docker-compose.yml**
- **Purpose:** Simplified Docker orchestration
- **Usage:**
  ```bash
  docker-compose up -d
  docker-compose exec omokai_dev bash
  ```
- **Features:**
  - Volume mounting
  - Environment variables
  - Easy cleanup
  - X11 forwarding for GUI

### 6. **dependencies.yaml**
- **Purpose:** YAML manifest of all dependencies
- **Usage:** Reference or import into other tools
- **Format:** Machine-readable dependency specification

### 7. **setup_env.sh**
- **Purpose:** Environment setup and verification
- **Usage:** `source setup_env.sh`
- **Features:**
  - Auto-source ROS 2
  - Auto-source workspace
  - Verification commands
  - Helpful aliases

### 8. **DEPENDENCIES.md**
- **Purpose:** Detailed dependency documentation
- **Content:** Complete list, descriptions, and purposes
- **Use for:** Understanding what each dependency does

### 9. **SETUP.md**
- **Purpose:** Comprehensive setup guide
- **Content:** All methods, troubleshooting, next steps
- **Use for:** Learning all available options

### 10. **INSTALLATION_SUMMARY.md**
- **Purpose:** This file - quick reference guide

---

## 🚀 Quick Start Guide

### 👤 For Linux/Ubuntu Users

**Option A - Fully Automated (Recommended):**
```bash
python3 install_dependencies.py
```

**Option B - Simpler Script:**
```bash
bash install_dependencies.sh
```

**Option C - Manual Control:**
```bash
# Just install Python packages
pip3 install -r requirements.txt

# Then manually install ROS 2 system packages
sudo apt-get install ros-humble-rclpy ros-humble-nav-msgs ...
```

### 🐳 For Docker Users (Any OS)

```bash
# Build and run
docker-compose up -d
docker-compose exec omokai_dev bash
```

### 📋 To View Dependencies Only

```bash
python3 install_dependencies.py --list
```

Or check:
- `requirements.txt` (Python packages)
- `dependencies.yaml` (Full structure)
- `DEPENDENCIES.md` (Detailed info)

---

## 📚 Dependency Categories

### System Dependencies (12 packages)
- Build tools: build-essential, cmake, git
- Python dev: python3-pip, python3-dev  
- Computer vision: libopencv-dev, python3-opencv

### ROS 2 Packages (19 packages)
- Core: rclpy, rclcpp
- Messages: sensor_msgs, nav_msgs, geometry_msgs
- Navigation: nav2_msgs, nav2_core
- Bridges: cv_bridge, message_filters
- Build tools: ament_cmake, ament_copyright

### Python Packages (11 packages)
- CV: numpy, opencv-python, Pillow
- LLM: langchain-google-genai, langchain-core
- AI: ultralytics, roboflow
- Data: pydantic, PyYAML
- Tools: pytest, setuptools

**Total: 42 dependencies**

---

## ✅ Verification Checklist

After installation, verify with:

```bash
# Check ROS 2
ros2 --version
echo $ROS_DISTRO

# Check Python packages
python3 -c "import cv2, numpy, ultralytics, pydantic; print('OK')"

# Check workspace
ros2 pkg list | grep llm

# Check YOLO
python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# Build workspace
colcon build

# Source and run
source install/setup.bash
ros2 run llm_navigation nav2_goal
```

---

## 🔧 Post-Installation

### 1. Build the Workspace
```bash
cd /home/subham/omokai_ws
colcon build
```

### 2. Source Setup
```bash
source install/setup.bash
```

### 3. Optional: Add to .bashrc
```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "source /home/subham/omokai_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### 4. Run a Node
```bash
ros2 run llm_navigation nav2_goal
```

---

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| Permission denied | `chmod +x install_dependencies.sh` |
| ROS not found | `apt-get install ros-humble-ros-base` |
| pip command missing | `sudo apt-get install python3-pip` |
| YOLO model download fails | Check internet, run: `python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"` |
| Docker build fails | `docker build --no-cache -t omokai:humble .` |
| OpenCV errors | `pip3 install --force-reinstall opencv-python` |

---

## 📖 Documentation Files

| File | Purpose |
|------|---------|
| DEPENDENCIES.md | Complete dependency documentation |
| SETUP.md | Step-by-step setup guide |
| requirements.txt | Python pip packages |
| dependencies.yaml | YAML dependency manifest |
| Dockerfile | Docker environment |
| docker-compose.yml | Docker orchestration |
| setup_env.sh | Environment configuration |

---

## 🎯 Recommended Workflow

1. **Choose installation method:**
   - Python script: `python3 install_dependencies.py`
   - Bash script: `bash install_dependencies.sh`
   - Docker: `docker-compose up -d`

2. **Verify installation:**
   - `python3 install_dependencies.py --list` to check
   - Or source `setup_env.sh` to run verification

3. **Build workspace:**
   - `colcon build`

4. **Source and run:**
   - `source install/setup.bash`
   - `ros2 run llm_navigation nav2_goal`

---

## 🔗 Related Packages

- **llm_description:** Robot URDF and meshes
- **llm_navigation:** Navigation, frontier exploration, person detection  
- **llm_prompt:** LLM-based robot control
- **llm_simulation:** Gazebo simulation environment

---

## 📞 Need Help?

1. Read `SETUP.md` for comprehensive guide
2. Check `DEPENDENCIES.md` for detailed info
3. Review package-specific documentation in each folder
4. Check official docs:
   - [ROS 2 Humble](https://docs.ros.org/en/humble/)
   - [YOLOv8](https://docs.ultralytics.com/)
   - [LangChain](https://python.langchain.com/)

---

## 📊 Installation Statistics

- **Total Dependencies:** 42
- **System Packages:** 12
- **ROS 2 Packages:** 19  
- **Python Packages:** 11
- **Installation Time:** 10-30 minutes (depending on network/system)
- **Disk Space Needed:** ~5-10 GB

---

**Last Updated:** 2024
**Project:** omokai_ws - LLM-based Autonomous Robot Navigation
**ROS Distribution:** Humble
