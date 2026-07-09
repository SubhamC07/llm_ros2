#!/usr/bin/env python3
import os
import json
import math
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

import numpy as np
import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from rclpy.parameter import Parameter

from nav_msgs.msg import OccupancyGrid, Odometry
from geometry_msgs.msg import PoseArray, PoseStamped, Pose
from visualization_msgs.msg import MarkerArray, Marker
from std_msgs.msg import Bool
from tf2_ros import Buffer, TransformListener

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

GridCell = Tuple[int, int]


class FrontierChoice(BaseModel):
    selected_frontier_id: int = Field(..., description="ID of the chosen frontier")
    reason: str = Field(default="", description="Short reason for the choice")
    confidence: float = Field(default=0.0, description="Confidence from 0 to 1")


class FrontierLLMPlanner:
    """
    Small wrapper around Gemini structured output.
    If GOOGLE_API_KEY is missing or the model fails, the caller can fall back
    to deterministic ranking.
    """
    def __init__(self, model_name: str = "gemini-2.5-flash", temperature: float = 0.0):
        self.enabled = False
        self.error: Optional[str] = None
        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            self.error = "GOOGLE_API_KEY is not set"
            return

        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=temperature,
            )

            system_prompt = """
You are a frontier selector for autonomous exploration.

You will receive JSON with:
- robot state
- map and footprint settings
- recent target history
- a list of frontier candidates, each with rich geometric and safety features

Choose exactly one frontier that is the best next exploration target.

Hard rules:
- Never select a candidate with inside_footprint = true.
- Never select a candidate with too_close = true.
- Prefer candidates with higher reachability_score.
- Prefer larger cluster_size when all else is similar.
- Prefer lower risk_score.
- Prefer candidates in front of the robot when reasonable.
- Prefer lower distance_to_robot when quality is otherwise similar.
- Avoid oscillation: if the current target is still valid and similar in quality, keep it.
- Avoid recently visited or repeatedly rejected frontiers.

Return only the structured result.
"""
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{frontier_context}")
            ])

            self.chain = self.prompt | llm.with_structured_output(FrontierChoice)
            self.enabled = True

        except Exception as e:
            self.error = str(e)
            self.enabled = False

    def choose_frontier(self, frontier_context: str) -> FrontierChoice:
        if not self.enabled:
            raise RuntimeError(self.error or "LLM planner is disabled")
        return self.chain.invoke({"frontier_context": frontier_context})


