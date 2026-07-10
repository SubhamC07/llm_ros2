# Dockerfile for llm_ros2
# Complete reproducible environment for the LLM-based robot navigation system

FROM ros:humble-ros-base-jammy

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
ENV WORKSPACE=/home/llm_ros2

# Install system dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    # Build tools
    build-essential \
    cmake \
    git \
    # Python development
    python3-pip \
    python3-dev \
    python3-colcon-common-extensions \
    # Computer vision
    libopencv-dev \
    python3-opencv \
    # Additional utilities
    wget \
    curl \
    vim \
    nano \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install ROS 2 packages
RUN apt-get update && apt-get install -y \
    # Core ROS
    ros-${ROS_DISTRO}-rclpy \
    ros-${ROS_DISTRO}-rclcpp \
    # Message types
    ros-${ROS_DISTRO}-sensor-msgs \
    ros-${ROS_DISTRO}-nav-msgs \
    ros-${ROS_DISTRO}-geometry-msgs \
    ros-${ROS_DISTRO}-visualization-msgs \
    ros-${ROS_DISTRO}-std-msgs \
    # Navigation
    ros-${ROS_DISTRO}-nav2-msgs \
    ros-${ROS_DISTRO}-nav2-core \
    # Transforms
    ros-${ROS_DISTRO}-tf2-ros \
    # Bridges
    ros-${ROS_DISTRO}-cv-bridge \
    ros-${ROS_DISTRO}-message-filters \
    # Launch
    ros-${ROS_DISTRO}-launch \
    ros-${ROS_DISTRO}-launch-ros \
    ros-${ROS_DISTRO}-ament-index-python \
    # Build tools
    ros-${ROS_DISTRO}-ament-cmake \
    ros-${ROS_DISTRO}-ament-copyright \
    ros-${ROS_DISTRO}-ament-flake8 \
    ros-${ROS_DISTRO}-ament-pep257 \
    # Development tools
    python3-pytest \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash omokai

# Set up workspace
WORKDIR ${WORKSPACE}

# Copy requirements.txt
COPY requirements.txt .

# Install Python packages
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Create workspace structure
RUN mkdir -p src && \
    chown -R omokai:omokai ${WORKSPACE}

# Setup entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
source /opt/ros/'"${ROS_DISTRO}"'/setup.bash\n\
if [ -f "${WORKSPACE}/install/setup.bash" ]; then\n\
    source ${WORKSPACE}/install/setup.bash\n\
fi\n\
exec "$@"' > /ros_entrypoint.sh && \
    chmod +x /ros_entrypoint.sh

# Switch to non-root user
USER omokai

# Set up ROS environment
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["bash"]
