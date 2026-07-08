#!/usr/bin/env python3
import math
import os
import time
from typing import Any, Callable, Dict, List, Literal, Tuple

import rclpy
from geometry_msgs.msg import PoseStamped, Twist
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from execute import executor


# Validated Mission JSON (Schemas Layer)
class MissionTask(BaseModel):
    action: Literal["cmd_vel", "navigate_to_pose", "stop"] = Field(
        ...,
        description="Task name. Supported actions: cmd_vel, navigate_to_pose, stop"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific parameters"
    )


class MissionPlan(BaseModel):
    mission_name: str = Field(..., description="Short descriptive name of the route")
    tasks: List[MissionTask] = Field(..., description="Sequential list of tasks to execute")


# LLM Interfacing
class LLMPlanner:
    def __init__(self):
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0
        )

        self.structured_llm = llm.with_structured_output(MissionPlan)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are the high-level mission planner for a mobile robot.

Convert the user's instruction into a sequential mission JSON with only these actions:

1) cmd_vel
   params:
   - linear_x: float   (m/s)
   - angular_z: float  (rad/s)
   - duration_sec: float

2) navigate_to_pose
   params:
   - x: float
   - y: float
   - yaw: float        (radians)
   - frame_id: string  (usually "map")

3) stop
   params:
   - duration_sec: float

