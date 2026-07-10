#!/usr/bin/env python3
import os
import json
import math
import sys
import threading
import time
import rclpy
from typing import Optional, List, Tuple
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.parameter import Parameter
from tf2_ros import Buffer, TransformListener

from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import PoseArray, PoseStamped, Point
from visualization_msgs.msg import Marker
from std_msgs.msg import ColorRGBA, String

# Import Google GenAI SDK
try:
    import google.generativeai as genai
    HAS_GEMINI = True
    from google.generativeai.types import GenerationConfig
except ImportError:
    HAS_GEMINI = False

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
        self.declare_parameter("weight_distance", 1.5)
        self.declare_parameter("weight_heading", 1.0)
        self.declare_parameter("weight_hysteresis", 2.5)
        self.declare_parameter("switching_threshold", 1.0)
        
        # Memory thresholds
        self.declare_parameter("visited_radius", 0.5)
        self.declare_parameter("blacklist_timeout", 45.0)
        self.declare_parameter("obstacle_safe_distance", 0.4)
        self.declare_parameter("front_preference_weight", 1.5)
        self.declare_parameter("pub_period", 1.0)
        
        # Google Gemini API Parameters
        self.declare_parameter("google_api_key", "")
        self.declare_parameter("llm_model", "gemini-2.5-flash")

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

        # --- LLM Operational State ---
        self.mapping_mode = "idle" 
        self.mapping_start_time = None
        self.mapping_duration = None

        # --- Setup Gemini Client ---
        api_key = self.get_parameter("google_api_key").value or os.environ.get("GOOGLE_API_KEY")
        self.model_name = self.get_parameter("llm_model").value
        
        if HAS_GEMINI and api_key:
            genai.configure(api_key=api_key)
            
            system_instruction = (
                "You are an AI coordinate mapping manager for an autonomous robot. Your task is to process user requests "
                "and output valid raw JSON data without markdown code blocks. The JSON object must contain exactly two fields:\n"
                "1. 'mode': string value constraint ('indefinite', 'timed', 'complete', 'stop')\n"
                "2. 'duration': numeric float value representing duration in SECONDS if timed mapping is requested, or null otherwise.\n\n"
                "Examples:\n"
                "- 'complete mapping' -> {\"mode\": \"complete\", \"duration\": null}\n"
                "- 'go on mapping indefinitely' -> {\"mode\": \"indefinite\", \"duration\": null}\n"
                "- 'map for 5 minutes and stop' -> {\"mode\": \"timed\", \"duration\": 300.0}\n"
                "- 'abort operations and freeze' -> {\"mode\": \"stop\", \"duration\": null}"
            )
            
            self.llm_model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )
            self.get_logger().info(f"Gemini API active utilizing model: {self.model_name}")
        else:
            self.llm_model = None
            self.get_logger().warn("Google API Key not found or library missing. Falling back to rule-based keyword matching.")

        # --- State Tracking ---
        self.current_goal = None
        self.current_goal_score = -float('inf')
        self.goal_selected_time = None
        
        self.visited_goals = []
        self.blacklisted_goals = []
        self.map: Optional[OccupancyGrid] = None

        # --- TF Setup ---
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # --- ROS Interfaces ---
        self.frontier_sub = self.create_subscription(PoseArray, "/local_frontier_points", self.frontier_callback, 10)
        self.map_sub = self.create_subscription(OccupancyGrid, "/map", self.map_callback, 10)
        self.llm_sub = self.create_subscription(String, "/llm_command", self.llm_command_callback, 10)
        
        self.goal_pub = self.create_publisher(PoseStamped, "/goal_given", 10)
        self.marker_pub = self.create_publisher(Marker, "/selected_frontier_marker", 10)

        self.pub_timer = self.create_timer(pub_period, self.timer_publish_goal)

        # --- Terminal Input Thread Launch ---
        self.input_thread = threading.Thread(target=self.terminal_input_loop, daemon=True)
        self.input_thread.start()

        self.get_logger().info("FrontierSelector ready. You can type commands directly into this terminal!")

    def terminal_input_loop(self):
        """Background thread loop to catch terminal inputs without blocking ROS2 execution"""
        time.sleep(1.5) # Wait for initial log messages to pass
        while rclpy.ok():
            try:
                # Terminal prompt line
                prompt = input("\n[Gemini Prompt] -> Enter command: ").strip()
                if prompt:
                    self.process_incoming_command(prompt)
            except (KeyboardInterrupt, EOFError):
                break

    def llm_command_callback(self, msg: String):
        """Still supports incoming topic triggers if needed"""
        self.process_incoming_command(msg.data.strip())

    def process_incoming_command(self, prompt: str):
        """Unified command pipeline for both topic and terminal inputs"""
        self.get_logger().info(f"Processing command: '{prompt}'")
        parsed_config = self.parse_prompt_with_gemini(prompt)
        
        mode = parsed_config.get("mode", "idle")
        duration = parsed_config.get("duration", None)

        self.mapping_mode = mode
        self.mapping_start_time = self.get_clock().now()
        self.mapping_duration = float(duration) if duration is not None else None

        self.get_logger().info(f"State updated -> Mode: {self.mapping_mode.upper()} | Duration: {self.mapping_duration}s")
        
        if self.mapping_mode in ["stop", "idle"]:
            self.clear_current_goal()

    def parse_prompt_with_gemini(self, prompt: str) -> dict:
        if self.llm_model is not None:
            try:
                response = self.llm_model.generate_content(
                    prompt,
                    generation_config=GenerationConfig(response_mime_type="application/json")
                )
                return json.loads(response.text)
            except Exception as e:
                self.get_logger().error(f"Gemini API failure: {e}. Falling back to regex parser.")

        # --- Rule-Based Fallback ---
        prompt_lower = prompt.lower()
        if any(x in prompt_lower for x in ["stop", "abort", "freeze"]):
            return {"mode": "stop", "duration": None}
        elif any(x in prompt_lower for x in ["indefinitely", "forever"]):
            return {"mode": "indefinite", "duration": None}
        elif any(x in prompt_lower for x in ["for", "min", "sec"]):
            words = prompt_lower.split()
            duration = 60.0
            for idx, word in enumerate(words):
                if word.isdigit() or parts_are_float(word):
                    val = float(word)
                    if idx + 1 < len(words):
                        next_word = words[idx + 1]
                        if "min" in next_word: duration = val * 60.0
                        elif "sec" in next_word: duration = val
                        elif "hour" in next_word: duration = val * 3600.0
                    return {"mode": "timed", "duration": duration}
            return {"mode": "timed", "duration": duration}
        else:
            return {"mode": "complete", "duration": None}

    def frontier_callback(self, msg: PoseArray):
        if self.mapping_mode in ["idle", "stop"]:
            self.clear_current_goal()
            return

        if self.mapping_mode == "timed" and self.mapping_start_time is not None:
            elapsed = (self.get_clock().now() - self.mapping_start_time).nanoseconds / 1e9
            if self.mapping_duration and elapsed >= self.mapping_duration:
                self.get_logger().info(f"Time limit reached ({elapsed:.1f}s). Stopping exploration.")
                self.mapping_mode = "idle"
                self.clear_current_goal()
                return

        robot_pose = self.get_robot_pose_and_yaw()
        if robot_pose is None: return
        rx, ry, r_yaw = robot_pose

        if self.current_goal is not None:
            dist_to_goal = math.hypot(self.current_goal[0] - rx, self.current_goal[1] - ry)
            if dist_to_goal <= self.visited_radius:
                self.get_logger().info(f"Goal {self.current_goal} reached!")
                self.visited_goals.append(self.current_goal)
                self.clear_current_goal()
            elif self.goal_selected_time is not None:
                elapsed_time = (self.get_clock().now() - self.goal_selected_time).nanoseconds / 1e9
                if elapsed_time > self.blacklist_timeout:
                    self.get_logger().warn(f"Goal {self.current_goal} timed out. Blacklisting.")
                    self.blacklisted_goals.append(self.current_goal)
                    self.clear_current_goal()

        candidates: List[Tuple[float, float, float, float]] = []
        for pose in msg.poses:
            fx, fy = pose.position.x, pose.position.y
            if self.is_near_any(fx, fy, self.visited_goals) or self.is_near_any(fx, fy, self.blacklisted_goals):
                continue
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

        if len(candidates) == 0 and self.mapping_mode == "complete":
            self.get_logger().info("No safe frontiers left. Complete mapping finished!")
            self.mapping_mode = "idle"
            self.clear_current_goal()
            return

        candidates.sort(key=lambda item: (item[0], item[1]))
        best_frontier, best_score = None, -float('inf')
        for distance, heading_diff, score, fx, fy in candidates:
            if score > best_score:
                best_score = score
                best_frontier = (fx, fy)

        if best_frontier is not None:
            if self.current_goal is None:
                self.set_new_goal(best_frontier, best_score)
            elif best_score > (self.current_goal_score + self.switch_thresh):
                self.get_logger().info(f"Switching goal! Improvement: {best_score:.2f} > {self.current_goal_score:.2f}")
                self.set_new_goal(best_frontier, best_score)
            elif self.is_near_any(best_frontier[0], best_frontier[1], [self.current_goal]):
                self.current_goal_score = best_score
        
        self.publish_marker()

    def set_new_goal(self, frontier, score):
        self.current_goal = frontier
        self.current_goal_score = score
        self.goal_selected_time = self.get_clock().now()
        self.timer_publish_goal()

    def clear_current_goal(self):
        self.current_goal = None
        self.current_goal_score = -float('inf')
        self.goal_selected_time = None

    def timer_publish_goal(self):
        if self.current_goal is None or self.mapping_mode in ["idle", "stop"]:
            return
        msg = PoseStamped()
        msg.header.frame_id = self.map_frame
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.position.x = self.current_goal[0]
        msg.pose.position.y = self.current_goal[1]
        msg.pose.orientation.w = 1.0 
        self.goal_pub.publish(msg)

    def get_robot_pose_and_yaw(self):
        try:
            trans = self.tf_buffer.lookup_transform(self.map_frame, self.base_frame, rclpy.time.Time(), timeout=Duration(seconds=0.15))
            rx, ry = trans.transform.translation.x, trans.transform.translation.y
            q = trans.transform.rotation
            siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
            cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
            return rx, ry, math.atan2(siny_cosp, cosy_cosp)
        except Exception as e:
            self.get_logger().warn(f"Transform failure: {e}", throttle_duration_sec=5.0)
            return None

    def is_near_any(self, x, y, goal_list):
        for gx, gy in goal_list:
            if math.hypot(x - gx, y - gy) <= self.visited_radius: return True
        return False

    def normalize_angle(self, angle):
        while angle > math.pi: angle -= 2.0 * math.pi
        while angle < -math.pi: angle += 2.0 * math.pi
        return angle

    def publish_marker(self):
        marker = Marker()
        marker.header.frame_id = self.map_frame
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "selected_frontier"
        marker.id = 999
        marker.type = Marker.CYLINDER
        if self.current_goal is not None and self.mapping_mode not in ["idle", "stop"]:
            marker.action = Marker.ADD
            marker.pose.position.x, marker.pose.position.y = self.current_goal[0], self.current_goal[1]
            marker.pose.position.z = 0.3
            marker.scale.x, marker.scale.y, marker.scale.z = 0.35, 0.35, 0.6
            marker.color = ColorRGBA(r=1.0, g=0.55, b=0.0, a=0.85)
        else:
            marker.action = Marker.DELETE
        self.marker_pub.publish(marker)

    def map_callback(self, msg: OccupancyGrid):
        self.map = msg

    def is_near_obstacle(self, x: float, y: float, min_distance: float) -> bool:
        if self.map is None: return False
        resolution = self.map.info.resolution
        if resolution <= 0.0: return False
        origin_x, origin_y = self.map.info.origin.position.x, self.map.info.origin.position.y
        width, height = self.map.info.width, self.map.info.height
        col, row = int((x - origin_x) / resolution), int((y - origin_y) / resolution)
        radius_cells = int(math.ceil(min_distance / resolution))
        if row < 0 or row >= height or col < 0 or col >= width: return True
        grid = self.map.data
        for dr in range(-radius_cells, radius_cells + 1):
            for dc in range(-radius_cells, radius_cells + 1):
                r, c = row + dr, col + dc
                if r < 0 or r >= height or c < 0 or c >= width: continue
                if grid[r * width + c] == 100:
                    if math.hypot(dc * resolution, dr * resolution) <= min_distance: return True
        return False

def parts_are_float(str_val):
    try:
        float(str_val)
        return True
    except ValueError:
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