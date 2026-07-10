#!/bin/bash
# llm_ros2 Environment Setup
# Source this file to set up the environment for the workspace
# Usage: source setup_env.sh

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=========================================="
echo "Setting up llm_ros2 environment"
echo "=========================================="

# Check if ROS 2 is already sourced
if [ -z "$ROS_DISTRO" ]; then
    echo ""
    echo "⚠️  ROS 2 not found. Attempting to source..."
    
    # Try common ROS 2 installation paths
    if [ -f "/opt/ros/humble/setup.bash" ]; then
        echo "  Found ROS 2 Humble at /opt/ros/humble"
        source /opt/ros/humble/setup.bash
    elif [ -f "/opt/ros/iron/setup.bash" ]; then
        echo "  Found ROS 2 Iron at /opt/ros/iron"
        source /opt/ros/iron/setup.bash
    elif [ -f "/opt/ros/rolling/setup.bash" ]; then
        echo "  Found ROS 2 Rolling at /opt/ros/rolling"
        source /opt/ros/rolling/setup.bash
    else
        echo "  ✗ ROS 2 not found. Please install ROS 2 first."
        echo "  Visit: https://docs.ros.org/en/humble/Installation.html"
        return 1
    fi
fi

echo "✓ ROS Distribution: $ROS_DISTRO"
echo "  ROS Install space: $AMENT_PREFIX_PATH"

# Set workspace variables
export WORKSPACE_ROOT="${SCRIPT_DIR}"
export llm_ros2="${WORKSPACE_ROOT}"

echo ""
echo "Setting workspace paths..."

# Source the local workspace if built
if [ -f "${WORKSPACE_ROOT}/install/setup.bash" ]; then
    echo "  Sourcing workspace install space..."
    source "${WORKSPACE_ROOT}/install/setup.bash"
    echo "✓ Workspace sourced"
else
    echo "  ⚠️  Workspace not built yet. Run: colcon build"
    echo "  After building, this script will auto-source the workspace."
fi

# Set ROS parameters
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-42}
export ROS_PARAM_USE_SIM_TIME=${ROS_PARAM_USE_SIM_TIME:-false}

echo ""
echo "Environment variables set:"
echo "  WORKSPACE_ROOT=${WORKSPACE_ROOT}"
echo "  llm_ros2=${llm_ros2}"
echo "  ROS_DISTRO=${ROS_DISTRO}"
echo "  ROS_DOMAIN_ID=${ROS_DOMAIN_ID}"
echo "  ROS_PARAM_USE_SIM_TIME=${ROS_PARAM_USE_SIM_TIME}"

# Add workspace scripts to PATH
if [[ ":$PATH:" != *":${WORKSPACE_ROOT}:":* ]]; then
    export PATH="${WORKSPACE_ROOT}:${PATH}"
fi

# Function to verify installation
verify_installation() {
    echo ""
    echo "=========================================="
    echo "Verifying Installation"
    echo "=========================================="
    
    # Check Python packages
    echo ""
    echo "Python packages:"
    python3 -c "
import sys
packages = ['numpy', 'cv2', 'ultralytics', 'pydantic', 'langchain_google_genai', 'langchain_core', 'roboflow']
missing = []
for pkg in packages:
    try:
        __import__(pkg)
        print(f'  ✓ {pkg}')
    except ImportError:
        print(f'  ✗ {pkg} (MISSING)')
        missing.append(pkg)

if missing:
    print(f'\nMissing packages: {missing}')
    print('Run: pip3 install -r requirements.txt')
" 2>/dev/null || echo "  ✗ Python verification failed"
    
    # Check ROS packages
    echo ""
    echo "ROS 2 packages:"
    if command -v ros2 &> /dev/null; then
        ros2 pkg list | grep -E "llm_" | while read pkg; do
            echo "  ✓ $pkg"
        done
        
        if [ -z "$(ros2 pkg list | grep llm_)" ]; then
            echo "  ⚠️  No llm_* packages found. Build workspace with: colcon build"
        fi
    else
        echo "  ✗ ros2 command not found"
    fi
    
    # Check YOLO
    echo ""
    echo "Additional checks:"
    python3 -c "from ultralytics import YOLO; print('  ✓ YOLOv8 available')" 2>/dev/null || echo "  ✗ YOLOv8 not available"
    
    echo ""
}

# Function to build workspace
build_workspace() {
    echo ""
    echo "=========================================="
    echo "Building Workspace"
    echo "=========================================="
    cd "${WORKSPACE_ROOT}"
    colcon build --symlink-install
    
    # Re-source after building
    if [ -f "${WORKSPACE_ROOT}/install/setup.bash" ]; then
        source "${WORKSPACE_ROOT}/install/setup.bash"
        echo "✓ Workspace rebuilt and sourced"
    fi
}

# Function to show helpful aliases
show_aliases() {
    echo ""
    echo "=========================================="
    echo "Useful Aliases (add to ~/.bashrc):"
    echo "=========================================="
    echo ""
    echo "# Navigate to workspace"
    echo "alias cdo='cd ${WORKSPACE_ROOT}'"
    echo ""
    echo "# Build workspace"
    echo "alias build_ws='cd ${WORKSPACE_ROOT} && colcon build --symlink-install'"
    echo ""
    echo "# Source workspace"
    echo "alias source_ws='source ${WORKSPACE_ROOT}/install/setup.bash'"
    echo ""
    echo "# Run common nodes"
    echo "alias nav2_goal='ros2 run llm_navigation nav2_goal'"
    echo "alias frontier_explorer='ros2 run llm_navigation frontier_explorer'"
    echo "alias person_detection='ros2 run llm_navigation person_detection_yolo'"
    echo ""
}

echo ""
echo "=========================================="
echo "✓ Environment setup complete!"
echo "=========================================="
echo ""
echo "Available commands:"
echo "  • verify_installation  - Check all dependencies"
echo "  • build_workspace      - Build the workspace"
echo "  • show_aliases         - Show useful bash aliases"
echo ""
echo "To add to your bashrc:"
echo "  echo 'source ${WORKSPACE_ROOT}/setup_env.sh' >> ~/.bashrc"
echo ""
