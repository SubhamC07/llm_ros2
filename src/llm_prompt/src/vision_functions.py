import json
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String

class VisionRobotExecutor(Node):
    def __init__(self):
        super().__init__("vision_executor_interface")
        self.cmd_vel_pub = self.create_publisher(Twist, "/cmd_vel", 10)

        # Subscribe to YOLO detections
        self.yolo_sub = self.create_subscription(
            String,
            "/vision/detections",
            self.yolo_callback,
            10
        )

        self.latest_detection = None
        self.current_state = "IDLE"

        # Tuning parameters
        self.image_center_x = 640.0
        self.center_tolerance_px = 30.0
        
        # Tracking State Variables
        self.target_class = None
        self.maintain_distance = 0.0
        self.timeout = 0.0
        self.last_seen_time = 0.0

        # Create a timer for control loop (10Hz -> 0.1s rate_sleep)
        self.control_timer = self.create_timer(0.1, self.control_loop)

    def yolo_callback(self, msg: String):
        try:
            self.latest_detection = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().warn("Failed to parse detection JSON.")
            self.latest_detection = None

    def capture_snapshot(self, target_class: str):
        self.get_logger().info(
            f"[VISION] Snapshot taken of '{target_class}'. Sending to Operator UI..."
        )
        # Insert cv_bridge image save logic here

    def start_following(self, target_class: str, maintain_distance: float, timeout: float):
        """Call this method to initiate tracking state safely."""
        self.target_class = target_class
        self.maintain_distance = maintain_distance
        self.timeout = timeout
        self.current_state = "FOLLOW"
        self.last_seen_time = time.time()
        self.get_logger().info(f"[TRACKING] Initiating follow for '{target_class}'...")

    def control_loop(self):
        """Non-blocking control loop run by the ROS 2 timer."""
        if self.current_state != "FOLLOW":
            return

        # Check for global timeout since the tracking started/last refreshed
        if (time.time() - self.last_seen_time) > self.timeout:
            self.get_logger().warn(
                f"[TRACKING] Timeout reached. Target '{self.target_class}' lost or time expired."
            )
            self.stop()
            return

        if not self.latest_detection:
            self.stop_cmd_vel()
            return

        if self.latest_detection.get("class_name") != self.target_class:
            self.stop_cmd_vel()
            return

        # Target is visible -> refresh the timeout window
        self.last_seen_time = time.time()

        detection = self.latest_detection
        depth_m = float(detection.get("depth_m", -1.0))

        bbox_center = detection.get("bbox_center", {})
        center_x = float(bbox_center.get("x", self.image_center_x))

        # ---- Distance control ----
        dist_error = depth_m - self.maintain_distance
        cmd = Twist()

        # Forward/backward control using depth
        if depth_m > 0.0:
            if dist_error > 0.5:
                cmd.linear.x = 0.2
            elif dist_error < -0.5:
                cmd.linear.x = -0.2
            else:
                cmd.linear.x = 0.0
        else:
            self.get_logger().warn("Invalid depth value in detection.")
            cmd.linear.x = 0.0

        # ---- Heading control using bbox center ----
        pixel_error = center_x - self.image_center_x

        if abs(pixel_error) > self.center_tolerance_px:
            cmd.angular.z = -0.003 * pixel_error
        else:
            cmd.angular.z = 0.0

        # Limit speeds
        cmd.linear.x = max(min(cmd.linear.x, 0.3), -0.3)
        cmd.angular.z = max(min(cmd.angular.z, 0.8), -0.8)

        self.cmd_vel_pub.publish(cmd)

        self.get_logger().info(
            f"[TRACKING] {self.target_class}: depth={depth_m:.2f}m, "
            f"center_x={center_x:.1f}, lin_x={cmd.linear.x:.2f}, ang_z={cmd.angular.z:.2f}"
        )

    def stop_cmd_vel(self):
        """Sends zero velocity to stop movement without breaking out of FOLLOW state loop."""
        self.cmd_vel_pub.publish(Twist())

    def stop(self):
        """Halts the robot entirely and resets state to IDLE."""
        self.get_logger().info("[CONTROL] Halting robot and resetting state.")
        self.cmd_vel_pub.publish(Twist())
        self.current_state = "IDLE"
        self.target_class = None

def main(args=None):
    rclpy.init(args=args)
    node = VisionRobotExecutor()
    
    # Example snippet to trigger tracking on startup for testing:
    # node.start_following(target_class="person", maintain_distance=1.5, timeout=10.0)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()