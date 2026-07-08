#!/usr/bin/env python3
import math
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String, Bool


class nav2_goal(Node):
    def __init__(self):
        super().__init__('nav2_goal')

        self.subscription = self.create_subscription(
            String,
            '/goal_given',
            self.goal_callback,
            10
        )

        self.open_pub = self.create_publisher(Bool, '/open_to_goal', 10)

        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.goal_active = False

        self.publish_open_state(True)
        self.get_logger().info("Subscribed to /goal_given. Waiting for goals...")

    def publish_open_state(self, state: bool):
        msg = Bool()
        msg.data = state
        self.open_pub.publish(msg)
        self.get_logger().info(f"/open_to_goal -> {state}")

    def yaw_to_quaternion(self, yaw):
        qx = 0.0
        qy = 0.0
        qz = math.sin(yaw / 2.0)
        qw = math.cos(yaw / 2.0)
        return qx, qy, qz, qw

    def goal_callback(self, msg):
        if self.goal_active:
            self.get_logger().warn("Ignoring new goal because a Nav2 goal is already active.")
            return

        self.get_logger().info(f"Received goal request: '{msg.data}'")

        try:
            clean_string = msg.data.replace(" ", "")
            data_dict = dict(item.split(":") for item in clean_string.split(","))

            target_x = float(data_dict['x'])
            target_y = float(data_dict['y'])
            target_yaw = float(data_dict['yaw'])
            target_frame = str(data_dict['frame_id'])

        except (ValueError, KeyError, IndexError) as e:
            self.get_logger().error(
                f"Failed to parse the string message. Make sure the format is exact. Error: {e}"
            )
            return

        if not self.nav_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error("NavigateToPose action server is not available.")
            return

        goal_msg = NavigateToPose.Goal()

        pose = PoseStamped()
        pose.header.frame_id = target_frame
        pose.header.stamp = self.get_clock().now().to_msg()

        pose.pose.position.x = target_x
        pose.pose.position.y = target_y
        pose.pose.position.z = 0.0

        qx, qy, qz, qw = self.yaw_to_quaternion(target_yaw)
        pose.pose.orientation.x = qx
        pose.pose.orientation.y = qy
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw

        goal_msg.pose = pose

        self.goal_active = True
        self.publish_open_state(False)

        self.get_logger().info(
            f"Sending Nav2 goal: X:{target_x}, Y:{target_y}, Yaw:{target_yaw}, Frame:{target_frame}"
        )

        self.send_goal_future = self.nav_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        self.send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        try:
            goal_handle = future.result()
        except Exception as e:
            self.get_logger().error(f"Goal response failed: {e}")
            self.goal_active = False
            self.publish_open_state(True)
            return

        if not goal_handle.accepted:
            self.get_logger().warn('Goal rejected by Nav2.')
            self.goal_active = False
            self.publish_open_state(True)
            return

        self.get_logger().info('Goal accepted by Nav2. Navigating...')
        self.get_result_future = goal_handle.get_result_async()
        self.get_result_future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback_msg):
        # Optional: log distance_remaining if you want.
        pass

    def get_result_callback(self, future):
        try:
            result = future.result()
            status = result.status
        except Exception as e:
            self.get_logger().error(f"Navigation result error: {e}")
            self.goal_active = False
            self.publish_open_state(True)
            return

        self.get_logger().info(f'Navigation finished with status code: {status}')

        self.goal_active = False
        self.publish_open_state(True)


def main(args=None):
    rclpy.init(args=args)
    node = nav2_goal()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down node.")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()