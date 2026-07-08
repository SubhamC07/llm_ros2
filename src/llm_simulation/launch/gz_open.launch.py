#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from os.path import join
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    AppendEnvironmentVariable,
)
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node

def generate_launch_description():
    rover_gazebo = get_package_share_directory("llm_simulation")
    world_file = LaunchConfiguration(
        "world_file", 
        default=join(rover_gazebo, "worlds", "eyantra_warehouse_open.world") #small_warehouse.world
    )

    gz_sim_share = get_package_share_directory("ros_gz_sim")
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            join(gz_sim_share, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={
            "gz_args": PythonExpression(["'", world_file, " -r'"])
        }.items(),
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='rover_bridge',
        parameters=[{
            'config_file': os.path.join(rover_gazebo, 'config', 'bridge.yaml'),
            'qos_overrides./tf_static.publisher.durability': 'transient_local',
            'use_sim_time': True
        }],
        output='screen'
    )


    return LaunchDescription([
        # Set resource paths for Gazebo
        AppendEnvironmentVariable(
            name="IGN_GAZEBO_RESOURCE_PATH",
            value=join(rover_gazebo, "worlds")
        ),
        AppendEnvironmentVariable(
            name="IGN_GAZEBO_RESOURCE_PATH",
            value=join(rover_gazebo, "models")
        ),
        # Declare launch arguments
        DeclareLaunchArgument("world_file", default_value=world_file),
        
        # Launch Gazebo
        gz_sim,
        bridge
    ])