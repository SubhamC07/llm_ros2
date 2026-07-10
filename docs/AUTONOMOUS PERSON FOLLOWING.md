# Autonomous Person Following with RGB-D YOLOv8

## Testing / How to Run

Run the system in this exact order:

```bash
ros2 launch llm_simulation gz.launch.py
ros2 launch llm_description spawn_bot.launch.py
ros2 run llm_navigation person_detection_yolo
ros2 run llm_navigation follow_person
```

## What Each Step Does

### `ros2 launch llm_simulation gz.launch.py`
Starts the Gazebo simulation environment.

### `ros2 launch llm_description spawn_bot.launch.py`
Spawns the robot model into the simulation.

### `ros2 run llm_navigation person_detection_yolo`
Starts the perception node that detects pedestrians using YOLOv8 and publishes detection data.

### `ros2 run llm_navigation follow_person`
Starts the control node that listens to the detection data and publishes `/cmd_vel` commands to follow the detected person.

## Expected Result

- The robot should detect a person in front of the RGB camera.
- The perception node should publish the target position and depth.
- The follower node should move the robot forward or backward to maintain the target distance.
- The robot should rotate left or right to keep the person near the center of the image.

## Before Running

Make sure:

- The ROS 2 workspace is built successfully.
- The YOLOv8 model file exists at:

```text
<package_root>/models/best.pt
```

- The camera topics are available:

```text
/camera/image_raw
/camera/depth/image_raw
```

- The control topic `/cmd_vel` is connected to the robot base controller.

## Short Description of the Code

### 1) `person_detection_yolo` node

This node performs RGB-D based person detection.

#### Main idea
- Reads RGB image and depth image together using `message_filters`.
- Runs YOLOv8 on the RGB frame.
- Filters detections to keep only pedestrians.
- Extracts the bounding box center and gets the depth value from the depth image at that point.
- Publishes the detection result as a JSON string on `/vision/detections`.
- Optionally shows a GUI window with annotated detections.

#### Important output fields
The published JSON contains:

- `class_name`
- `confidence`
- `bbox_center`
- `image_center`
- `image_width`
- `depth_m`

These fields are used later by the follower node to compute velocity commands.

#### Notes
- The node uses YOLOv8 from the `ultralytics` package.
- It expects the trained weights file `best.pt`.
- The model was trained on Google Colab.
- The dataset source referenced in the code is:

```text
rf.workspace("detection-ceyyf").project("widerperson-7kxya")
```

This indicates the dataset/project connection used for training and exporting the model.

### 2) `follow_person` node

This node converts detection data into robot motion.

#### Main idea
- Subscribes to `/vision/detections`.
- Parses the JSON message.
- Uses the detected person’s depth to calculate forward/backward motion.
- Uses the person’s horizontal position in the image to calculate angular correction.
- Publishes a `Twist` message on `/cmd_vel`.

#### Control logic

**Linear control**
- If the person is farther than the target distance, the robot moves forward.
- If the person is too close, the robot moves backward.
- A deadzone is used so the robot does not keep oscillating near the target distance.

**Angular control**
- If the person is left of the image center, the robot turns left.
- If the person is right of the image center, the robot turns right.
- A deadzone is used to avoid constant small corrections.

**Recovery behavior**
- If no detection arrives for a few seconds, the robot starts spinning in place.
- This helps the system keep searching for the person.

## Data Flow Between Nodes

```text
RGB + Depth Camera
        |
        v
person_detection_yolo
        |
        |  publishes JSON on /vision/detections
        v
follow_person
        |
        |  publishes Twist on /cmd_vel
        v
Robot motion in simulation
```

## YOLOv8 Training Note

The detection model was trained using YOLOv8 in Google Colab.

### Training summary
- Dataset: WiderPerson-based pedestrian dataset
- Training platform: Google Colab
- Model output: `best.pt`
- Use case: pedestrian detection for person following

### Why YOLOv8 was used
- Fast inference
- Good real-time performance
- Easy integration with Python and ROS 2
- Reliable bounding box output for control-based following

## Code Explanation in Simple Words

### `person_detection_yolo`
This code looks at the camera image, finds a person, and measures how far the person is using depth data. Then it sends this information to another node.

### `follow_person`
This code reads the detected person location and tells the robot how to move. It tries to keep the person in the middle of the camera view and at a fixed distance.

## Output Topics

### Published by perception node
- `/vision/detections`

### Published by follower node
- `/cmd_vel`

## Common Checks if It Does Not Work

- Confirm `best.pt` is in the correct model folder.
- Confirm the camera topic names match the code.
- Confirm `/cmd_vel` is not blocked by another node.
- Confirm the depth image and RGB image are synchronized.
- Confirm the robot base controller is active in Gazebo.

## Final Notes

This project uses a simple closed-loop person following pipeline:

1. detect person,
2. read depth,
3. compute control,
4. move robot.

It is easy to extend later with tracking, smoothing, or stronger safety rules.
