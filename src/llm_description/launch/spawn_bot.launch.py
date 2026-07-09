#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import xacro
from ament_index_python.packages import get_package_share_directory, get_package_prefix
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable, TimerAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node

def generate_launch_description():
    # Package details
    pkg_name = 'llm_description'
    pkg_rover_share = get_package_share_directory(pkg_name)
    pkg_rover_prefix = get_package_prefix(pkg_name)

    # 1) Declare use_sim_time arg
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time', default_value='True',
        description='Use simulation (Gazebo) clock'
    )

    # 2) Set Ignition resource & plugin paths for Fortress
    ign_res = os.environ.get('IGN_GAZEBO_RESOURCE_PATH', '')
    ign_res += f":{pkg_rover_share}/models"
    ign_plg = os.environ.get('IGN_GAZEBO_PLUGIN_PATH', '')
    ign_plg += f":{pkg_rover_prefix}/lib"

    # 3) Process the rover_description.xacro with proper namespacing
    xacro_file = os.path.join(pkg_rover_share, 'urdf', 'turtlebot3_burger.urdf.xacro')

    robot_desc = xacro.process_file(xacro_file, mappings={'prefix': 'igvc_'}).toxml()

    # 4) Robot State Publisher
    rsp_node = Node(
        package='robot_state_publisher', 
        executable='robot_state_publisher',
        name='robot_state_publisher', 
        output='screen',
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'robot_description': robot_desc,
        }]
    )

    # 5) Spawn the rover after a short delay
    spawn_rover = TimerAction(
        period=2.0,
        actions=[
            Node(
                package='ros_gz_sim', 
                executable='create', 
                name='spawn_rosbot',
                output='screen',
                arguments=[
                    '-name', 'anvrit', 
                    '-topic', '/robot_description',
                    
                    # '-x', '11.5', 
                    # '-y', '-10.0', 
                    # '-z', '0.1550', 
                    # '-Y', '1.57',

                    # '-x', '-5.0', 
                    # '-y', '-8.417', 
                    # '-z', '0.1550', 
                    # '-Y', '1.57',

                    # '-x', '2.2', 
                    # '-y', '0.2', 
                    # '-z', '1.6550', 
                    # '-Y', '0.0',

                    # '-x', '0.5', 
                    # '-y', '-10.0', 
                    # '-z', '1.6550', 
                    # '-Y', '0.0',


                    '-x', '-2.5', 
                    '-y', '-5.5', 
                    '-z', '0.4550', 
                    '-Y', '1.57',
                ],
            )
        ]
    )

    # jsp_node = Node(
    #     package='joint_state_publisher', 
    #     executable='joint_state_publisher',
    #     name='joint_state_publisher', 
    #     output='screen',
    #     parameters=[{
    #         'use_sim_time': LaunchConfiguration('use_sim_time'),
    #         'robot_description': robot_desc,
    #     }]
    # )

    bridge = TimerAction(
        period=5.0,
        actions=[
            Node(
                package="ros_gz_bridge",
                executable="parameter_bridge",
                name="rover_gz_bridge",
                # namespace="rover",  # Add namespace for bridge
                arguments=[
                    # "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock",
                    "/camera/image@sensor_msgs/msg/Image@ignition.msgs.Image",
                    "/camera/depth_image@sensor_msgs/msg/Image@ignition.msgs.Image",
                    "/camera/camera_info@sensor_msgs/msg/CameraInfo@ignition.msgs.CameraInfo",
                    "/camera/points@sensor_msgs/msg/PointCloud2@ignition.msgs.PointCloudPacked",


                    # "/camera2/image@sensor_msgs/msg/Image@ignition.msgs.Image",
                    # "/camera2/depth_image@sensor_msgs/msg/Image@ignition.msgs.Image",
                    # "/camera2/camera_info@sensor_msgs/msg/CameraInfo@ignition.msgs.CameraInfo",
                    # "/camera2/points@sensor_msgs/msg/PointCloud2@ignition.msgs.PointCloudPacked",
                ],
                remappings=[
                    ("/camera/image", "/camera/image_raw"),
                    ("/camera/depth_image", "/camera/depth/image_raw"),
                    ("/camera/camera_info", "/camera/camera_info"),
                    ("/camera/points", "/camera/depth/points"),


                    # ("/camera2/image", "/camera2/image_raw"),
                    # ("/camera2/depth_image", "/camera2/depth/image_raw"),
                    # ("/camera2/camera_info", "/camera2/camera_info"),
                    # ("/camera2/points", "/camera2/depth/points"),
                ],
                output="screen",
                parameters=[{"use_sim_time": True}],
            )
        ]
    )


    camera_info_relay = TimerAction(
        period=15.0,
        actions=[
            Node(
                package='topic_tools',
                executable='relay',
                name='camera_info_relay',
                # namespace='rover',  # Add namespace for relay
                arguments=['/camera/camera_info', '/camera/depth/camera_info'],
                output='screen',
                parameters=[{"use_sim_time": True}],
            )
        ]
    )

    # velodyne_bridge = Node(
    #     package='ros_gz_bridge',
    #     executable='parameter_bridge',
    #     arguments=['/velodyne_points/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked'],
    #     output='screen',
    #     remappings=[('/velodyne_points/points', '/velodyne_points')],
    # )

    # point_cloud_to_laserscan = Node(
    #     package='pointcloud_to_laserscan',
    #     executable='pointcloud_to_laserscan_node',
    #     name='pointcloud_to_laserscan',
    #     parameters=[{
    #         'use_sim_time': LaunchConfiguration('use_sim_time'),
    #         'target_frame': 'velodyne',
    #         'transform_tolerance': 0.1,
    #         'min_height': 0.20,
    #         'max_height': 4.0,
    #         'angle_min': -3.14,
    #         'angle_max': 3.14,
    #         'angle_increment': 0.0174,
    #         'scan_time': 0.1,
    #         'range_min': 0.75,
    #         'range_max': 20.0,
    #         'use_inf': True,
    #         'qos_overrides': {
    #             '/scan': {
    #                 'publisher': {
    #                     'reliability': 'best_effort',
    #                     'durability': 'volatile',
    #                     'history': 'keep_last',
    #                     'depth': 10,
    #                 }
    #             }
    #         },
    #     }],
    #     remappings=[
    #         ('cloud_in', '/velodyne_points'),
    #         ('scan', '/scan')
    #     ]
    # )

    # Assemble launch description
    return LaunchDescription([
        use_sim_time_arg,
        bridge,
        rsp_node,
        # jsp_node,
        spawn_rover,
        camera_info_relay,
        # velodyne_bridge,
        # point_cloud_to_laserscan,
    ])