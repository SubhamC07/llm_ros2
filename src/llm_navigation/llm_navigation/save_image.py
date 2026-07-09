#!/usr/bin/env python3

import cv2
import os
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import message_filters
from ultralytics import YOLO

class RgbdYoloPerceptionNode(Node):
    def __init__(self):
        super().__init__('rgbd_yolo_perception_node')
        self.bridge = CvBridge()
        
        # Folder setup for screenshots
        self.save_path = "captured_targets"
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)
            
        self.model = YOLO('yolov8n.pt') # Lightweight model
        self.target_captured = False # Flag taaki baar baar photo na khiche

        # Subscribers
        self.rgb_sub = message_filters.Subscriber(self, Image, '/camera/image_raw')
        self.depth_sub = message_filters.Subscriber(self, Image, '/camera/depth/image_raw')
        self.ts = message_filters.ApproximateTimeSynchronizer([self.rgb_sub, self.depth_sub], 10, 0.1)
        self.ts.registerCallback(self.sync_callback)

    def sync_callback(self, rgb_msg, depth_msg):
        rgb_frame = self.bridge.imgmsg_to_cv2(rgb_msg, 'bgr8')
        results = self.model(rgb_frame, classes=[0], verbose=False) # class 0 = person

        if len(results[0].boxes) > 0:
            # 1. Screenshot Logic (Sirf ek baar capture karega)
            if not self.target_captured:
                timestamp = int(time.time())
                cv2.imwrite(f"{self.save_path}/target_{timestamp}.jpg", rgb_frame)
                self.get_logger().info(f"Target found! Screenshot saved: target_{timestamp}.jpg")
                self.target_captured = True
            
            # 2. Yahan apna detection JSON publish kar de (jo hum pehle kar rahe the)
            # ... (Publishing logic)
        else:
            self.target_captured = False # Reset jab insaan gayab ho jaye

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(RgbdYoloPerceptionNode())
    rclpy.shutdown()