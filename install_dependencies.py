#!/usr/bin/env python3
"""
Dependency Installation Script for omokai_ws
This script handles all dependency installation in a cross-platform manner
"""

import subprocess
import sys
import os
from pathlib import Path


class DependencyInstaller:
    """Installs all dependencies for the omokai_ws project"""
    
    def __init__(self):
        self.ros_distro = os.getenv('ROS_DISTRO', 'humble')
        self.python_executable = sys.executable
        self.workspace_root = Path(__file__).parent
        
    def run_command(self, cmd, description=""):
        """Execute a shell command"""
        print(f"\n▶ {description}")
        print(f"  Command: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, check=True, capture_output=False)
            print(f"✓ {description} completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ {description} failed with error code {e.returncode}")
            return False
    
    def update_system_packages(self):
        """Update system package manager"""
        print("\n" + "="*50)
        print("Step 1: Updating system packages")
        print("="*50)
        
        self.run_command(
            ["sudo", "apt-get", "update"],
            "Updating apt cache"
        )
        self.run_command(
            ["sudo", "apt-get", "upgrade", "-y"],
            "Upgrading system packages"
        )
    
    def install_system_dependencies(self):
        """Install system-level dependencies"""
        print("\n" + "="*50)
        print("Step 2: Installing system dependencies")
        print("="*50)
        
        packages = [
            "python3-pip",
            "python3-dev",
            "build-essential",
            "git",
            "cmake",
            "libopencv-dev",
            "python3-opencv",
        ]
        
        self.run_command(
            ["sudo", "apt-get", "install", "-y"] + packages,
            "Installing system packages"
        )
    
    def install_ros_packages(self):
        """Install ROS 2 packages"""
        print("\n" + "="*50)
        print("Step 3: Installing ROS 2 packages")
        print("="*50)
        
        ros_packages = [
            "rclpy",
            "rclcpp",
            "sensor-msgs",
            "nav-msgs",
            "geometry-msgs",
            "visualization-msgs",
            "std-msgs",
            "nav2-msgs",
            "tf2-ros",
            "cv-bridge",
            "message-filters",
            "launch",
            "launch-ros",
            "ament-index-python",
            "ament-cmake",
            "ament-copyright",
            "ament-flake8",
            "ament-pep257",
            "nav2-core",
        ]
        
        ros_packages_with_distro = [
            f"ros-{self.ros_distro}-{pkg}" for pkg in ros_packages
        ]
        
        self.run_command(
            ["sudo", "apt-get", "install", "-y"] + ros_packages_with_distro,
            "Installing ROS 2 packages"
        )
    
    def install_python_packages(self):
        """Install Python packages from requirements.txt"""
        print("\n" + "="*50)
        print("Step 4: Installing Python packages")
        print("="*50)
        
        requirements_file = self.workspace_root / "requirements.txt"
        
        if not requirements_file.exists():
            print(f"✗ requirements.txt not found at {requirements_file}")
            return False
        
        # Upgrade pip
        self.run_command(
            [self.python_executable, "-m", "pip", "install", "--upgrade", "pip"],
            "Upgrading pip"
        )
        
        # Install from requirements.txt
        self.run_command(
            [self.python_executable, "-m", "pip", "install", "-r", str(requirements_file)],
            "Installing Python packages from requirements.txt"
        )
        
        return True
    
    def install_all(self):
        """Install all dependencies"""
        print("\n" + "="*70)
        print("omokai_ws Dependency Installation")
        print("="*70)
        print(f"ROS Distribution: {self.ros_distro}")
        print(f"Python Executable: {self.python_executable}")
        print(f"Workspace Root: {self.workspace_root}")
        
        try:
            self.update_system_packages()
            self.install_system_dependencies()
            self.install_ros_packages()
            self.install_python_packages()
            
            print("\n" + "="*70)
            print("✓ Installation Complete!")
            print("="*70)
            print("\nNext steps:")
            print(f"  cd {self.workspace_root}")
            print(f"  source /opt/ros/{self.ros_distro}/setup.bash")
            print(f"  colcon build")
            print(f"  source install/setup.bash")
            print()
            
            return True
            
        except Exception as e:
            print(f"\n✗ Installation failed: {e}")
            return False


def print_dependency_list():
    """Print a detailed dependency list"""
    print("\n" + "="*70)
    print("Dependency Summary for omokai_ws")
    print("="*70)
    
    print("\n📦 System Dependencies:")
    print("  • python3-pip, python3-dev")
    print("  • build-essential, git, cmake")
    print("  • libopencv-dev, python3-opencv")
    
    print("\n📦 ROS 2 Packages (Humble):")
    ros_deps = [
        "rclpy, rclcpp",
        "sensor-msgs, nav-msgs, geometry-msgs",
        "visualization-msgs, std-msgs, nav2-msgs",
        "tf2-ros, cv-bridge, message-filters",
        "launch, launch-ros, ament-index-python",
        "ament-cmake, ament-copyright, ament-flake8",
        "ament-pep257, nav2-core"
    ]
    for dep in ros_deps:
        print(f"  • {dep}")
    
    print("\n🐍 Python Packages:")
    pip_deps = [
        "numpy (>=1.21.0)",
        "opencv-python (>=4.5.0)",
        "Pillow (>=8.0.0)",
        "pydantic (>=2.0.0)",
        "langchain-google-genai (>=0.1.0)",
        "langchain-core (>=0.1.0)",
        "ultralytics (>=8.0.0) - YOLO models",
        "roboflow (>=1.0.0) - Dataset management",
        "PyYAML (>=5.4.0)",
        "pytest (>=7.0.0)",
        "setuptools (>=65.0.0)"
    ]
    for dep in pip_deps:
        print(f"  • {dep}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Install dependencies for omokai_ws"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print dependency list and exit"
    )
    parser.add_argument(
        "--ros-distro",
        type=str,
        default="humble",
        help="ROS distribution (default: humble)"
    )
    parser.add_argument(
        "--skip-system",
        action="store_true",
        help="Skip system package installation"
    )
    parser.add_argument(
        "--skip-ros",
        action="store_true",
        help="Skip ROS package installation"
    )
    
    args = parser.parse_args()
    
    if args.list:
        print_dependency_list()
        sys.exit(0)
    
    os.environ['ROS_DISTRO'] = args.ros_distro
    
    installer = DependencyInstaller()
    
    if not args.skip_system:
        installer.update_system_packages()
        installer.install_system_dependencies()
    
    if not args.skip_ros:
        installer.install_ros_packages()
    
    installer.install_python_packages()
