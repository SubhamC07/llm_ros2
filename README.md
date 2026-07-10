# LLM-ROS2

A ROS 2 Humble project demonstrating how **Large Language Models (LLMs)** can be integrated with classical robotics algorithms to perform high-level robot control. The project combines natural language understanding, autonomous navigation, mapping, and perception inside a Gazebo simulation.

The repository is intended as a collection of practical examples showing how LLMs can act as a high-level planner while ROS 2 nodes execute deterministic and safe robot behaviors.

---

## Features

- 🤖 LLM-based mission planning using Google Gemini
- 🗺️ Autonomous frontier-based exploration
- 🚶 RGB-D person detection and following using YOLOv8
- 🧭 Nav2 goal execution
- 🛡️ Safety guardrails for LLM-generated commands
- 🌍 Gazebo simulation environment
- 📦 Modular ROS2 package structure

---

## Project Structure

```
llm_ros2/
│
├── docs/
│   ├── AUTONOMOUS MAPPING OF UNEXPLORED SPACE.md
│   ├── AUTONOMOUS PERSON FOLLOWING.md
│   └── SIMPLE LLM ROBOT CONTROLLER.md
│
├── llm_description/
│
├── llm_navigation/
│
├── llm_prompt/
│
├── llm_simulation/
│
└── README.md
│
└── README_INSTALLATION.md
```

---

# Repository Overview

## llm_simulation

Contains the Gazebo simulation world used throughout the project.

Provides

- Simulation environment
- World configuration
- Robot testing environment

---

## llm_description

Contains the robot description.

Includes

- URDF/Xacro
- Robot meshes
- Sensors
- Launch files for spawning the robot

---

## llm_navigation

Implements the robot navigation and perception algorithms.

Includes examples such as

- Person Following
- Nav2 Goal Interface
- Navigation utilities
- Motion controllers

---

## llm_prompt

Contains the LLM integration layer.

This package converts natural language instructions into structured robot missions while applying safety validation before execution.

---

## docs

Detailed documentation for each implemented project.

| Document | Description |
|-----------|-------------|
| `autonomous_mapping.md` | Complete explanation of frontier-based autonomous mapping. |
| `autonomous_person_following_rgbd_yolov8.md` | RGB-D YOLOv8 person following implementation and testing guide. |
| `llm_mission_planning_nav2.md` | LLM mission planning, guardrails and Nav2 execution pipeline. |

These documents include:

- Setup
- Testing procedure
- Code explanation
- Node communication
- Data flow
- Implementation details

---

## Project Modules

## 1. Autonomous Mapping

Performs exploration of unknown environments using frontier-based exploration.

### Flow

```
Laser Scan
      │
      ▼
SLAM Toolbox
      │
      ▼
Occupancy Grid
      │
      ▼
Frontier Detection
      │
      ▼
Frontier Selection
      │
      ▼
Navigation Goal
      │
      ▼
Robot Movement
```

📖 Documentation

```
docs/autonomous_mapping.md
```

---

## 2. RGB-D Person Following

Uses YOLOv8 to detect pedestrians and depth images to estimate distance before commanding the robot to follow the detected person.

### Flow

```
RGB Camera
      │
Depth Camera
      │
      ▼
YOLOv8 Detection
      │
      ▼
Depth Estimation
      │
      ▼
Target Position
      │
      ▼
Velocity Controller
      │
      ▼
Robot Motion
```

📖 Documentation

```
docs/autonomous_person_following_rgbd_yolov8.md
```

---

## 3. LLM Mission Planning

Allows users to control the robot using natural language.

The LLM generates a structured mission, validates it using predefined safety rules, and executes the approved actions through deterministic ROS2 nodes.

### Flow

```
User Prompt
      │
      ▼
Gemini LLM
      │
      ▼
Mission Plan
      │
      ▼
Safety Validator
      │
      ▼
Deterministic Executor
      │
      ▼
Nav2 / cmd_vel
      │
      ▼
Robot
```

📖 Documentation

```
docs/llm_mission_planning_nav2.md
```

---

## High-Level Architecture

```
                   User
                     │
                     ▼
          Natural Language Prompt
                     │
                     ▼
                 Gemini LLM
                     │
          Structured Mission Plan
                     │
                     ▼
             Safety Guardrails
                     │
                     ▼
         Deterministic ROS2 Nodes
          │                  │
          │                  │
     Navigation         Perception
          │                  │
          └──────────┬───────┘
                     │
                     ▼
                  Robot
```

---

## Technologies Used

- ROS2 Humble
- Python
- Gazebo
- Nav2
- SLAM Toolbox
- YOLOv8
- OpenCV
- Google Gemini API
- LangChain
- Pydantic

---

## Documentation

The repository contains detailed documentation for every major implementation inside the **docs** directory.

- 📄 `docs/autonomous_mapping.md`
- 📄 `docs/autonomous_person_following_rgbd_yolov8.md`
- 📄 `docs/llm_mission_planning_nav2.md`

Each document explains:

- Implementation overview
- How to run
- ROS2 nodes
- Data flow
- Algorithm summary
- Testing procedure

---

## Future Work

- Multi-agent coordination
- Vision-language navigation
- Semantic mapping
- Dynamic obstacle avoidance
- Multi-person tracking
- Voice-controlled robot interaction
- Additional LLM providers
- Real robot deployment

---

## License

This project is intended for educational and research purposes.

---

## Author

**Subham Chhotaray**

---
Contributions, suggestions, and feedback are always welcome. Made with ❤️.

## Resources

| Resource | Purpose |
|----------|---------|
| [Human Follower Robotic Cart with YOLOv8](https://github.com/law4percent/human-follower-robotic-cart-with-yolov8) | Reference for the RGB-D person following pipeline, YOLOv8-based pedestrian detection, and control logic. |
| [Frontier Exploration](https://github.com/shimmer0909/Frontier-Exploration) | Reference implementation for frontier-based autonomous exploration and frontier selection concepts. |
| [TurtleBot3](https://github.com/robotis-git/turtlebot3) | Reference for the robot URDF. |
| [eYRC Krishi Cobot Repository](https://github.com/eYantra-Robotics-Competition/eyrc-25-26-krishi-cobot) | Source of the Gazebo worlds and simulation assets used for testing and evaluation. |

> These repositories served as references and inspiration during development. The implementation in this project has been adapted and integrated to fit the overall LLM-driven ROS 2 architecture.
