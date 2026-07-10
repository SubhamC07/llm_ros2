#!/usr/bin/env python3
"""
llm_ros2 - Quick Dependency Reference
A quick lookup tool for all project dependencies
"""

import json
from pathlib import Path

DEPENDENCIES = {
    "system": {
        "build_tools": ["build-essential", "cmake", "git"],
        "python_dev": ["python3-pip", "python3-dev"],
        "computer_vision": ["libopencv-dev", "python3-opencv"]
    },
    
    "ros2": {
        "core": ["rclpy", "rclcpp"],
        "messages": ["sensor-msgs", "nav-msgs", "geometry-msgs", "visualization-msgs", "std-msgs"],
        "navigation": ["nav2-msgs", "nav2-core"],
        "transforms": ["tf2-ros"],
        "bridges": ["cv-bridge", "message-filters"],
        "launch": ["launch", "launch-ros", "ament-index-python"],
        "build_testing": ["ament-cmake", "ament-copyright", "ament-flake8", "ament-pep257"]
    },
    
    "python": {
        "core": {"numpy": ">=1.21.0", "Pillow": ">=8.0.0"},
        "computer_vision": {"opencv-python": ">=4.5.0"},
        "llm": {"langchain-google-genai": ">=0.1.0", "langchain-core": ">=0.1.0"},
        "ai": {"ultralytics": ">=8.0.0", "roboflow": ">=1.0.0"},
        "data_validation": {"pydantic": ">=2.0.0"},
        "data_format": {"PyYAML": ">=5.4.0"},
        "testing": {"pytest": ">=7.0.0"},
        "build": {"setuptools": ">=65.0.0"}
    }
}

PACKAGES = {
    "llm_description": {
        "type": "ROS 2 CMake (URDF/Meshes)",
        "key_deps": ["ament_cmake"]
    },
    "llm_prompt": {
        "type": "ROS 2 Python (LLM Control)",
        "key_deps": ["langchain-google-genai", "pydantic", "numpy", "rclpy"]
    },
    "llm_navigation": {
        "type": "ROS 2 Python (Navigation/Detection)",
        "key_deps": ["ultralytics", "roboflow", "opencv", "rclpy", "nav_msgs"]
    },
    "llm_simulation": {
        "type": "ROS 2 CMake (Gazebo)",
        "key_deps": ["ament_cmake", "launch", "launch_ros"]
    }
}

FILES = {
    "requirements.txt": "Python packages only",
    "install_dependencies.py": "⭐ Full Python installer",
    "install_dependencies.sh": "Bash installer",
    "Dockerfile": "🐳 Docker container",
    "docker-compose.yml": "Docker Compose config",
    "setup_env.sh": "Environment setup",
    "dependencies.yaml": "YAML manifest",
    "DEPENDENCIES.md": "📖 Detailed docs",
    "SETUP.md": "📋 Setup guide",
    "INSTALLATION_SUMMARY.md": "Quick reference"
}

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def show_system_deps():
    """Show system dependencies"""
    print_header("System Dependencies")
    for category, packages in DEPENDENCIES["system"].items():
        print(f"\n{category.replace('_', ' ').title()}:")
        for pkg in packages:
            print(f"  • {pkg}")

def show_ros_deps():
    """Show ROS 2 dependencies"""
    print_header("ROS 2 Packages (Humble)")
    for category, packages in DEPENDENCIES["ros2"].items():
        print(f"\n{category.replace('_', ' ').title()}:")
        for pkg in packages:
            print(f"  • ros-humble-{pkg}")

def show_python_deps():
    """Show Python dependencies"""
    print_header("Python Packages")
    for category, packages in DEPENDENCIES["python"].items():
        print(f"\n{category.replace('_', ' ').title()}:")
        if isinstance(packages, dict):
            for pkg, version in packages.items():
                print(f"  • {pkg} {version}")
        else:
            for pkg in packages:
                print(f"  • {pkg}")

def show_packages():
    """Show workspace packages"""
    print_header("Workspace Packages")
    for pkg_name, info in PACKAGES.items():
        print(f"\n{pkg_name}:")
        print(f"  Type: {info['type']}")
        print(f"  Key Dependencies: {', '.join(info['key_deps'])}")

