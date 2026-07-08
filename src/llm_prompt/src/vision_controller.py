#!/usr/bin/env python3
import os
from typing import Any, Dict, List, Literal, Tuple

import rclpy
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# Import your executor interface
from vision_functions import VisionRobotExecutor


# ==========================================
# 1. SCHEMAS
# ==========================================
class MissionTask(BaseModel):
    action: Literal["conditional_vision_track", "stop"] = Field(
        ...,
        description="Action type. conditional_vision_track means watching and following a target."
    )
    params: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")


class MissionPlan(BaseModel):
    mission_name: str
    tasks: List[MissionTask]


# ==========================================
# 2. LLM PLANNER
# ==========================================
class LLMPlanner:
    def __init__(self):
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        self.structured_llm = llm.with_structured_output(MissionPlan)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are a mission planner. Produce a sequential JSON mission.

Available Actions:
1) conditional_vision_track
   params:
   - target_class (string, e.g., 'person', 'backpack')
   - maintain_distance (float, meters)
   - timeout_sec (float)
   - take_snapshot (bool)

2) stop
   params:
   - duration_sec (float)
"""),
            ("human", "{user_input}")
        ])

        self.chain = self.prompt | self.structured_llm

    def plan_mission(self, user_input: str) -> MissionPlan:
        return self.chain.invoke({"user_input": user_input})


# ==========================================
# 3. THE GUARDRAIL
# ==========================================
class MissionValidator:
    def __init__(self):
        self.ALLOWED_TARGETS = ["person", "backpack", "forklift"]
        self.MIN_FOLLOW_DIST = 1.5  # Safety: Never get closer than 1.5m

    def validate(self, plan: MissionPlan) -> Tuple[bool, str]:
        for idx, task in enumerate(plan.tasks):
            p = task.params

            if task.action == "conditional_vision_track":
                if p.get("target_class") not in self.ALLOWED_TARGETS:
                    return False, f"Task #{idx}: Unrecognized target '{p.get('target_class')}'."

                if float(p.get("maintain_distance", 0)) < self.MIN_FOLLOW_DIST:
                    return False, (
                        f"Task #{idx}: Follow distance too close! "
                        f"Must be >= {self.MIN_FOLLOW_DIST}m."
                    )

            elif task.action == "stop":
                if float(p.get("duration_sec", 0)) < 0:
                    return False, f"Task #{idx}: stop duration cannot be negative."

        return True, "Vision guardrails passed."


# ==========================================
# 4. ORCHESTRATOR
# ==========================================
def main():
    rclpy.init()
    executor_node = VisionRobotExecutor()
    planner = LLMPlanner()
    validator = MissionValidator()

    user_input = (
        "If you see a person, snap a pic and follow them at 2 meters for 30 seconds."
    )

    print("LLM is planning...")
    plan = planner.plan_mission(user_input)
    print(f"Plan Draft: {plan.model_dump_json(indent=2)}")

    is_safe, msg = validator.validate(plan)
    print(f"Guardrail Check: {msg}")

    if is_safe:
        for task in plan.tasks:
            if task.action == "conditional_vision_track":
                if task.params.get("take_snapshot"):
                    executor_node.capture_snapshot(task.params["target_class"])

                executor_node.conditional_follow(
                    target_class=task.params["target_class"],
                    maintain_distance=task.params["maintain_distance"],
                    timeout=task.params["timeout_sec"]
                )

            elif task.action == "stop":
                executor_node.stop()

    executor_node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()