class LLMFrontierExplorer(Node):
    def __init__(self):
        super().__init__("llm_frontier_explorer")

        # Parameters
        self.declare_parameter("use_sim_time", True)
        self.declare_parameter("base_frame", "base_footprint")

        self.declare_parameter("min_goal_distance", 0.5)
        self.declare_parameter("min_cluster_size", 5)
        self.declare_parameter("detection_period", 1.0)
        self.declare_parameter("llm_call_period", 5.0)

        self.declare_parameter("footprint_min_x", -0.65)
        self.declare_parameter("footprint_max_x", 0.05)
        self.declare_parameter("footprint_min_y", -0.30)
        self.declare_parameter("footprint_max_y", 0.30)
        self.declare_parameter("footprint_padding", 0.20)

        self.declare_parameter("current_target_reacquire_distance", 0.50)
        self.declare_parameter("recent_revisit_radius", 0.80)
        self.declare_parameter("distance_norm", 8.0)

        self.declare_parameter("llm_model", "gemini-2.5-flash")
        self.declare_parameter("llm_temperature", 0.0)
        self.declare_parameter("llm_min_confidence_to_switch", 0.45)
        self.declare_parameter("max_recent_targets", 10)

        self.base_frame = self.get_parameter("base_frame").value
        self.min_goal_distance = float(self.get_parameter("min_goal_distance").value)
        self.min_cluster_size = int(self.get_parameter("min_cluster_size").value)
        self.detection_period = float(self.get_parameter("detection_period").value)
        self.llm_call_period = float(self.get_parameter("llm_call_period").value)

        self.footprint_min_x = float(self.get_parameter("footprint_min_x").value)
        self.footprint_max_x = float(self.get_parameter("footprint_max_x").value)
        self.footprint_min_y = float(self.get_parameter("footprint_min_y").value)
        self.footprint_max_y = float(self.get_parameter("footprint_max_y").value)
        self.footprint_padding = float(self.get_parameter("footprint_padding").value)

        self.current_target_reacquire_distance = float(
            self.get_parameter("current_target_reacquire_distance").value
        )
        self.recent_revisit_radius = float(self.get_parameter("recent_revisit_radius").value)
        self.distance_norm = float(self.get_parameter("distance_norm").value)

        self.llm_min_confidence_to_switch = float(
            self.get_parameter("llm_min_confidence_to_switch").value
        )
        self.max_recent_targets = int(self.get_parameter("max_recent_targets").value)

        llm_model = self.get_parameter("llm_model").value
        llm_temperature = float(self.get_parameter("llm_temperature").value)

        # State
        self.map: Optional[OccupancyGrid] = None
        self.map_received = False

        self.current_velocity = {"linear": 0.0, "angular": 0.0}
        self.current_target_id: int = -1
        self.current_target_pose: Optional[Dict[str, float]] = None
        self.target_history: Deque[Dict[str, Any]] = deque(maxlen=self.max_recent_targets)

        self.latest_candidates: List[Dict[str, Any]] = []
        self.latest_pose_array = PoseArray()
        self.force_replan = False
        self.last_llm_choice: Optional[FrontierChoice] = None

        # ROS interfaces
        self.map_sub = self.create_subscription(
            OccupancyGrid,
            "/map",
            self.map_callback,
            10
        )

        self.odom_sub = self.create_subscription(
            Odometry,
            "/odom",
            self.odom_callback,
            10
        )

        self.frontier_reached_sub = self.create_subscription(
            Bool,
            "/frontier_reached",
            self.reached_callback,
            10
        )

        self.frontier_pub = self.create_publisher(PoseArray, "/local_frontier_points", 10)
        self.marker_array_pub = self.create_publisher(MarkerArray, "/frontier_markers", 10)
        self.goal_pub = self.create_publisher(PoseStamped, "/goal_given", 10)

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.llm_planner = FrontierLLMPlanner(
            model_name=llm_model,
            temperature=llm_temperature,
        )

        if self.llm_planner.enabled:
            self.get_logger().info(f"LLM planner enabled with model: {llm_model}")
        else:
            self.get_logger().warn(
                "LLM planner disabled; using deterministic fallback. "
                f"Reason: {self.llm_planner.error}"
            )

        self.detection_timer = self.create_timer(self.detection_period, self.detection_timer_callback)
        self.decision_timer = self.create_timer(self.llm_call_period, self.decision_timer_callback)

        self.get_logger().info(
            "LLM Frontier Explorer started. Detecting frontiers, scoring them, "
            "and publishing goals to /goal_given."
        )

    def map_callback(self, msg: OccupancyGrid):
        self.map = msg
        self.map_received = True

    def odom_callback(self, msg: Odometry):
        self.current_velocity["linear"] = float(msg.twist.twist.linear.x)
        self.current_velocity["angular"] = float(msg.twist.twist.angular.z)

    def reached_callback(self, msg: Bool):
        if msg.data:
            self.force_replan = True
            self.current_target_id = -1
            self.current_target_pose = None
            self.get_logger().info("Frontier reached signal received. Forcing replan.")

    @staticmethod
    def normalize_angle(angle: float) -> float:
        return (angle + math.pi) % (2.0 * math.pi) - math.pi

    @staticmethod
    def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        return math.atan2(siny_cosp, cosy_cosp)

    def get_robot_pose(self) -> Optional[Dict[str, float]]:
        try:
            trans = self.tf_buffer.lookup_transform(
                "map",
                self.base_frame,
                Time(),
                timeout=Duration(seconds=0.2),
            )
            yaw = self.quaternion_to_yaw(
                trans.transform.rotation.x,
                trans.transform.rotation.y,
                trans.transform.rotation.z,
                trans.transform.rotation.w,
            )
            return {
                "x": float(trans.transform.translation.x),
                "y": float(trans.transform.translation.y),
                "yaw": float(yaw),
            }
        except Exception as e:
            self.get_logger().warn(f"Robot pose not available: {e}")
            return None

    def world_from_cell(self, row: int, col: int) -> Tuple[float, float]:
        resolution = self.map.info.resolution
        origin_x = self.map.info.origin.position.x
        origin_y = self.map.info.origin.position.y
        x = origin_x + (col + 0.5) * resolution
        y = origin_y + (row + 0.5) * resolution
        return x, y

    def map_to_base(self, x: float, y: float, robot_pose: Dict[str, float]) -> Tuple[float, float]:
        dx = x - robot_pose["x"]
        dy = y - robot_pose["y"]
        yaw = robot_pose["yaw"]
        local_x = math.cos(yaw) * dx + math.sin(yaw) * dy
        local_y = -math.sin(yaw) * dx + math.cos(yaw) * dy
        return local_x, local_y

    def is_inside_footprint(self, local_x: float, local_y: float) -> bool:
        min_x = self.footprint_min_x - self.footprint_padding
        max_x = self.footprint_max_x + self.footprint_padding
        min_y = self.footprint_min_y - self.footprint_padding
        max_y = self.footprint_max_y + self.footprint_padding
        return (min_x <= local_x <= max_x) and (min_y <= local_y <= max_y)

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

            cluster: List[GridCell] = []
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

    def candidate_is_revisited(self, x: float, y: float) -> bool:
        for item in self.target_history:
            px = float(item.get("x", 1e9))
            py = float(item.get("y", 1e9))
            if math.hypot(x - px, y - py) <= self.recent_revisit_radius:
                return True
        return False

    def nearest_candidate_to_pose(
        self,
        pose_xy: Optional[Dict[str, float]],
        candidates: List[Dict[str, Any]],
        threshold: float
    ) -> Optional[Dict[str, Any]]:
        if not pose_xy or not candidates:
            return None

        best = None
        best_dist = float("inf")
        for c in candidates:
            d = math.hypot(c["centroid_x"] - pose_xy["x"], c["centroid_y"] - pose_xy["y"])
            if d < best_dist:
                best_dist = d
                best = c
        if best is not None and best_dist <= threshold:
            best = dict(best)
            best["distance_to_current_target"] = float(best_dist)
            return best
        return None

    def clamp01(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def compute_cluster_candidate(
        self,
        cluster: List[GridCell],
        grid: np.ndarray,
        robot_pose: Dict[str, float]
    ) -> Dict[str, Any]:
        rows = np.array([cell[0] for cell in cluster], dtype=np.float32)
        cols = np.array([cell[1] for cell in cluster], dtype=np.float32)

        mean_row = float(np.mean(rows))
        mean_col = float(np.mean(cols))
        centroid_x = self.map.info.origin.position.x + (mean_col + 0.5) * self.map.info.resolution
        centroid_y = self.map.info.origin.position.y + (mean_row + 0.5) * self.map.info.resolution

        dist = math.hypot(centroid_x - robot_pose["x"], centroid_y - robot_pose["y"])
        bearing = math.atan2(centroid_y - robot_pose["y"], centroid_x - robot_pose["x"])
        rel_heading = self.normalize_angle(bearing - robot_pose["yaw"])

        local_x, local_y = self.map_to_base(centroid_x, centroid_y, robot_pose)
        inside_footprint = self.is_inside_footprint(local_x, local_y)
        too_close = dist < self.min_goal_distance

        rows_i = [c[0] for c in cluster]
        cols_i = [c[1] for c in cluster]
        min_row, max_row = min(rows_i), max(rows_i)
        min_col, max_col = min(cols_i), max(cols_i)

        bbox_h_cells = (max_row - min_row + 1)
        bbox_w_cells = (max_col - min_col + 1)
        bbox_area_cells = float(max(1, bbox_h_cells * bbox_w_cells))
        compactness = float(len(cluster) / bbox_area_cells)

        unknown_neighbors = 0
        free_neighbors = 0
        occupied_neighbors = 0

        h, w = grid.shape
        for r, c in cluster:
            r0 = max(0, r - 1)
            r1 = min(h, r + 2)
            c0 = max(0, c - 1)
            c1 = min(w, c + 2)
            neighborhood = grid[r0:r1, c0:c1]
            unknown_neighbors += int(np.count_nonzero(neighborhood == -1))
            free_neighbors += int(np.count_nonzero(neighborhood == 0))
            occupied_neighbors += int(np.count_nonzero(neighborhood > 0))

        total_neighbors = max(1, unknown_neighbors + free_neighbors + occupied_neighbors)
        free_ratio = free_neighbors / total_neighbors
        occupied_ratio = occupied_neighbors / total_neighbors

        in_front_of_robot = abs(rel_heading) <= (math.pi / 2.0)
        forward_alignment = max(0.0, math.cos(rel_heading))
        distance_score = 1.0 - self.clamp01(dist / self.distance_norm)

        revisited = self.candidate_is_revisited(centroid_x, centroid_y)

        reachability_score = self.clamp01(
            0.40 * free_ratio +
            0.20 * (1.0 if in_front_of_robot else 0.0) +
            0.20 * distance_score +
            0.20 * (0.0 if inside_footprint else 1.0)
        )

        risk_score = self.clamp01(
            0.50 * occupied_ratio +
            0.30 * (1.0 if inside_footprint else 0.0) +
            0.20 * (1.0 if too_close else 0.0)
        )

        size_score = self.clamp01(len(cluster) / max(1.0, float(self.min_cluster_size) * 6.0))
        heuristic_score = (
            0.30 * size_score +
            0.25 * reachability_score +
            0.20 * forward_alignment +
            0.15 * distance_score +
            0.10 * (1.0 - risk_score)
        )
        if revisited:
            heuristic_score -= 0.20
        heuristic_score = self.clamp01(heuristic_score)

        return {
            "id": -1,  # assigned later after sorting
            "row": float(mean_row),
            "col": float(mean_col),
            "centroid_x": float(centroid_x),
            "centroid_y": float(centroid_y),
            "cluster_size": int(len(cluster)),
            "bbox_min_row": int(min_row),
            "bbox_max_row": int(max_row),
            "bbox_min_col": int(min_col),
            "bbox_max_col": int(max_col),
            "bbox_width_m": float(bbox_w_cells * self.map.info.resolution),
            "bbox_height_m": float(bbox_h_cells * self.map.info.resolution),
            "distance_to_robot": float(dist),
            "bearing_to_robot": float(bearing),
            "relative_heading_error": float(rel_heading),
            "in_front_of_robot": bool(in_front_of_robot),
            "forward_alignment": float(forward_alignment),
            "inside_footprint": bool(inside_footprint),
            "too_close": bool(too_close),
            "unknown_neighbor_count": int(unknown_neighbors),
            "free_neighbor_count": int(free_neighbors),
            "occupied_neighbor_count": int(occupied_neighbors),
            "free_ratio": float(free_ratio),
            "occupied_ratio": float(occupied_ratio),
            "compactness": float(compactness),
            "reachability_score": float(reachability_score),
            "risk_score": float(risk_score),
            "revisited": bool(revisited),
            "heuristic_score": float(heuristic_score),
        }

    def detect_frontiers(self, robot_pose: Dict[str, float]) -> List[Dict[str, Any]]:
        if self.map is None:
            return []

        width = self.map.info.width
        height = self.map.info.height
        if len(self.map.data) != width * height:
            self.get_logger().warn("OccupancyGrid data size does not match width*height.")
            return []

        grid = np.array(self.map.data, dtype=np.int16).reshape((height, width))
        frontier_cells: List[GridCell] = []

        for row in range(1, height - 1):
            for col in range(1, width - 1):
                if grid[row, col] != 0:
                    continue

                neighborhood = grid[row - 1:row + 2, col - 1:col + 2]
                if not np.any(neighborhood == -1):
                    continue

                x, y = self.world_from_cell(row, col)
                if math.hypot(x - robot_pose["x"], y - robot_pose["y"]) >= self.min_goal_distance:
                    frontier_cells.append((row, col))

        clusters = self.cluster_frontiers_grid(frontier_cells)

        candidates: List[Dict[str, Any]] = []
        for cluster in clusters:
            if len(cluster) < self.min_cluster_size:
                continue

            candidate = self.compute_cluster_candidate(cluster, grid, robot_pose)
            if candidate["inside_footprint"] or candidate["too_close"]:
                continue
            candidates.append(candidate)

        candidates.sort(
            key=lambda c: (
                -c["cluster_size"],
                -c["heuristic_score"],
                c["distance_to_robot"],
                c["centroid_x"],
                c["centroid_y"],
            )
        )

        for idx, cand in enumerate(candidates):
            cand["id"] = idx

        return candidates

    def publish_frontier_pose_array(self, candidates: List[Dict[str, Any]], stamp_msg):
        pose_array = PoseArray()
        pose_array.header.frame_id = "map"
        pose_array.header.stamp = stamp_msg

        for cand in candidates:
            pose = Pose()
            pose.position.x = cand["centroid_x"]
            pose.position.y = cand["centroid_y"]
            pose.position.z = 0.0
            pose.orientation.w = 1.0
            pose_array.poses.append(pose)

        self.frontier_pub.publish(pose_array)
        self.latest_pose_array = pose_array

    def publish_markers(self, candidates: List[Dict[str, Any]], selected_id: Optional[int], stamp_msg):
        marker_array = MarkerArray()

        delete_all = Marker()
        delete_all.action = Marker.DELETEALL
        marker_array.markers.append(delete_all)

        marker_id = 0
        for cand in candidates:
            marker = Marker()
            marker.header.frame_id = "map"
            marker.header.stamp = stamp_msg
            marker.ns = "frontier_candidates"
            marker.id = marker_id
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            marker.pose.position.x = cand["centroid_x"]
            marker.pose.position.y = cand["centroid_y"]
            marker.pose.position.z = 0.08
            marker.pose.orientation.w = 1.0
            marker.scale.x = 0.16
            marker.scale.y = 0.16
            marker.scale.z = 0.16

            # Heuristic-based color: greener is better
            score = self.clamp01(cand["heuristic_score"])
            marker.color.r = float(1.0 - score)
            marker.color.g = float(score)
            marker.color.b = 0.0
            marker.color.a = 0.95
            marker_array.markers.append(marker)
            marker_id += 1

        if selected_id is not None and 0 <= selected_id < len(candidates):
            sel = candidates[selected_id]
            marker = Marker()
            marker.header.frame_id = "map"
            marker.header.stamp = stamp_msg
            marker.ns = "selected_frontier"
            marker.id = 9999
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            marker.pose.position.x = sel["centroid_x"]
            marker.pose.position.y = sel["centroid_y"]
            marker.pose.position.z = 0.14
            marker.pose.orientation.w = 1.0
            marker.scale.x = 0.28
            marker.scale.y = 0.28
            marker.scale.z = 0.28
            marker.color.r = 1.0
            marker.color.g = 0.0
            marker.color.b = 0.0
            marker.color.a = 1.0
            marker_array.markers.append(marker)

        self.marker_array_pub.publish(marker_array)

    def build_context(self, robot_pose: Dict[str, float], candidates: List[Dict[str, Any]]) -> str:
        current_target_match = self.nearest_candidate_to_pose(
            self.current_target_pose,
            candidates,
            self.current_target_reacquire_distance,
        )

        recent_targets = []
        for item in list(self.target_history)[-5:]:
            recent_targets.append({
                "id": int(item.get("id", -1)),
                "x": float(item.get("x", 0.0)),
                "y": float(item.get("y", 0.0)),
                "time_ns": int(item.get("time_ns", 0)),
            })

        frontiers_for_llm = []
        for c in candidates:
            frontiers_for_llm.append({
                "id": int(c["id"]),
                "x": round(float(c["centroid_x"]), 3),
                "y": round(float(c["centroid_y"]), 3),
                "cluster_size": int(c["cluster_size"]),
                "distance_to_robot": round(float(c["distance_to_robot"]), 3),
                "bearing_to_robot": round(float(c["bearing_to_robot"]), 3),
                "relative_heading_error": round(float(c["relative_heading_error"]), 3),
                "in_front_of_robot": bool(c["in_front_of_robot"]),
                "inside_footprint": bool(c["inside_footprint"]),
                "too_close": bool(c["too_close"]),
                "unknown_neighbor_count": int(c["unknown_neighbor_count"]),
                "free_neighbor_count": int(c["free_neighbor_count"]),
                "occupied_neighbor_count": int(c["occupied_neighbor_count"]),
                "compactness": round(float(c["compactness"]), 3),
                "reachability_score": round(float(c["reachability_score"]), 3),
                "risk_score": round(float(c["risk_score"]), 3),
                "revisited": bool(c["revisited"]),
                "heuristic_score": round(float(c["heuristic_score"]), 3),
            })

        context = {
            "robot": {
                "map_x": round(float(robot_pose["x"]), 3),
                "map_y": round(float(robot_pose["y"]), 3),
                "yaw": round(float(robot_pose["yaw"]), 3),
                "linear_vel": round(float(self.current_velocity["linear"]), 3),
                "angular_vel": round(float(self.current_velocity["angular"]), 3),
                "moving_forward": bool(self.current_velocity["linear"] > 0.05),
                "current_target_id": int(self.current_target_id),
                "current_target_pose": self.current_target_pose,
            },
            "map_info": {
                "resolution": float(self.map.info.resolution) if self.map else None,
                "origin_x": float(self.map.info.origin.position.x) if self.map else None,
                "origin_y": float(self.map.info.origin.position.y) if self.map else None,
                "width": int(self.map.info.width) if self.map else None,
                "height": int(self.map.info.height) if self.map else None,
            },
            "footprint": {
                "min_x": self.footprint_min_x,
                "max_x": self.footprint_max_x,
                "min_y": self.footprint_min_y,
                "max_y": self.footprint_max_y,
                "padding": self.footprint_padding,
            },
            "selection_state": {
                "force_replan": bool(self.force_replan),
                "current_target_still_valid": bool(current_target_match is not None),
                "current_target_nearest_candidate_id": (
                    int(current_target_match["id"]) if current_target_match is not None else None
                ),
                "current_target_distance_to_nearest_candidate": (
                    round(float(current_target_match["distance_to_current_target"]), 3)
                    if current_target_match is not None
                    else None
                ),
                "llm_min_confidence_to_switch": self.llm_min_confidence_to_switch,
            },
            "frontier_summary": {
                "num_candidates": len(candidates),
                "largest_cluster_size": max([c["cluster_size"] for c in candidates], default=0),
                "nearest_distance": round(min([c["distance_to_robot"] for c in candidates], default=0.0), 3),
                "best_heuristic_id": int(max(candidates, key=lambda c: c["heuristic_score"])["id"]) if candidates else None,
            },
            "recent_target_history": recent_targets,
            "frontiers": frontiers_for_llm,
        }

        return json.dumps(context, indent=2)

    def deterministic_fallback(self, candidates: List[Dict[str, Any]]) -> Optional[FrontierChoice]:
        if not candidates:
            return None

        # If the current target is still alive, keep it when reasonable.
        current_match = self.nearest_candidate_to_pose(
            self.current_target_pose,
            candidates,
            self.current_target_reacquire_distance,
        )
        if current_match is not None and not self.force_replan:
            return FrontierChoice(
                selected_frontier_id=int(current_match["id"]),
                reason="Keeping the current valid frontier target.",
                confidence=0.75,
            )

        best = max(candidates, key=lambda c: c["heuristic_score"])
        return FrontierChoice(
            selected_frontier_id=int(best["id"]),
            reason="Deterministic fallback chosen by heuristic score.",
            confidence=float(best["heuristic_score"]),
        )

    def choose_frontier(self, context_json: str, candidates: List[Dict[str, Any]]) -> Optional[FrontierChoice]:
        if self.llm_planner.enabled:
            try:
                decision = self.llm_planner.choose_frontier(context_json)
                if decision is not None:
                    return decision
            except Exception as e:
                self.get_logger().warn(f"LLM call failed; using fallback. Error: {e}")

        return self.deterministic_fallback(candidates)

    def publish_goal(self, candidate: Dict[str, Any]):
        goal_msg = PoseStamped()
        goal_msg.header.frame_id = "map"
        goal_msg.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.position.x = float(candidate["centroid_x"])
        goal_msg.pose.position.y = float(candidate["centroid_y"])
        goal_msg.pose.position.z = 0.0
        goal_msg.pose.orientation.w = 1.0

        self.goal_pub.publish(goal_msg)

        self.current_target_id = int(candidate["id"])
        self.current_target_pose = {
            "x": float(candidate["centroid_x"]),
            "y": float(candidate["centroid_y"]),
        }

        self.target_history.append({
            "id": int(candidate["id"]),
            "x": float(candidate["centroid_x"]),
            "y": float(candidate["centroid_y"]),
            "time_ns": int(self.get_clock().now().nanoseconds),
        })

        self.get_logger().info(
            f"Published goal: id={candidate['id']} x={candidate['centroid_x']:.2f} "
            f"y={candidate['centroid_y']:.2f}"
        )

    def detection_timer_callback(self):
        if not self.map_received or self.map is None:
            return

        robot_pose = self.get_robot_pose()
        if robot_pose is None:
            return

        candidates = self.detect_frontiers(robot_pose)
        self.latest_candidates = candidates

        stamp_msg = self.get_clock().now().to_msg()

        self.publish_frontier_pose_array(candidates, stamp_msg)

        # Highlight current target if it still exists in the current candidate list.
        selected_id = None
        current_match = self.nearest_candidate_to_pose(
            self.current_target_pose,
            candidates,
            self.current_target_reacquire_distance,
        )
        if current_match is not None:
            selected_id = int(current_match["id"])

        self.publish_markers(candidates, selected_id, stamp_msg)

        self.get_logger().info(f"Detected {len(candidates)} frontier candidates")

    def decision_timer_callback(self):
        if not self.latest_candidates:
            return

        robot_pose = self.get_robot_pose()
        if robot_pose is None:
            return

        # Build the full compact decision context from the algorithmic state
        context_json = self.build_context(robot_pose, self.latest_candidates)

        self.get_logger().info(
            f"Selecting from {len(self.latest_candidates)} frontier candidates..."
        )

        decision = self.choose_frontier(context_json, self.latest_candidates)
        if decision is None:
            self.get_logger().warn("No frontier decision available.")
            return

        self.last_llm_choice = decision

        chosen_id = int(decision.selected_frontier_id)
        if not (0 <= chosen_id < len(self.latest_candidates)):
            self.get_logger().warn(
                f"LLM returned invalid frontier ID: {chosen_id}. Using fallback."
            )
            fallback = self.deterministic_fallback(self.latest_candidates)
            if fallback is None:
                return
            decision = fallback
            chosen_id = int(decision.selected_frontier_id)

        chosen_candidate = self.latest_candidates[chosen_id]

        # Final hard safety guard before publishing
        if chosen_candidate["inside_footprint"] or chosen_candidate["too_close"]:
            self.get_logger().warn(
                "Chosen frontier failed hard safety checks. Using fallback."
            )
            fallback = self.deterministic_fallback(self.latest_candidates)
            if fallback is None:
                return
            decision = fallback
            chosen_id = int(decision.selected_frontier_id)
            chosen_candidate = self.latest_candidates[chosen_id]

        # Oscillation guard: if current target is still valid and the new choice
        # is low confidence, keep the current target.
        current_match = self.nearest_candidate_to_pose(
            self.current_target_pose,
            self.latest_candidates,
            self.current_target_reacquire_distance,
        )
        if (
            current_match is not None
            and not self.force_replan
            and chosen_id != int(current_match["id"])
            and float(decision.confidence) < self.llm_min_confidence_to_switch
        ):
            self.get_logger().info(
                "Keeping current target because it is still valid and LLM confidence is low."
            )
            chosen_candidate = current_match
            chosen_id = int(current_match["id"])

        # Avoid republishing the exact same goal over and over
        should_publish = True
        if self.current_target_pose is not None:
            same_target_dist = math.hypot(
                chosen_candidate["centroid_x"] - self.current_target_pose["x"],
                chosen_candidate["centroid_y"] - self.current_target_pose["y"],
            )
            if same_target_dist < 0.20 and not self.force_replan:
                should_publish = False

        if should_publish:
            self.publish_goal(chosen_candidate)
            self.get_logger().info(
                f"LLM choice: id={chosen_id} conf={float(decision.confidence):.2f} "
                f"reason={decision.reason}"
            )
        else:
            self.get_logger().info(
                f"Target unchanged; not republishing. id={chosen_id}"
            )

        # Refresh markers with the new selected target highlighted
        stamp_msg = self.get_clock().now().to_msg()
        self.publish_markers(self.latest_candidates, chosen_id, stamp_msg)

        self.force_replan = False


def main(args=None):
    rclpy.init(args=args)
    node = LLMFrontierExplorer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()