#!/usr/bin/env python3
import os
import json
import math
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.duration import Duration

from geometry_msgs.msg import PoseArray, PoseStamped
from nav_msgs.msg import Odometry
from tf2_ros import Buffer, TransformListener

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from rclpy.parameter import Parameter

# ---------------------------------------------------------
# LLM Setup (From your provided code)
# ---------------------------------------------------------
class FrontierChoice(BaseModel):
    selected_frontier_id: int = Field(..., description="ID of the chosen frontier")
    reason: str = Field(default="", description="Short reason for the choice")
    confidence: float = Field(default=0.0, description="Confidence from 0 to 1")

class FrontierLLMPlanner:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is not set. Please export it.")

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0,
        )

        self.structured_llm = llm.with_structured_output(FrontierChoice)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are a frontier selector for autonomous exploration.

You will be given a compact JSON context containing:
- robot map pose
- robot odom velocity
- current target frontier id
- recent target history
- a list of frontier candidates, each with metadata

Choose exactly one frontier that is the best next exploration target.

Selection rules:
- Prefer frontiers with higher exploration value.
- Prefer reachable candidates.
- Prefer larger cluster size and useful coverage.
- Prefer candidates that are not too far away.
- Prefer candidates in front of the robot when reasonable.
- Avoid oscillation: if the current target is still valid and similar in quality, keep it.
- Avoid invalid, duplicate, or missing IDs.
- Return only a structured choice with the selected frontier ID, a short reason, and a confidence value.
- Avoid any point inside of the robot's current footprint or too close to the robot.
- Current, footprint: "[[0.05, 0.3], [0.05, -0.3], [-0.65, -0.3], [-0.65, 0.3]]", with a padding of 0.2m
- Preference of frontiers that are in the direction of the robot's current velocity vector, if applicable.
- Prefer frontiers that are not in the same location as recently visited frontiers (avoid oscillation).
"""),
            ("human", "{frontier_context}")
        ])

        self.chain = self.prompt | self.structured_llm

    def choose_frontier(self, frontier_context: str) -> FrontierChoice:
        return self.chain.invoke({"frontier_context": frontier_context})

# ---------------------------------------------------------
# ROS 2 Interfacing Node
# ---------------------------------------------------------
class LLMFrontierNode(Node):
    def __init__(self):
        super().__init__("llm_frontier_explorer")
        self.set_parameters([
            Parameter("use_sim_time", Parameter.Type.BOOL, True)
        ])
        
        self.llm_planner = FrontierLLMPlanner()
        
        # State tracking
        self.latest_frontiers = None
        self.current_velocity = {"linear": 0.0, "angular": 0.0}
        self.current_target_id = -1
        self.target_history = []
        
        # We don't want to spam the LLM API every time a frontier point is published.
        # We will rate-limit the LLM calls to once every X seconds.
        self.declare_parameter("llm_call_period", 5.0)
        llm_period = self.get_parameter("llm_call_period").value
        
        # TF Setup for robot pose
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.base_frame = "base_footprint" # Or "base_link"
        
        # Publishers and Subscribers
        self.goal_pub = self.create_publisher(PoseStamped, "/goal_given", 10)
        
        self.frontier_sub = self.create_subscription(
            PoseArray,
            "/local_frontier_points",
            self.frontier_callback,
            10
        )
        
        self.odom_sub = self.create_subscription(
            Odometry,
            "/odom",
            self.odom_callback,
            10
        )
        
        # Timer to trigger LLM decision making
        self.timer = self.create_timer(llm_period, self.decision_timer_callback)
        
        self.get_logger().info("LLM Frontier Explorer initialized. Waiting for frontiers...")

    def odom_callback(self, msg: Odometry):
        """Keep track of current robot velocity for the LLM context."""
        self.current_velocity["linear"] = msg.twist.twist.linear.x
        self.current_velocity["angular"] = msg.twist.twist.angular.z

    def frontier_callback(self, msg: PoseArray):
        """Store the latest frontiers published by the bundler."""
        self.latest_frontiers = msg

    def get_robot_pose(self):
        """Look up the robot's pose in the map frame."""
        try:
            trans = self.tf_buffer.lookup_transform(
                "map",
                self.base_frame,
                rclpy.time.Time(),
                timeout=Duration(seconds=0.2),
            )
            return {
                "x": trans.transform.translation.x,
                "y": trans.transform.translation.y
            }
        except Exception as e:
            self.get_logger().warn(f"Could not get robot pose: {e}")
            return None

    def decision_timer_callback(self):
        """Periodically evaluate frontiers and send a goal to /goal_given."""
        if not self.latest_frontiers or not self.latest_frontiers.poses:
            return

        robot_pose = self.get_robot_pose()
        if not robot_pose:
            return

        # 1. Build the list of frontier candidates
        candidates = []
        for i, pose in enumerate(self.latest_frontiers.poses):
            # Calculate simple Euclidean distance to provide useful metadata to the LLM
            dist = math.hypot(pose.position.x - robot_pose["x"], pose.position.y - robot_pose["y"])
            candidates.append({
                "id": i,
                "x": round(pose.position.x, 2),
                "y": round(pose.position.y, 2),
                "distance_to_robot": round(dist, 2)
            })

        # 2. Construct the JSON context exactly as your prompt expects
        context_dict = {
            "robot_map_pose": robot_pose,
            "robot_odom_velocity": self.current_velocity,
            "current_target_id": self.current_target_id,
            "recent_target_history": self.target_history[-5:], # Keep last 5
            "frontiers": candidates
        }
        
        context_json = json.dumps(context_dict, indent=2)

        # 3. Query the LLM
        self.get_logger().info(f"Querying Gemini with {len(candidates)} frontiers...")
        try:
            decision = self.llm_planner.choose_frontier(context_json)
            self.get_logger().info(
                f"LLM Choice: ID {decision.selected_frontier_id} | "
                f"Reason: {decision.reason} | Conf: {decision.confidence:.2f}"
            )
        except Exception as e:
            self.get_logger().error(f"LLM API Call failed: {e}")
            return

        # 4. Validate and Publish the goal to /goal_given
        chosen_id = decision.selected_frontier_id
        if 0 <= chosen_id < len(self.latest_frontiers.poses):
            chosen_pose = self.latest_frontiers.poses[chosen_id]
            
            # Update history
            self.current_target_id = chosen_id
            if chosen_id not in self.target_history:
                self.target_history.append(chosen_id)

            # Construct PoseStamped for the Nav2 continuous updater
            goal_msg = PoseStamped()
            goal_msg.header.frame_id = "map"
            goal_msg.header.stamp = self.get_clock().now().to_msg()
            goal_msg.pose = chosen_pose

            self.goal_pub.publish(goal_msg)
            self.get_logger().info(f"Published new goal to /goal_given: X={chosen_pose.position.x:.2f}, Y={chosen_pose.position.y:.2f}")
        else:
            self.get_logger().warn(f"LLM returned invalid frontier ID: {chosen_id}")

def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = LLMFrontierNode()
        rclpy.spin(node)
    except RuntimeError as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        pass
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()