#!/usr/bin/env python3
import math
from collections import deque
from typing import List, Optional, Tuple, Set

import numpy as np
import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.parameter import Parameter

from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import PoseArray, Pose
from visualization_msgs.msg import MarkerArray, Marker
from std_msgs.msg import Bool
from tf2_ros import Buffer, TransformListener


GridCell = Tuple[int, int]


class LocalFrontierBundler(Node):
    def __init__(self):
        super().__init__("local_frontier_bundler")

        # Set sim time safely
        self.set_parameters([
            Parameter("use_sim_time", Parameter.Type.BOOL, True)
        ])

        # Parameters
        self.declare_parameter("base_frame", "base_footprint")
        self.declare_parameter("min_goal_distance", 0.5)
        self.declare_parameter("min_cluster_size", 5)
        self.declare_parameter("detection_period", 1.0)

        self.base_frame = self.get_parameter("base_frame").value
        self.min_goal_distance = float(self.get_parameter("min_goal_distance").value)
        self.min_cluster_size = int(self.get_parameter("min_cluster_size").value)
        self.detection_period = float(self.get_parameter("detection_period").value)

        # State
        self.map: Optional[OccupancyGrid] = None
        self.map_received = False

        # ROS interfaces
        self.map_sub = self.create_subscription(
            OccupancyGrid,
            "/map",
            self.map_callback,
            10
        )
        self.frontier_reached_sub = self.create_subscription(
            Bool,
            "/frontier_reached",
            self.reached_callback,
            10
        )

        self.points_pub = self.create_publisher(PoseArray, "/local_frontier_points", 10)
        self.marker_array_pub = self.create_publisher(MarkerArray, "/frontier_markers", 10)

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # Run periodically so it keeps publishing
        self.timer = self.create_timer(self.detection_period, self.timer_callback)

        self.get_logger().info(
            "LocalFrontierBundler started. Publishing frontier centroids to "
            "/local_frontier_points and /frontier_markers"
        )

    def map_callback(self, msg: OccupancyGrid):
        self.map = msg
        self.map_received = True

    def reached_callback(self, msg: Bool):
        if msg.data:
            self.detect_frontiers()

    def timer_callback(self):
        if not self.map_received or self.map is None:
            return
        self.detect_frontiers()

    def get_robot_pose(self) -> Optional[Tuple[float, float]]:
        try:
            trans = self.tf_buffer.lookup_transform(
                "map",
                self.base_frame,
                rclpy.time.Time(),
                timeout=Duration(seconds=0.2),
            )
            return (
                trans.transform.translation.x,
                trans.transform.translation.y,
            )
        except Exception as e:
            self.get_logger().warn(f"Robot pose not available: {e}")
            return None

    def world_from_cell(self, row: int, col: int) -> Tuple[float, float]:
        """
        Convert map grid cell index to world coordinates at cell center.
        """
        resolution = self.map.info.resolution
        origin_x = self.map.info.origin.position.x
        origin_y = self.map.info.origin.position.y
        x = origin_x + (col + 0.5) * resolution
        y = origin_y + (row + 0.5) * resolution
        return x, y

    def cluster_frontiers_grid(self, frontier_cells: List[GridCell]) -> List[List[GridCell]]:
        frontier_set: Set[GridCell] = set(frontier_cells)
        visited: Set[GridCell] = set()
        clusters: List[List[GridCell]] = []

        neighbors = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1),
        ]

        for cell in frontier_cells:
            if cell in visited:
                continue

            cluster = []
            queue = deque([cell])
            visited.add(cell)

            while queue:
                r, c = queue.popleft()
                cluster.append((r, c))

                for dr, dc in neighbors:
                    nbr = (r + dr, c + dc)
                    if nbr in frontier_set and nbr not in visited:
                        visited.add(nbr)
                        queue.append(nbr)

            clusters.append(cluster)

        return clusters

    def detect_frontiers(self):
        if self.map is None:
            self.get_logger().warn("No map detected yet.")
            return

        robot_pose = self.get_robot_pose()
        if robot_pose is None:
            return

        rx, ry = robot_pose

        width = self.map.info.width
        height = self.map.info.height
        resolution = self.map.info.resolution
        origin_x = self.map.info.origin.position.x
        origin_y = self.map.info.origin.position.y

        grid = np.array(self.map.data, dtype=np.int16).reshape((height, width))

        frontier_cells: List[GridCell] = []

        # Frontier definition:
        # free cell (0) with at least one unknown neighbor (-1)
        for row in range(1, height - 1):
            for col in range(1, width - 1):
                if grid[row, col] != 0:
                    continue

                neighborhood = grid[row - 1:row + 2, col - 1:col + 2]
                if not np.any(neighborhood == -1):
                    continue

                x = origin_x + (col + 0.5) * resolution
                y = origin_y + (row + 0.5) * resolution

                if math.hypot(x - rx, y - ry) >= self.min_goal_distance:
                    frontier_cells.append((row, col))

        clusters = self.cluster_frontiers_grid(frontier_cells)

        pose_array = PoseArray()
        pose_array.header.frame_id = "map"
        pose_array.header.stamp = self.get_clock().now().to_msg()

        marker_array = MarkerArray()

        # Clear old markers first
        delete_all = Marker()
        delete_all.action = Marker.DELETEALL
        marker_array.markers.append(delete_all)

        marker_id = 0
        published_count = 0

        for cluster in clusters:
            if len(cluster) < self.min_cluster_size:
                continue

            rows = [cell[0] for cell in cluster]
            cols = [cell[1] for cell in cluster]

            mean_row = float(np.mean(rows))
            mean_col = float(np.mean(cols))

            x = origin_x + (mean_col + 0.5) * resolution
            y = origin_y + (mean_row + 0.5) * resolution

            pose = Pose()
            pose.position.x = float(x)
            pose.position.y = float(y)
            pose.position.z = 0.0
            pose.orientation.w = 1.0
            pose_array.poses.append(pose)

            marker = Marker()
            marker.header.frame_id = "map"
            marker.header.stamp = pose_array.header.stamp
            marker.ns = "frontier_centroids"
            marker.id = marker_id
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            marker.pose.position.x = float(x)
            marker.pose.position.y = float(y)
            marker.pose.position.z = 0.1
            marker.pose.orientation.w = 1.0
            marker.scale.x = 0.18
            marker.scale.y = 0.18
            marker.scale.z = 0.18
            marker.color.r = 0.0
            marker.color.g = 1.0
            marker.color.b = 0.0
            marker.color.a = 1.0
            marker.lifetime = Duration(seconds=0.3).to_msg()
            marker_array.markers.append(marker)

            marker_id += 1
            published_count += 1

        self.points_pub.publish(pose_array)
        self.marker_array_pub.publish(marker_array)

        self.get_logger().info(f"Published {published_count} frontier clusters")

def main(args=None):
    rclpy.init(args=args)
    node = LocalFrontierBundler()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()