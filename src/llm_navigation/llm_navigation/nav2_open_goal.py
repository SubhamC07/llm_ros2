import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose

from rclpy.parameter import Parameter

class ContinuousGoalUpdater(Node):
    def __init__(self):
        super().__init__('nav2_continuous_goal')

        self.set_parameters([
            Parameter("use_sim_time", Parameter.Type.BOOL, True)
        ])

        # Create an Action Client for the Nav2 navigate_to_pose server
        self.nav_to_pose_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # Subscribe to your custom topic
        self.goal_subscription = self.create_subscription(
            PoseStamped,
            '/goal_given',
            self.goal_callback,
            10
        )

        # Wait for the Nav2 action server to come online
        self.get_logger().info('Waiting for "navigate_to_pose" action server...')
        self.nav_to_pose_client.wait_for_server()
        self.get_logger().info('Action server available! Ready to receive goals on /goal_given.')

    def goal_callback(self, msg: PoseStamped):
        """
        Triggered every time a new PoseStamped message is published to /goal_given.
        """
        self.get_logger().info(
            f'Received new goal -> X: {msg.pose.position.x:.2f}, Y: {msg.pose.position.y:.2f}'
        )

        # Ensure the frame_id is set (usually 'map')
        if not msg.header.frame_id:
            msg.header.frame_id = 'map'
            msg.header.stamp = self.get_clock().now().to_msg()

        # Construct the Action Goal message
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = msg

        # Send the goal asynchronously. Nav2 will automatically preempt any existing goal.
        self.get_logger().info('Sending new goal to Nav2...')
        send_goal_future = self.nav_to_pose_client.send_goal_async(goal_msg)
        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        """
        Callback to check if Nav2 accepted or rejected the goal.
        """
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('Goal was rejected by Nav2.')
            return

        self.get_logger().info('Goal accepted! Robot is navigating to the new pose.')

def main(args=None):
    rclpy.init(args=args)
    node = ContinuousGoalUpdater()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Keyboard interrupt received. Shutting down...')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()