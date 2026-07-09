#!/usr/bin/env python3

import json
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist

class PersonFollowerNode(Node):
    def __init__(self):
        super().__init__('person_follower_node')
        
        # --- Parameters ---
        self.declare_parameter('target_distance', 1.5)      # Target distance in meters
        self.declare_parameter('max_linear_speed', 0.5)     # Max forward/backward speed (m/s)
        self.declare_parameter('max_angular_speed', 1.0)    # Max rotation speed (rad/s)
        self.declare_parameter('kp_linear', 0.6)            # Proportional gain for distance
        self.declare_parameter('kp_angular', 2.0)           # Proportional gain for rotation
        self.declare_parameter('timeout_sec', 1.0)          # Stop if no detection for 1s

        self.target_dist = self.get_parameter('target_distance').value
        self.max_v = self.get_parameter('max_linear_speed').value
        self.max_w = self.get_parameter('max_angular_speed').value
        self.kp_v = self.get_parameter('kp_linear').value
        self.kp_w = self.get_parameter('kp_angular').value
        self.timeout = self.get_parameter('timeout_sec').value

        # --- Publishers & Subscribers ---
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.det_sub = self.create_subscription(String, '/vision/detections', self.detection_callback, 10)
        
        # --- Safety Timer ---
        self.last_detection_time = time.time()
        self.timer = self.create_timer(0.1, self.safety_loop) # Check safety every 100ms
        
        self.get_logger().info("Person Follower Node Started. Ready to follow the target!")

    def detection_callback(self, msg: String):
        # Update timestamp on new detection
        self.last_detection_time = time.time()
        
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().error("Invalid JSON received!")
            return

        depth_m = data.get("depth_m", -1.0)
        bbox_x = data.get("bbox_center", {}).get("x", 0.0)
        img_center_x = data.get("image_center", {}).get("x", 0.0)
        img_width = data.get("image_width", 1.0)

        twist = Twist()

        # --- 1. Linear Velocity (Forward/Backward Control) ---
        if depth_m > 0.1:  # Valid depth check (ignore -1.0 or extreme noise)
            error_dist = depth_m - self.target_dist
            linear_vel = self.kp_v * error_dist
            
            # Clip speed to max limits
            twist.linear.x = max(-self.max_v, min(self.max_v, linear_vel))
            
            # Deadzone: don't jitter if within 15cm of target distance
            if abs(error_dist) < 0.15:
                twist.linear.x = 0.0
        else:
            twist.linear.x = 0.0

        # --- 2. Angular Velocity (Left/Right Rotation Control) ---
        if img_width > 0:
            # Normalize pixel error between -1 and 1
            error_yaw = (img_center_x - bbox_x) / (img_width / 2.0)
            angular_vel = self.kp_w * error_yaw
            
            # Clip speed
            twist.angular.z = max(-self.max_w, min(self.max_w, angular_vel))

            # Deadzone: don't jitter if almost centered
            if abs(error_yaw) < 0.1:
                twist.angular.z = 0.0

        self.cmd_pub.publish(twist)

    def safety_loop(self):
        # Stop robot immediately if detection stream stops
        if time.time() - self.last_detection_time > self.timeout:
            stop_msg = Twist()
            self.cmd_pub.publish(stop_msg)


def main(args=None):
    rclpy.init(args=args)
    node = PersonFollowerNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Stop the robot before shutting down
        stop_msg = Twist()
        node.cmd_pub.publish(stop_msg)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()