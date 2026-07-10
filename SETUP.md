# omokai_ws - Installation & Setup Guide

A complete guide to reproducing the omokai_ws robotics project environment with all dependencies.

## Quick Start

Choose one of the installation methods below:

### Option 1: Python Script (Recommended) ✨
The most flexible and informative approach:

```bash
# View all dependencies
python3 install_dependencies.py --list

# Full automated installation
python3 install_dependencies.py

# Custom ROS distribution
python3 install_dependencies.py --ros-distro humble
```

### Option 2: Bash Script
Simple one-liner installation:

```bash
chmod +x install_dependencies.sh
./install_dependencies.sh
```

### Option 3: Docker (Fully Isolated) 🐳
No system dependencies needed:

```bash
# Build Docker image
docker build -t omokai:humble-latest .

# Run development container
docker run -it --rm -v $(pwd):/home/omokai_ws omokai:humble-latest bash

# Or with docker-compose
docker-compose up -d
docker-compose exec omokai_dev bash
```

### Option 4: pip Only
If ROS 2 is already installed:

```bash
pip3 install -r requirements.txt
```

## Installation Methods Explained

### Method 1: Python Script (install_dependencies.py)

**Features:**
- ✅ Detailed progress reporting
- ✅ Modular installation (skip steps if needed)
- ✅ Error handling and retry logic
- ✅ Dependency verification
- ✅ List dependencies without installing

**Usage:**
```bash
# Show all dependencies
python3 install_dependencies.py --list

# Full installation
python3 install_dependencies.py

# Skip system updates (faster)
python3 install_dependencies.py --skip-system

# Skip ROS packages (if already installed)
python3 install_dependencies.py --skip-ros --ros-distro humble
```

**Best for:** Users who want control and visibility

---

### Method 2: Bash Script (install_dependencies.sh)

**Features:**
- ✅ Simple and straightforward
- ✅ All dependencies in one script
- ✅ Automatic ROS distro detection
- ✅ Post-installation guidance

**Usage:**
```bash
./install_dependencies.sh
```

**Best for:** Quick setup on Linux/Ubuntu

---

### Method 3: Docker (Dockerfile + docker-compose.yml)

**Features:**
- ✅ Completely isolated environment
- ✅ Reproducible across different machines
- ✅ No system pollution
- ✅ Easy to clean up
- ✅ GPU support optional

**Usage:**

```bash
# Build image
docker build -t omokai:humble .

# Run container
docker run -it --rm \
  -v $(pwd):/home/omokai_ws \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  omokai:humble bash

# Or simpler with docker-compose
docker-compose up -d
docker-compose exec omokai_dev bash
```

**Best for:** CI/CD pipelines, different OS, reproducibility

---

### Method 4: pip Requirements (requirements.txt)

For Python packages only:

```bash
pip3 install -r requirements.txt
```

**Prerequisites:**
- ROS 2 Humble already installed
- Python 3.8+
- System dev packages installed

**Best for:** Minimal setup, ROS already present

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Ubuntu 20.04 | Ubuntu 22.04 LTS |
| **CPU** | Dual-core | Quad-core or better |
| **RAM** | 4 GB | 8 GB |
| **Disk** | 5 GB free | 10+ GB free |
| **GPU** | Optional | Recommended (NVIDIA) |
| **Python** | 3.8 | 3.10+ |

## Complete Dependency List

### System Packages
```
build-essential cmake git python3-pip python3-dev 
libopencv-dev python3-opencv
```

### ROS 2 Packages (Humble)
```
rclpy rclcpp sensor-msgs nav-msgs geometry-msgs
visualization-msgs std-msgs nav2-msgs tf2-ros cv-bridge
message-filters launch launch-ros ament-index-python
ament-cmake ament-copyright ament-flake8 ament-pep257
```

### Python Packages
```
numpy>=1.21.0
opencv-python>=4.5.0
Pillow>=8.0.0
pydantic>=2.0.0
langchain-google-genai>=0.1.0
langchain-core>=0.1.0
ultralytics>=8.0.0
roboflow>=1.0.0
PyYAML>=5.4.0
pytest>=7.0.0
setuptools>=65.0.0
```

## Post-Installation Setup

After successful installation:

```bash
# Navigate to workspace
cd /home/subham/omokai_ws

# Source ROS 2 setup
source /opt/ros/humble/setup.bash

# Build the workspace
colcon build

# Source the built packages
source install/setup.bash

# Verify installation
ros2 pkg list | grep llm
```

