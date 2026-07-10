# LLM Mission Planning + Nav2 Execution

## Testing / How to Run

Run the system in this order:

```bash
ros2 launch llm_simulation gz.launch.py
ros2 launch llm_description spawn_bot.launch.py
ros2 run llm_prompt llm_robot_controller
ros2 run llm_navigation nav2_goal
```

## What each step does

### `ros2 launch llm_simulation gz.launch.py`
Starts the Gazebo simulation environment.

### `ros2 launch llm_description spawn_bot.launch.py`
Spawns the robot model into the simulation.

### `ros2 run llm_navigation llm_robot_controller`
Starts the LLM-based mission planner.  
It reads a user command, converts it into a structured mission plan, validates it, and executes it through the robot interface.

### `ros2 run llm_navigation nav2_goal`
Starts the Nav2 goal bridge node.  
It listens on `/goal_given`, converts the received goal string into a proper `NavigateToPose` action goal, and sends it to Nav2.

---

## Expected Result

- The user types a natural language routing command.
- The LLM converts it into a structured mission plan.
- The validator checks that the plan is safe and within limits.
- The executor sends either:
  - direct velocity commands on `/cmd_vel`, or
  - a goal request on `/goal_given`
- `nav2_goal` receives the goal request and forwards it to Nav2.
- The robot moves in simulation according to the planned mission.

---

## Before Running

Make sure:

- The ROS 2 workspace is built successfully.
- The environment is sourced.
- `GOOGLE_API_KEY` is set in the terminal.
- Nav2 is running if you want to use `navigate_to_pose`.
- The robot is spawned correctly in Gazebo.
- The `/cmd_vel` topic is connected to the base controller.
- The `/goal_given` topic is available for goal forwarding.

Example:

```bash
export GOOGLE_API_KEY=your_api_key_here
source install/setup.bash
```

---

## Short Description of the Code

This project is a simple LLM-driven robot mission pipeline:

1. User gives a route command in text.
2. The LLM converts it into a structured mission plan.
3. Safety rules validate the mission.
4. The executor performs the mission.
5. If the mission contains a navigation goal, it is forwarded to Nav2.

---

## 1) `llm_robot_controller.py`

This is the main orchestration node.

### Main idea
- Takes a user command.
- Sends it to Gemini through LangChain.
- Forces the output into a structured schema.
- Validates the plan using guardrails.
- Executes the plan through a deterministic executor.

### Key parts

#### `MissionTask`
Represents one action in the mission.

Supported actions:
- `cmd_vel`
- `navigate_to_pose`
- `stop`

#### `MissionPlan`
Represents the full mission:
- `mission_name`
- `tasks`

#### `LLMPlanner`
This class:
- loads `gemini-2.5-flash`
- wraps it with structured output
- prompts it to generate a mission plan from natural language

#### `MissionValidator`
This class checks:
- total number of tasks
- command velocity limits
- navigation coordinate sanity
- duration limits
- unsupported actions

#### `RobotDeterministicExecutor`
This class:
- executes the validated mission step by step
- publishes velocity commands through `executor`
- forwards navigation goals when needed
- stops the robot at the end

### Supported mission actions

#### `cmd_vel`
Direct velocity control.

Parameters:
- `linear_x`
- `angular_z`
- `duration_sec`

#### `navigate_to_pose`
High-level navigation request.

Parameters:
- `x`
- `y`
- `yaw`
- `frame_id`

#### `stop`
Stops the robot for a period of time.

Parameters:
- `duration_sec`

---

## 2) `execute.py`

This file contains the low-level execution helper.

### Main idea
It provides direct robot interaction utilities:

- publishes `/cmd_vel`
- publishes `/goal_given`
- stops the robot safely

### Important methods

#### `send_cmd_vel(linear_x, angular_z, duration)`
Publishes a Twist command repeatedly for the requested duration.

#### `send_nav_goal(x, y, yaw, frame_id)`
Publishes a goal request as a string on `/goal_given`.

#### `stop()`
Publishes a zero Twist message to stop the robot.

---

## 3) `nav2_goal.py`

This node bridges the custom goal request to Nav2.

### Main idea
- Subscribes to `/goal_given`
- Parses the goal string
- Builds a `NavigateToPose` goal
- Sends the goal to Nav2 action server

### Flow
1. Receives a string like:
   ```text
   x:1.0, y:2.0, yaw:0.0, frame_id:map
   ```
2. Parses `x`, `y`, `yaw`, and `frame_id`
3. Converts yaw into a quaternion
4. Creates a `PoseStamped`
5. Sends the goal to Nav2 using `NavigateToPose`

### Why this node is needed
The mission executor does not directly talk to the Nav2 action server.  
Instead, it publishes a simple message on `/goal_given`, and this node translates it into a proper navigation goal.

---

## Data Flow Between Components

```text
User command
    |
    v
llm_robot_controller
    |
    | 1. LLM planning
    | 2. safety validation
    | 3. deterministic execution
    |
    +--> /cmd_vel  -----------------> Robot base controller
    |
    +--> /goal_given ----------------> nav2_goal
                                         |
                                         v
                                 Nav2 NavigateToPose
                                         |
                                         v
                                   Robot navigation
```

---

## Code Explanation in Simple Words

### `llm_robot_controller.py`
This code takes a sentence from the user, asks the LLM to turn it into a robot plan, checks whether the plan is safe, and then executes it.

### `execute.py`
This code directly sends motion commands or navigation requests to the robot.

### `nav2_goal.py`
This code listens for goal requests and passes them to Nav2 in the correct format.

---

## Output Topics

### Published by executor
- `/cmd_vel`
- `/goal_given`

### Consumed by Nav2 bridge
- `/goal_given`

### Consumed by robot base controller
- `/cmd_vel`

---

## Common Checks if It Does Not Work

- Confirm `GOOGLE_API_KEY` is valid.
- Confirm the workspace is sourced.
- Confirm `llm_robot_controller.py`, `execute.py`, and `nav2_goal.py` are in the correct package path.
- Confirm `/cmd_vel` is not already controlled by another node.
- Confirm Nav2 action server is running.
- Confirm `/goal_given` messages are being published.
- Confirm the parser format matches exactly:
  ```text
  x:1.0, y:2.0, yaw:0.0, frame_id:map
  ```

---

## Final Notes

This project combines:

- LLM-based planning
- safety validation
- direct velocity execution
- Nav2 navigation goal forwarding

It gives a simple and auditable way to convert text instructions into robot motion.

The design is modular, so later you can add:
- better memory
- richer action types
- obstacle-aware safety checks
- tighter Nav2 feedback handling
- improved goal parsing
