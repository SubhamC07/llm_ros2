import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
import math
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String

class nav2_goal(Node):
    def __init__(self):
        super().__init__('nav2_goal')
        self.subscription = self.create_subscription(String, '/goal_given', self.goal_callback, 10)
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.get_logger().info("Subscribed to /goal_given. Waiting for goals...")

    def yaw_to_quaternion(self, yaw):
        qx = 0.0
        qy = 0.0
        qz = math.sin(yaw / 2.0)
        qw = math.cos(yaw / 2.0)
        return qx, qy, qz, qw

    def goal_callback(self, msg):
        self.get_logger().info(f"Received goal request: '{msg.data}'")
        
        try:
            # The incoming string looks like: "x:1.0, y:2.0, yaw:0.0, frame_id:map"
            # 1. Remove all spaces for clean parsing
            clean_string = msg.data.replace(" ", "") 
            
            # 2. Split by commas, then split by colons to create a dictionary
            # Resulting dict: {'x': '1.0', 'y': '2.0', 'yaw': '0.0', 'frame_id': 'map'}
            data_dict = dict(item.split(":") for item in clean_string.split(","))

            # 3. Cast the dictionary values back to floats and strings
            target_x = float(data_dict['x'])
            target_y = float(data_dict['y'])
            target_yaw = float(data_dict['yaw'])
            target_frame = str(data_dict['frame_id'])
            
        except (ValueError, KeyError, IndexError) as e:
            self.get_logger().error(f"Failed to parse the string message. Make sure the format is exact. Error: {e}")
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

        self.get_logger().info(f"Sending Nav2 goal:: X:{target_x}, Y:{target_y}, Yaw:{target_yaw}, Frame:{target_frame}")
        self.send_goal_future = self.nav_client.send_goal_async(goal_msg, feedback_callback=self.feedback_callback)
        self.send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('Goal rejected by Nav2.')
            return

        self.get_logger().info('Goal accepted by Nav2. Navigating...')
        self.get_result_future = goal_handle.get_result_async()
        self.get_result_future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback_msg):
        # Optional: You can log distance remaining here if you want
        pass

    def get_result_callback(self, future):
        status = future.result().status
        self.get_logger().info(f'Navigation finished with status code: {status}')


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