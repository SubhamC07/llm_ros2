#!/usr/bin/env python3

import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

from std_msgs.msg import String


class executor(Node):
    def __init__(self):
        super().__init__("executor")
        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.goal_given = self.create_publisher(String, "/goal_given", 10)

    def send_cmd_vel(self, linear_x: float, angular_z: float, duration: float, publish_rate: float = 10.0):
        twist = Twist()
        twist.linear.x = linear_x
        twist.angular.z = angular_z
        dt = 1.0 / publish_rate
        start = time.time()
        while time.time() - start < duration:
            self.cmd_pub.publish(twist)
            time.sleep(dt)
        self.stop()
    
    def send_nav_goal(self, x: float, y: float, yaw: float, frame_id: str = "map"):
        goal_msg = String()
        goal_msg.data = f"x:{x}, y:{y}, yaw:{yaw}, frame_id:{frame_id}" 
        self.goal_given.publish(goal_msg)

    def stop(self):
        self.cmd_pub.publish(Twist())


def main():
    rclpy.init()
    node = executor()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()