Rules:
- Produce only supported actions.
- Keep the mission sequential.
- Prefer simple, auditable task sequences.
- Do not directly control the robot. Only produce mission JSON.
- For route-like commands, break them into tasks logically.
"""),
            ("human", "{user_input}")
        ])

        self.chain = self.prompt | self.structured_llm

    def plan_mission(self, user_input: str) -> MissionPlan:
        return self.chain.invoke({"user_input": user_input})


# ==============================================================================
# 3. GUARDRAIL LAYER (Safety Verification)
# ==============================================================================

class MissionValidator:
    def __init__(self):
        self.MAX_TOTAL_TASKS = 30

        # cmd_vel safety limits
        self.MAX_LINEAR_X = 1.0      # m/s
        self.MAX_ANGULAR_Z = 1.5     # rad/s
        self.MAX_CMD_DURATION = 60.0 # sec

        # navigation safety limits
        self.MAX_ABS_COORD = 100.0   # map-bound sanity check
        self.MAX_ABS_YAW = 2 * math.pi

        # stop limits
        self.MAX_STOP_DURATION = 10.0

    def _is_finite_number(self, value: Any) -> bool:
        try:
            return isinstance(value, (int, float)) and math.isfinite(float(value))
        except Exception:
            return False

    def validate(self, plan: MissionPlan) -> Tuple[bool, str]:
        if len(plan.tasks) > self.MAX_TOTAL_TASKS:
            return False, f"Rejected: too many tasks ({len(plan.tasks)} > {self.MAX_TOTAL_TASKS})."

        for idx, task in enumerate(plan.tasks, start=1):
            action = task.action
            p = task.params

            if action == "cmd_vel":
                required = ["linear_x", "angular_z", "duration_sec"]
                for key in required:
                    if key not in p:
                        return False, f"Task #{idx}: missing '{key}' for cmd_vel."

                if not all(self._is_finite_number(p[k]) for k in required):
                    return False, f"Task #{idx}: cmd_vel parameters must be finite numbers."

                linear_x = float(p["linear_x"])
                angular_z = float(p["angular_z"])
                duration_sec = float(p["duration_sec"])

                if abs(linear_x) > self.MAX_LINEAR_X:
                    return False, f"Task #{idx}: linear_x out of bounds."
                if abs(angular_z) > self.MAX_ANGULAR_Z:
                    return False, f"Task #{idx}: angular_z out of bounds."
                if duration_sec <= 0 or duration_sec > self.MAX_CMD_DURATION:
                    return False, f"Task #{idx}: duration_sec out of bounds."

            elif action == "navigate_to_pose":
                required = ["x", "y", "yaw"]
                for key in required:
                    if key not in p:
                        return False, f"Task #{idx}: missing '{key}' for navigate_to_pose."

                if not all(self._is_finite_number(p[k]) for k in required):
                    return False, f"Task #{idx}: navigate_to_pose parameters must be finite numbers."

                x = float(p["x"])
                y = float(p["y"])
                yaw = float(p["yaw"])
                frame_id = str(p.get("frame_id", "map"))

                if abs(x) > self.MAX_ABS_COORD or abs(y) > self.MAX_ABS_COORD:
                    return False, f"Task #{idx}: goal coordinates look unreasonable."
                if abs(yaw) > self.MAX_ABS_YAW:
                    return False, f"Task #{idx}: yaw out of sane bounds."
                if not frame_id:
                    return False, f"Task #{idx}: frame_id cannot be empty."

            elif action == "stop":
                duration_sec = float(p.get("duration_sec", 0.0))
                if not self._is_finite_number(duration_sec):
                    return False, f"Task #{idx}: stop duration must be a finite number."
                if duration_sec < 0 or duration_sec > self.MAX_STOP_DURATION:
                    return False, f"Task #{idx}: stop duration out of bounds."

            else:
                return False, f"Task #{idx}: unsupported action '{action}'."

        return True, "Mission validated and safe."


# ==============================================================================
# 4. DETERMINISTIC EXECUTOR LAYER
# ==============================================================================

class RobotDeterministicExecutor(Node):
    def __init__(self):
        super().__init__("deterministic_executor")

        # FIX: Renamed from self.executor to self.robot_interface
        self.robot_interface = executor() 

        self.registry: Dict[str, Callable[[MissionTask], None]] = {
            "cmd_vel": self._execute_cmd_vel,
            "navigate_to_pose": self._execute_navigate_to_pose,
            "stop": self._execute_stop,
        }

    def execute_mission(self, plan: MissionPlan):
        self.get_logger().info(f"Starting mission: '{plan.mission_name}'")

        for idx, task in enumerate(plan.tasks, start=1):
            self.get_logger().info(f"Step [{idx}/{len(plan.tasks)}]: {task.action} -> {task.params}")
            handler = self.registry.get(task.action)
            if handler is None:
                raise ValueError(f"No executor available for action '{task.action}'")
            handler(task)

        # UPDATE:
        self.robot_interface.stop()
        self.get_logger().info("Mission completed.")

    def _publish_zero(self):
        # UPDATE:
        self.robot_interface.stop()

    def _execute_cmd_vel(self, task: MissionTask):
        # UPDATE:
        self.robot_interface.send_cmd_vel(
            linear_x=float(task.params["linear_x"]),
            angular_z=float(task.params["angular_z"]),
            duration=float(task.params["duration_sec"])
        )

    def _execute_stop(self, task: MissionTask):
        duration_sec = float(task.params.get("duration_sec", 0.0))
        # UPDATE:
        self.robot_interface.send_cmd_vel(
            linear_x=0.0,
            angular_z=0.0,
            duration=duration_sec
        )

    def _execute_navigate_to_pose(self, task: MissionTask):
        x = float(task.params["x"])
        y = float(task.params["y"])
        yaw = float(task.params["yaw"])
        frame_id = "map"
        # UPDATE:
        self.robot_interface.send_nav_goal(x=x, y=y, yaw=yaw, frame_id=frame_id)
# ==============================================================================
# 5. ORCHESTRATION LOOP
# ==============================================================================

def main():
    rclpy.init()

    planner = LLMPlanner()
    validator = MissionValidator()
    executor_node = RobotDeterministicExecutor()

    print("\n--- LLM Mission Planning Interface Active ---")
    print("Supported actions: cmd_vel, navigate_to_pose, stop")
    print("Type 'exit' or 'quit' to stop.\n")

    try:
        while True:
            user_prompt = input("Enter routing command: ").strip()
            if user_prompt.lower() in ["exit", "quit"]:
                break

            try:
                print("\nLLM is compiling mission blueprint...")
                raw_plan = planner.plan_mission(user_prompt)
                print(f"\nCompiled Plan Draft:\n{raw_plan.model_dump_json(indent=2)}")

                is_safe, message = validator.validate(raw_plan)
                print(f"\nGuardrail Status: {message}")

                if is_safe:
                    executor_node.execute_mission(raw_plan)
                else:
                    print("Mission execution blocked due to safety violations.\n")

            except Exception as e:
                print(f"Flow error: {e}\n")

    finally:
        executor_node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()