def show_files():
    """Show generated files"""
    print_header("Generated Files")
    for filename, description in FILES.items():
        print(f"  • {filename}")
        print(f"    {description}")

def show_quick_install():
    """Show quick install commands"""
    print_header("Quick Install Commands")
    
    print("\nPython Script (Recommended):")
    print("  python3 install_dependencies.py")
    
    print("\nBash Script:")
    print("  bash install_dependencies.sh")
    
    print("\nDocker:")
    print("  docker-compose up -d")
    
    print("\nPython packages only:")
    print("  pip3 install -r requirements.txt")
    
    print("\nView dependencies:")
    print("  python3 install_dependencies.py --list")

def show_build_workflow():
    """Show typical build workflow"""
    print_header("Build Workflow")
    
    print("""
1. Install Dependencies:
   python3 install_dependencies.py

2. Setup Environment:
   source setup_env.sh

3. Build Workspace:
   cd /home/subham/llm_ros2
   colcon build

4. Source Install:
   source install/setup.bash

5. Run Node:
   ros2 run llm_navigation nav2_goal
""")

def show_stats():
    """Show installation statistics"""
    print_header("Installation Statistics")
    
    system_count = sum(len(pkgs) for pkgs in DEPENDENCIES["system"].values())
    ros_count = sum(len(pkgs) for pkgs in DEPENDENCIES["ros2"].values())
    python_count = sum(len(pkgs) for pkgs in DEPENDENCIES["python"].values())
    
    print(f"""
System Packages:     {system_count}
ROS 2 Packages:      {ros_count}
Python Packages:     {python_count}
──────────────────────
Total:              {system_count + ros_count + python_count}

Installation Time:   10-30 minutes
Disk Space Needed:   5-10 GB
Python Version:      3.8+
ROS Distribution:    Humble
""")

def main():
    """Main menu"""
    print("\n" + "="*60)
    print("  llm_ros2 - Dependency Reference Tool")
    print("="*60)
    print("""
Options:
  1. Show System Dependencies
  2. Show ROS 2 Dependencies
  3. Show Python Dependencies
  4. Show Workspace Packages
  5. Show Generated Files
  6. Show Quick Install
  7. Show Build Workflow
  8. Show Statistics
  9. Show All (Verbose)
  0. Exit
""")
    
    while True:
        choice = input("Select option (0-9): ").strip()
        
        if choice == "1":
            show_system_deps()
        elif choice == "2":
            show_ros_deps()
        elif choice == "3":
            show_python_deps()
        elif choice == "4":
            show_packages()
        elif choice == "5":
            show_files()
        elif choice == "6":
            show_quick_install()
        elif choice == "7":
            show_build_workflow()
        elif choice == "8":
            show_stats()
        elif choice == "9":
            show_system_deps()
            show_ros_deps()
            show_python_deps()
            show_packages()
            show_files()
            show_quick_install()
            show_build_workflow()
            show_stats()
        elif choice == "0":
            print("\n👋 Goodbye!\n")
            break
        else:
            print("Invalid option. Try again.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Command line mode
        command = sys.argv[1].lower()
        
        if command == "--system":
            show_system_deps()
        elif command == "--ros":
            show_ros_deps()
        elif command == "--python":
            show_python_deps()
        elif command == "--packages":
            show_packages()
        elif command == "--files":
            show_files()
        elif command == "--install":
            show_quick_install()
        elif command == "--workflow":
            show_build_workflow()
        elif command == "--stats":
            show_stats()
        elif command == "--all":
            show_system_deps()
            show_ros_deps()
            show_python_deps()
            show_packages()
            show_files()
            show_quick_install()
            show_build_workflow()
            show_stats()
        else:
            print(f"Unknown option: {command}")
            print("\nUsage:")
            print("  python3 dependencies_reference.py --system")
            print("  python3 dependencies_reference.py --ros")
            print("  python3 dependencies_reference.py --python")
            print("  python3 dependencies_reference.py --packages")
            print("  python3 dependencies_reference.py --files")
            print("  python3 dependencies_reference.py --install")
            print("  python3 dependencies_reference.py --workflow")
            print("  python3 dependencies_reference.py --stats")
            print("  python3 dependencies_reference.py --all")
            print("  python3 dependencies_reference.py        (interactive)")
    else:
        # Interactive menu
        main()