## Verify Installation

Check if everything is installed correctly:

```bash
# Check ROS 2
ros2 --version

# Check Python packages
python3 -c "import cv2, numpy, ultralytics, langchain_google_genai; print('✓ All packages imported successfully')"

# Check ROS packages
ros2 pkg list | grep -E "(sensor|nav|geometry|visualization|std_msgs|nav2|tf2|cv_bridge)"

# Check YOLO model
python3 -c "from ultralytics import YOLO; print('✓ YOLO available')"

# List available nodes
ros2 pkg list | grep llm
```

## Environment Variables

Set these in your `.bashrc` or `.zshrc`:

```bash
# ROS 2 setup
source /opt/ros/humble/setup.bash

# Workspace setup
source ~/omokai_ws/install/setup.bash

# Optional ROS settings
export ROS_DOMAIN_ID=42                    # Unique ID to avoid conflicts
export ROS_PARAM_USE_SIM_TIME=true         # Use simulation time if using Gazebo
export ROS_LOG_DIR=~/.ros/log              # Log directory
```

## File Descriptions

| File | Purpose |
|------|---------|
| `requirements.txt` | Python pip dependencies |
| `install_dependencies.py` | Python installation script |
| `install_dependencies.sh` | Bash installation script |
| `dependencies.yaml` | YAML dependency manifest |
| `Dockerfile` | Docker containerization |
| `docker-compose.yml` | Docker Compose configuration |
| `DEPENDENCIES.md` | Detailed dependency documentation |
| `SETUP.md` | This file |

## Troubleshooting

### Issue: Permission denied running scripts
```bash
chmod +x install_dependencies.sh
chmod +x install_dependencies.py
```

### Issue: pip/apt command not found
```bash
# Install pip
sudo apt-get install python3-pip

# Update pip
pip3 install --upgrade pip
```

### Issue: ROS 2 not found
```bash
# Check ROS 2 installation
ls /opt/ros/

# If not installed, follow official ROS 2 setup:
# https://docs.ros.org/en/humble/Installation.html
```

### Issue: YOLO model download fails
```bash
# Check internet connection
ping google.com

# Clear YOLO cache
rm -rf ~/.cache/ultralytics/

# Re-download model
python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### Issue: Docker build fails
```bash
# Rebuild with no cache
docker build --no-cache -t omokai:humble .

# Check Docker daemon
docker ps
```

### Issue: OpenCV import errors
```bash
# Reinstall OpenCV
pip3 install --force-reinstall opencv-python

# Or use system package
sudo apt-get install python3-opencv
```

## Building the Workspace

```bash
# Clean build
cd ~/omokai_ws
rm -rf build install log
colcon build

# Build specific package
colcon build --packages-select llm_navigation

# Build with testing
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
```

## Running Nodes

```bash
# List available nodes
ros2 pkg list | grep llm

# Run a node
ros2 run llm_navigation nav2_goal

# Run with parameters
ros2 run llm_navigation frontier_explorer --ros-args -p use_sim_time:=true

# Run in launch file
ros2 launch llm_simulation gz.launch.py
```

## GPU Support (Optional)

For YOLO acceleration with GPU:

```bash
# NVIDIA GPU support
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify CUDA availability
python3 -c "import torch; print(torch.cuda.is_available())"

# Use GPU in code
from ultralytics import YOLO
model = YOLO('yolov8n.pt')
results = model.predict(source='image.jpg', device=0)  # device=0 for GPU
```

## Getting Help

1. **Check DEPENDENCIES.md** for detailed dependency information
2. **Review package.xml** files in each package
3. **Check official documentation:**
   - [ROS 2 Humble](https://docs.ros.org/en/humble/)
   - [YOLOv8](https://docs.ultralytics.com/)
   - [LangChain](https://python.langchain.com/)
   - [Gazebo](https://gazebosim.org/)

## Next Steps

1. ✅ Install dependencies using your preferred method
2. ✅ Build the workspace: `colcon build`
3. ✅ Source the install space: `source install/setup.bash`
4. ✅ Run the nodes: `ros2 run llm_navigation ...`
5. ✅ Check the individual package documentation

---

**Questions or Issues?** Refer to DEPENDENCIES.md or the package-specific README files.
