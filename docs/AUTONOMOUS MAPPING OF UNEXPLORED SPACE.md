# Autonomous Mapping of Unexplored Space

---

## Video Demonstration

See the autonomous mapping pipeline in action, from simulation launch to frontier exploration:

[[Watch the demo]](https://youtu.be/dxaaw9Ef30I)

---

## Testing / Execution Order

Run the system in this order so each layer is available before the next one consumes its data.

### 1) Start the simulation
```bash
ros2 launch llm_simulation gz.launch.py
```

**What this does:** launches the Gazebo simulation environment.

### 2) Spawn the robot
```bash
ros2 launch llm_description spawn_bot.launch.py
```

**What this does:** inserts the robot model into the simulation.

### 3) Start frontier extraction
```bash
ros2 run llm_navigation frontier_explorer
```

**What this does:** reads `/map`, finds frontier cells, clusters them, and publishes frontier centroids.

### 4) Start SLAM
```bash
ros2 launch slam_toolbox online_async_launch.py use_sim_time:=true slam_params_file:=/home/subham/llm_ros2/src/llm_navigation/config/mapper_params_online_async.yaml
```

**What this does:** builds and updates the occupancy grid while the robot explores.

### 5) Start Nav2
```bash
ros2 launch nav2_bringup navigation_launch.py use_sim_time:=true params_file:=/home/subham/llm_ros2/src/llm_navigation/config/nav2_params.yaml
```

**What this does:** starts the navigation stack and brings up the `navigate_to_pose` action server.

### 6) Start the goal bridge
```bash
python3 nav2_open_goal.py
```

**What this does:** listens to `/goal_given` and forwards the latest pose to Nav2.

### 7) Start the autonomous mapping logic

For the LLM-based mode:
```bash
cd /llm_ros2/src/llm_prompt/src
python3 autonomous_mapping.py
```

For the simple algorithm-only deployment:
```bash
ros2 run llm_navigation frontier_selection
```

**What this does:** selects the best frontier and publishes it on `/goal_given`.

---

## How to verify it is working

1. `/map` should be publishing from `slam_toolbox`.
2. `/local_frontier_points` should appear after frontier extraction.
3. `/goal_given` should contain a moving frontier target.
4. Nav2 should accept the goal and move the robot.
5. RViz should show frontier markers and the selected goal marker.

Useful checks:

```bash
ros2 topic echo /goal_given
ros2 topic echo /local_frontier_points
ros2 topic echo /frontier_markers
ros2 topic list
ros2 action list | grep navigate_to_pose
```

---

## End-to-end flow

```text
Gazebo / Robot
   ↓
SLAM Toolbox builds /map
   ↓
frontier_explorer finds frontier centroids
   ↓
frontier_selection or autonomous_mapping chooses one
   ↓
/goal_given is published
   ↓
nav2_open_goal.py sends the goal to Nav2
   ↓
robot navigates
   ↓
repeat until the map is complete
```

---

## What each code file does

## 1) `frontier_explorer` / `LocalFrontierBundler`

This node is responsible for **finding raw frontier cells** from the occupancy grid.

### Main idea
A frontier cell is a **free cell** that has at least one **unknown neighbor**.  
That means the robot is standing at the edge of explored space.

### Inputs
- `/map` (`nav_msgs/OccupancyGrid`)
- `/frontier_reached` (`std_msgs/Bool`)

### Outputs
- `/local_frontier_points` (`geometry_msgs/PoseArray`)
- `/frontier_markers` (`visualization_msgs/MarkerArray`)

### What the code does
- Converts the occupancy grid into a NumPy grid.
- Scans every free cell.
- Checks whether any 8-connected neighbor is unknown (`-1`).
- Removes frontier cells that are too close to the robot.
- Clusters nearby frontier cells using BFS.
- Computes centroid for each cluster.
- Publishes the centroids as candidate goals.

### Important parameters
- `base_frame`: robot base frame used for TF lookup.
- `min_goal_distance`: ignore frontiers too close to the robot.
- `min_cluster_size`: filter out tiny noisy frontier groups.
- `detection_period`: how often frontier detection runs.

### Why it matters
This is the **frontier extraction layer**.  
It does not decide the final goal. It only produces frontier candidates.

---

## 2) `frontier_selection` / `FrontierSelector` (simple algorithm version)

This node is the **goal decision layer** for algorithm-only deployment.

### Main idea
It receives frontier centroids, scores them, and chooses the best one.

### Inputs
- `/local_frontier_points`
- `/map`

### Outputs
- `/goal_given` (`geometry_msgs/PoseStamped`)
- `/selected_frontier_marker` (`visualization_msgs/Marker`)

### What the code does
- Reads the robot pose from TF.
- Keeps track of:
  - current goal
  - visited goals
  - blacklisted goals
- Scores each frontier by:
  - distance to robot
  - heading alignment
  - hysteresis bonus to reduce goal switching
  - optional front-facing preference
- Rejects goals that are:
  - already visited
  - blacklisted
  - too close to obstacles
- Publishes the best frontier continuously on `/goal_given`.

### Goal switching logic
The node avoids unstable jumping between targets.

It only switches if the new frontier is **better enough** than the current one by `switching_threshold`.

### Why it matters
This is the **simple deployable planner**.  
It gives you autonomous mapping without needing the LLM layer.

---

## 3) `nav2_open_goal.py` / `ContinuousGoalUpdater`

This node is the **bridge between frontier selection and Nav2**.

### Main idea
Whenever a new pose arrives on `/goal_given`, it sends it directly to the Nav2 `navigate_to_pose` action server.

### Inputs
- `/goal_given` (`geometry_msgs/PoseStamped`)

### Outputs
- Nav2 action goal: `navigate_to_pose`

### What the code does
- Waits for Nav2 action server.
- Subscribes to `/goal_given`.
- On every new goal:
  - copies the pose
  - fills missing frame data
  - sends the goal to Nav2
- Nav2 then preempts the old goal automatically if a new one arrives.

### Why it matters
This node is the **execution interface**.  
Without it, frontier selection would not actually move the robot.

---

## 4) `autonomous_mapping.py` / LLM-based mapping controller

This is the **LLM-enhanced version** of the same pipeline.

### Main idea
It adds command understanding so the user can say things like:
- complete mapping
- map indefinitely
- map for 5 minutes
- stop mapping

### Inputs
- terminal prompt
- `/llm_command` (`std_msgs/String`)
- `/local_frontier_points`
- `/map`

### Outputs
- `/goal_given`
- `/selected_frontier_marker`

### What the code does
- Uses Gemini if available.
- Falls back to keyword-based parsing if Gemini is not available.
- Converts user intent into one of these mapping modes:
  - `indefinite`
  - `timed`
  - `complete`
  - `stop`
- Uses the same frontier scoring and goal switching logic as the algorithm-only version.
- Stops when:
  - time limit is reached
  - no frontiers remain in complete mode
  - user requests stop

### Why it matters
This gives **natural language control** over exploration.

---

## Code-level explanation of the full pipeline

### Frontier extraction
The frontier extractor finds the border between known free space and unknown space.

### Frontier scoring
The selector ranks each frontier by:
- closeness
- heading alignment
- safety from obstacles
- stability of the current target

### Goal publication
The selected goal is published as a `PoseStamped` so Nav2 can consume it.

### Navigation execution
Nav2 receives the pose and plans a path to it.

### Repeat cycle
After the robot moves and the map grows, new frontiers appear, and the cycle repeats.

---

## Recommended deployment choice

### Use the algorithm-only version when you want:
- simpler debugging
- predictable behavior
- no API dependency
- fast on-robot deployment

Command:
```bash
ros2 run llm_navigation frontier_selection
```

### Use the LLM version when you want:
- command-based exploration control
- timed mapping
- stop / complete / indefinite modes
- more flexible human interaction

Command:
```bash
python3 autonomous_mapping.py
```

---

## Expected topic and action map

### Topics
- `/map`
- `/local_frontier_points`
- `/frontier_markers`
- `/goal_given`
- `/selected_frontier_marker`
- `/llm_command` (LLM mode)

### Action
- `navigate_to_pose`

---

## Testing checklist

### Simulation and map generation
- [ ] Gazebo launches correctly
- [ ] Robot spawns correctly
- [ ] `slam_toolbox` publishes `/map`
- [ ] TF tree is valid (`map -> odom -> base_footprint`)

### Frontier extraction
- [ ] `/local_frontier_points` is published
- [ ] frontier markers are visible in RViz
- [ ] frontier clusters are not too noisy

### Goal selection
- [ ] `/goal_given` updates continuously
- [ ] selected frontier marker is visible
- [ ] goals are not switching too rapidly

### Navigation
- [ ] Nav2 accepts the goal
- [ ] robot starts moving toward the frontier
- [ ] goal gets replaced when a better frontier appears

### Mapping completion
- [ ] unknown regions shrink as robot explores
- [ ] exploration stops in complete mode when no safe frontiers remain

---

## Notes for debugging

### If no frontiers appear
- check `/map`
- check if map frame is correct
- verify the robot is actually exploring new space
- confirm unknown cells exist in the occupancy grid

### If goals are not sent to Nav2
- check `/goal_given`
- check `nav2_open_goal.py`
- verify `navigate_to_pose` action exists

### If robot keeps switching targets too often
- increase `switching_threshold`
- increase `weight_hysteresis`
- increase `visited_radius`

### If robot chooses unsafe goals
- increase `obstacle_safe_distance`
- confirm occupancy values are correct
- ensure the map resolution and origin are valid

---

## Final summary

This system is a layered autonomous exploration pipeline:

1. **SLAM** builds the map.
2. **Frontier extraction** finds unexplored edges.
3. **Frontier selection** chooses the best candidate.
4. **Goal bridge** sends the goal to Nav2.
5. **Nav2** navigates the robot.
6. **LLM mode** adds natural-language control on top of the same logic.

The algorithm-only version is the cleanest option for deployment, while the LLM version adds higher-level control for experimentation.
