#!/usr/bin/env python3
import math
import rclpy
from typing import Optional, List, Tuple
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.parameter import Parameter
from tf2_ros import Buffer, TransformListener

from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import PoseArray, PoseStamped, Point
from visualization_msgs.msg import Marker
from std_msgs.msg import ColorRGBA

class FrontierSelector(Node):
    def __init__(self):
        super().__init__('frontier_selector')

        # Use simulation time matching your pipeline
        self.set_parameters([
            Parameter("use_sim_time", Parameter.Type.BOOL, True)
        ])

        # --- Parameters ---
        self.declare_parameter("base_frame", "base_footprint")
        self.declare_parameter("map_frame", "map")
        
        # Scoring weights
        self.declare_parameter("weight_distance", 1.5)     # Lower distance = higher score
        self.declare_parameter("weight_heading", 1.0)      # Alignment with current robot yaw
        self.declare_parameter("weight_hysteresis", 2.5)   # Bonus given to the current goal to prevent rapid switching
        self.declare_parameter("switching_threshold", 1.0) # Delta score required to force a goal switch
        
        # Memory thresholds
        self.declare_parameter("visited_radius", 0.5)      # Distance (m) to classify a goal as reached/visited
        self.declare_parameter("blacklist_timeout", 45.0)  # Time (s) allowed on a single goal before blacklisting
        self.declare_parameter("obstacle_safe_distance", 0.4)  # Minimum distance to occupied cells
        self.declare_parameter("front_preference_weight", 1.5)  # Bonus for front 180° candidates
        self.declare_parameter("pub_period", 1.0)          # Continuous goal publishing period (s)

        # Read Parameters
        self.base_frame = self.get_parameter("base_frame").value
        self.map_frame = self.get_parameter("map_frame").value
        self.w_dist = float(self.get_parameter("weight_distance").value)
        self.w_head = float(self.get_parameter("weight_heading").value)
        self.w_hyst = float(self.get_parameter("weight_hysteresis").value)
        self.switch_thresh = float(self.get_parameter("switching_threshold").value)
        self.visited_radius = float(self.get_parameter("visited_radius").value)
        self.blacklist_timeout = float(self.get_parameter("blacklist_timeout").value)
        self.obstacle_safe_distance = float(self.get_parameter("obstacle_safe_distance").value)
        self.w_front = float(self.get_parameter("front_preference_weight").value)
        pub_period = float(self.get_parameter("pub_period").value)

        # --- State Tracking ---
        self.current_goal = None          # (x, y) tuple
        self.current_goal_score = -float('inf')
        self.goal_selected_time = None    # builtin rclpy Time object
        
        self.visited_goals = []           # List of (x, y) tuples
        self.blacklisted_goals = []       # List of (x, y) tuples
        self.map: Optional[OccupancyGrid] = None

        # --- TF Setup ---
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # --- ROS Interfaces ---
        self.frontier_sub = self.create_subscription(
            PoseArray,
            "/local_frontier_points",
            self.frontier_callback,
            10
        )

        self.map_sub = self.create_subscription(
            OccupancyGrid,
            "/map",
            self.map_callback,
            10
        )
        
        self.goal_pub = self.create_publisher(PoseStamped, "/goal_given", 10)
        self.marker_pub = self.create_publisher(Marker, "/selected_frontier_marker", 10)

        # Timer for continuous publication downstream to ContinuousGoalUpdater
        self.pub_timer = self.create_timer(pub_period, self.timer_publish_goal)

        self.get_logger().info("FrontierSelector initialized and ready.")

    def frontier_callback(self, msg: PoseArray):
        # 1. Get current robot pose & yaw
        robot_pose = self.get_robot_pose_and_yaw()
        if robot_pose is None:
            return
        rx, ry, r_yaw = robot_pose

        # 2. Housekeeping: Check if we reached the current goal or timed out
        if self.current_goal is not None:
            dist_to_goal = math.hypot(self.current_goal[0] - rx, self.current_goal[1] - ry)
            
            # Check if visited
            if dist_to_goal <= self.visited_radius:
                self.get_logger().info(f"Goal {self.current_goal} reached! Marking as visited.")
                self.visited_goals.append(self.current_goal)
                self.clear_current_goal()
            
            # Check if stuck / timed out (Blacklisting)
            elif self.goal_selected_time is not None:
                elapsed_time = (self.get_clock().now() - self.goal_selected_time).nanoseconds / 1e9
                if elapsed_time > self.blacklist_timeout:
                    self.get_logger().warn(f"Goal {self.current_goal} timed out after {elapsed_time:.1f}s. Blacklisting.")
                    self.blacklisted_goals.append(self.current_goal)
                    self.clear_current_goal()

        # 3. Filter and evaluate incoming frontier list with obstacle safety
        candidates: List[Tuple[float, float, float, float]] = []

        for pose in msg.poses:
            fx = pose.position.x
            fy = pose.position.y

            # Filter out known visited or blacklisted areas
            if self.is_near_any(fx, fy, self.visited_goals) or self.is_near_any(fx, fy, self.blacklisted_goals):
                continue

            # Filter frontier points too close to occupied map cells
            if self.map is not None and self.is_near_obstacle(fx, fy, self.obstacle_safe_distance):
                continue

            distance = math.hypot(fx - rx, fy - ry)
            angle_to_frontier = math.atan2(fy - ry, fx - rx)
            heading_diff = abs(self.normalize_angle(angle_to_frontier - r_yaw))

            front_bonus = self.w_front if heading_diff <= (math.pi / 2.0) else 0.0
            score = -(self.w_dist * distance) - (self.w_head * heading_diff) + front_bonus
            if self.current_goal is not None and math.hypot(fx - self.current_goal[0], fy - self.current_goal[1]) <= self.visited_radius:
                score += self.w_hyst

            candidates.append((distance, heading_diff, score, fx, fy))

        # Prefer the nearest safe frontier options first, while still taking heading into account.
        candidates.sort(key=lambda item: (item[0], item[1]))

        best_frontier = None
        best_score = -float('inf')
        for distance, heading_diff, score, fx, fy in candidates:
            if score > best_score:
                best_score = score
                best_frontier = (fx, fy)

        # 4. Goal Switching Logic
        if best_frontier is not None:
            if self.current_goal is None:
                self.set_new_goal(best_frontier, best_score)
            else:
                # Only switch if candidate outperforms current tracking target beyond threshold
                if best_score > (self.current_goal_score + self.switch_thresh):
                    self.get_logger().info(f"Switching goal! Score improvement: {best_score:.2f} > {self.current_goal_score:.2f}")
                    self.set_new_goal(best_frontier, best_score)
                else:
                    # Maintain tracking position coordinates but update its structural score
                    if self.is_near_any(best_frontier[0], best_frontier[1], [self.current_goal]):
                        self.current_goal_score = best_score
        
        # Always update visual markers in RViz
        self.publish_marker()

    def set_new_goal(self, frontier, score):
        self.current_goal = frontier
        self.current_goal_score = score
        self.goal_selected_time = self.get_clock().now()
        # Prompt immediate update execution
        self.timer_publish_goal()

    def clear_current_goal(self):
        self.current_goal = None
        self.current_goal_score = -float('inf')
        self.goal_selected_time = None

    def timer_publish_goal(self):
        """Continuously streams out the target goal for ContinuousGoalUpdater configuration"""
        if self.current_goal is None:
            return

        msg = PoseStamped()
        msg.header.frame_id = self.map_frame
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.position.x = self.current_goal[0]
        msg.pose.position.y = self.current_goal[1]
        
        # Basic directional orientation looking at the goal
        msg.pose.orientation.w = 1.0 
        
        self.goal_pub.publish(msg)

    # --- Helper Computations ---
    def get_robot_pose_and_yaw(self):
        try:
            trans = self.tf_buffer.lookup_transform(
                self.map_frame,
                self.base_frame,
                rclpy.time.Time(),
                timeout=Duration(seconds=0.15)
            )
            rx = trans.transform.translation.x
            ry = trans.transform.translation.y
            
            # Extract Yaw Euler representation from Transform Quaternion
            q = trans.transform.rotation
            siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
            cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
            yaw = math.atan2(siny_cosp, cosy_cosp)
            
            return rx, ry, yaw
        except Exception as e:
            self.get_logger().warn(f"Failed to lookup robot transform: {e}", throttle_duration_sec=5.0)
            return None

    def is_near_any(self, x, y, goal_list):
        for gx, gy in goal_list:
            if math.hypot(x - gx, y - gy) <= self.visited_radius:
                return True
        return False

    def normalize_angle(self, angle):
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle

    # --- Visualization Outputs ---
    def publish_marker(self):
        marker = Marker()
        marker.header.frame_id = self.map_frame
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "selected_frontier"
        marker.id = 999
        marker.type = Marker.CYLINDER
        
        if self.current_goal is not None:
            marker.action = Marker.ADD
            marker.pose.position.x = self.current_goal[0]
            marker.pose.position.y = self.current_goal[1]
            marker.pose.position.z = 0.3
            marker.scale.x = 0.35
            marker.scale.y = 0.35
            marker.scale.z = 0.6
            # Gold/Orange color scheme indicating target pursuit
            marker.color = ColorRGBA(r=1.0, g=0.55, b=0.0, a=0.85)
        else:
            marker.action = Marker.DELETE

        self.marker_pub.publish(marker)

    def map_callback(self, msg: OccupancyGrid):
        self.map = msg

    def is_near_obstacle(self, x: float, y: float, min_distance: float) -> bool:
        if self.map is None:
            return False

        resolution = self.map.info.resolution
        if resolution <= 0.0:
            return False

        origin_x = self.map.info.origin.position.x
        origin_y = self.map.info.origin.position.y
        width = self.map.info.width
        height = self.map.info.height

        col = int((x - origin_x) / resolution)
        row = int((y - origin_y) / resolution)
        radius_cells = int(math.ceil(min_distance / resolution))

        if row < 0 or row >= height or col < 0 or col >= width:
            return True

        grid = self.map.data
        for dr in range(-radius_cells, radius_cells + 1):
            for dc in range(-radius_cells, radius_cells + 1):
                r = row + dr
                c = col + dc
                if r < 0 or r >= height or c < 0 or c >= width:
                    continue
                if grid[r * width + c] != 100:
                    continue
                distance = math.hypot(dc * resolution, dr * resolution)
                if distance <= min_distance:
                    return True

        return False

def main(args=None):
    rclpy.init(args=args)
    node = FrontierSelector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()