#!/usr/bin/env python3
import json
import os
import math
from typing import Any, Dict, List, Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

import tf2_ros
from tf2_ros import TransformException
from rclpy.time import Time
from rclpy.duration import Duration


class FrontierChoice(BaseModel):
    selected_frontier_id: int = Field(..., description="ID of the chosen frontier")
    reason: str = Field(default="", description="Short reason for the choice")


class FrontierLLMPlanner:
    def __init__(self):
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0,
        )

        self.structured_llm = llm.with_structured_output(FrontierChoice)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are a frontier selector for autonomous exploration.

You will be given:
- robot pose
- a list of frontier candidates from the occupancy grid

Choose exactly one frontier that is the best next exploration target.

Selection rules:
- Prefer frontiers with better exploration value.
- Prefer reachable-looking candidates.
- Prefer useful size / coverage over tiny fragments.
- Prefer points in front of the robot's current heading.
- Prefer backwards exploration only if no better options exist.
- Avoid choosing invalid or duplicate IDs.
- Return only a structured choice with the selected frontier ID and a short reason.
"""),
            ("human", "{frontier_context}")
        ])

        self.chain = self.prompt | self.structured_llm

    def choose_frontier(self, frontier_context: str) -> FrontierChoice:
        return self.chain.invoke({"frontier_context": frontier_context})


class FrontierToGoalNode(Node):
    def __init__(self):
        super().__init__("frontier_to_goal_node")

        self.frontier_sub = self.create_subscription(
            String,
            "/frontier_points",
            self.frontier_callback,
            10,
        )

        self.open_sub = self.create_subscription(
            Bool,
            "/open_to_goal",
            self.open_callback,
            10,
        )

        self.goal_pub = self.create_publisher(String, "/goal_given", 10)

        self.llm = FrontierLLMPlanner()

        self.map_frame_default = "map"
        self.latest_frontier_payload: Optional[Dict[str, Any]] = None
        self.open_to_goal: bool = False
        self.goal_sent_for_current_open: bool = False
        self.llm_busy: bool = False

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.get_logger().info("LLM frontier selector started.")
        self.get_logger().info("Waiting for /open_to_goal == True before selecting a frontier.")

    def open_callback(self, msg: Bool):
        self.open_to_goal = bool(msg.data)

        if self.open_to_goal:
            # New planning cycle can begin
            self.goal_sent_for_current_open = False
            self.try_select_and_publish_goal()
        else:
            # Goal is being executed or system is not ready
            self.goal_sent_for_current_open = False

    def frontier_callback(self, msg: String):
        try:
            payload = json.loads(msg.data)
        except Exception as e:
            self.get_logger().error(f"Failed to parse /frontier_points JSON: {e}")
            return

        self.latest_frontier_payload = payload
        self.try_select_and_publish_goal()

    def try_select_and_publish_goal(self):
        if not self.open_to_goal:
            return

        if self.goal_sent_for_current_open or self.llm_busy:
            return

        if self.latest_frontier_payload is None:
            return

        frontiers = self.latest_frontier_payload.get("frontiers", [])
        if not frontiers:
            self.get_logger().info("No frontier candidates available yet.")
            return

        frame_id = str(self.latest_frontier_payload.get("frame_id", self.map_frame_default))

        robot_pose = self.get_robot_pose()
        robot_pose_str = None
        if robot_pose is not None:
            robot_pose_str = {"x": round(robot_pose[0], 3), "y": round(robot_pose[1], 3)}
        else:
            robot_pose_str = "unavailable"

        frontier_context = json.dumps(
            {
                "frame_id": frame_id,
                "robot_pose": robot_pose_str,
                "frontiers": frontiers,
            },
            indent=2,
        )

        self.llm_busy = True
        try:
            choice = self.llm.choose_frontier(frontier_context)
        except Exception as e:
            self.llm_busy = False
            self.get_logger().error(f"LLM frontier selection failed: {e}")
            return

        self.llm_busy = False

        chosen = None
        for f in frontiers:
            try:
                if int(f.get("id", -1)) == int(choice.selected_frontier_id):
                    chosen = f
                    break
            except Exception:
                continue

        if chosen is None:
            self.get_logger().warn(
                f"LLM selected frontier id={choice.selected_frontier_id}, but it was not found in the current list."
            )
            return

        try:
            target_x = float(chosen["x"])
            target_y = float(chosen["y"])
        except Exception as e:
            self.get_logger().error(f"Chosen frontier is missing valid x/y fields: {e}")
            return

        # Frontiers are targets, so yaw can be simple.
        target_yaw = 0.0

        goal_str = f"x:{target_x:.3f}, y:{target_y:.3f}, yaw:{target_yaw:.3f}, frame_id:{frame_id}"

        out = String()
        out.data = goal_str
        self.goal_pub.publish(out)

        self.goal_sent_for_current_open = True
        self.get_logger().info(
            f"Published selected goal on /goal_given: {goal_str} | frontier_id={choice.selected_frontier_id} | reason={choice.reason}"
        )

    def get_robot_pose(self):
        try:
            tf = self.tf_buffer.lookup_transform(
                "map",
                "base_link",
                Time(),
                timeout=Duration(seconds=0.2),
            )
            return tf.transform.translation.x, tf.transform.translation.y
        except TransformException:
            return None


def main(args=None):
    rclpy.init(args=args)
    node = FrontierToGoalNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down frontier-to-goal node.")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()