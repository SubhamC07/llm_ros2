# 🚀 Quick Start - llm_ros2 Dependencies

Welcome! This guide helps you quickly get the project running.

## ⚡ 30-Second Setup

```bash
# Choose ONE of these:

# Option 1: Full automated (Recommended)
python3 install_dependencies.py

# Option 2: Simple bash
bash install_dependencies.sh

# Option 3: Docker (any OS)
docker-compose up -d && docker-compose exec omokai_dev bash
```

## 📦 What Gets Installed

- **42 total dependencies** across 3 categories
- **12 system packages** (build tools, Python dev, OpenCV)
- **19 ROS 2 packages** (messaging, navigation, transforms)
- **11 Python packages** (numpy, opencv, YOLO, LangChain, etc.)

## 🎯 Installation Methods

| Method | Command | Best For |
|--------|---------|----------|
| **Python Script** | `python3 install_dependencies.py` | Full control, Linux/Ubuntu |
| **Bash Script** | `bash install_dependencies.sh` | Quick setup, Linux/Ubuntu |
| **Docker** | `docker-compose up -d` | Any OS, reproducible |
| **pip Only** | `pip3 install -r requirements.txt` | ROS already installed |
| **View Only** | `python3 install_dependencies.py --list` | Just see dependencies |

## 📚 After Installation

```bash
# 1. Setup environment
source setup_env.sh

# 2. Build workspace
colcon build

# 3. Run a node
ros2 run llm_navigation nav2_goal
```

## 📖 Documentation Files

Created in `/home/subham/llm_ros2/`:

| File | Purpose |
|------|---------|
| `INSTALLATION_SUMMARY.md` | 📋 Index of all files |
| `SETUP.md` | 📚 Complete setup guide |
| `DEPENDENCIES.md` | 📖 Detailed dependency list |
| `requirements.txt` | 🐍 Python packages |
| `dependencies.yaml` | 📋 Machine-readable config |
| `setup_env.sh` | ⚙️ Environment setup |
| `dependencies_reference.py` | 🔍 Interactive reference tool |

## 🔍 Reference Tools

**Interactive menu:**
```bash
python3 dependencies_reference.py
```

**Quick lookup:**
```bash
python3 dependencies_reference.py --system     # System deps
python3 dependencies_reference.py --ros        # ROS deps
python3 dependencies_reference.py --python     # Python deps
python3 dependencies_reference.py --stats      # Statistics
python3 dependencies_reference.py --all        # Everything
```

## ✅ Verify Installation

```bash
# Check Python packages
python3 -c "import cv2, numpy, ultralytics, pydantic; print('✓ OK')"

# Check ROS 2
ros2 --version
echo $ROS_DISTRO

# Check workspace packages
ros2 pkg list | grep llm

# Check YOLO
python3 -c "from ultralytics import YOLO; print('✓ YOLO ready')"
```

## 🆘 Troubleshooting

**Permission denied:**
```bash
chmod +x install_dependencies.sh
chmod +x install_dependencies.py
```

**ROS 2 not found:**
```bash
# Install ROS 2 Humble first:
# https://docs.ros.org/en/humble/Installation.html
```

**YOLO download fails:**
```bash
# Clear cache and retry
rm -rf ~/.cache/ultralytics/
python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

## 📊 System Requirements

- **OS:** Ubuntu 22.04 LTS (or any with ROS 2 Humble)
- **CPU:** Dual-core minimum
- **RAM:** 4GB minimum, 8GB recommended
- **Disk:** 5GB free
- **Python:** 3.8+
- **Internet:** Required for downloads

## 🗂️ Project Structure

```
llm_ros2/
├── src/
│   ├── llm_description/     # Robot URDF/meshes
│   ├── llm_prompt/          # LLM control system
│   ├── llm_navigation/       # Navigation & detection
│   └── llm_simulation/       # Gazebo simulation
├── install_dependencies.py   # 🌟 Main installer
├── install_dependencies.sh   # Bash installer
├── requirements.txt          # Python packages
├── dependencies.yaml         # Dependency manifest
├── setup_env.sh              # Environment setup
├── Dockerfile                # Docker container
├── docker-compose.yml        # Docker compose config
├── dependencies_reference.py # Reference tool
├── SETUP.md                  # Setup guide
├── DEPENDENCIES.md           # Detailed docs
├── INSTALLATION_SUMMARY.md   # File index
└── README.md                 # This file
```

## 🎓 Workflow Example

```bash
# 1. Install
python3 install_dependencies.py

# 2. Setup environment
source setup_env.sh

# 3. Navigate to workspace
cd /home/subham/llm_ros2

# 4. Build
colcon build

# 5. Source built packages
source install/setup.bash

# 6. Run nodes
ros2 run llm_navigation frontier_explorer
ros2 run llm_navigation person_detection_yolo
ros2 run llm_prompt llm_robot_controller
```

## 📞 Getting Help

1. **Quick reference:** `python3 dependencies_reference.py`
2. **Full guide:** Read `SETUP.md`
3. **Detailed deps:** Read `DEPENDENCIES.md`
4. **Troubleshooting:** Check section above
5. **Official docs:**
   - [ROS 2 Humble](https://docs.ros.org/en/humble/)
   - [YOLOv8](https://docs.ultralytics.com/)
   - [LangChain](https://python.langchain.com/)

## 🎯 Next Steps

After successful installation:

1. ✅ Verify all packages are installed
2. ✅ Build the workspace: `colcon build`
3. ✅ Source install: `source install/setup.bash`
4. ✅ Run tests: `colcon test`
5. ✅ Launch simulation: `ros2 launch llm_simulation gz.launch.py`

---

**Ready? Start with:** `python3 install_dependencies.py`

**Questions?** Check the detailed guides in this directory.

Happy coding! 🤖
