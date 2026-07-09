#!/usr/bin/env python3

import json
import os

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import message_filters

from ultralytics import YOLO

class RgbdYoloPerceptionNode(Node):
    CLASS_NAMES = {
        0: 'crowd',
        1: 'ignore_regions',
        2: 'partially_visible_persons',
        3: 'pedestrians',
        4: 'riders',
    }

    def __init__(self):
        super().__init__('rgbd_yolo_perception_node')

        self.bridge = CvBridge()

        self.declare_parameter('show_gui', True)
        self.show_gui = self.get_parameter('show_gui').get_parameter_value().bool_value

        self.gui_window_name = "RGB-D YOLO Pedestrian Detections"
        if self.show_gui:
            cv2.namedWindow(self.gui_window_name, cv2.WINDOW_NORMAL)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        model_path = os.path.join(parent_dir, 'models', 'best.pt')

        self.get_logger().info(f"Loading YOLO model from: {model_path}")
        try:
            self.model = YOLO(model_path)
            self.get_logger().info("YOLO model loaded successfully!")
        except Exception as e:
            self.get_logger().error(f"Failed to load YOLO model: {e}")
            raise e

        self.rgb_sub = message_filters.Subscriber(self, Image, '/camera/image_raw')
        self.depth_sub = message_filters.Subscriber(self, Image, '/camera/depth/image_raw')

        self.ts = message_filters.ApproximateTimeSynchronizer(
            [self.rgb_sub, self.depth_sub],
            queue_size=10,
            slop=0.1
        )
        self.ts.registerCallback(self.sync_callback)

        self.detection_pub = self.create_publisher(String, '/vision/detections', 10)
        self.get_logger().info(f"RGB-D YOLO Node started. show_gui={self.show_gui}")

    def _get_detection_label(self, class_id):
        if class_id in self.CLASS_NAMES:
            return self.CLASS_NAMES[class_id]
        return str(class_id)

    def sync_callback(self, rgb_msg: Image, depth_msg: Image):
        try:
            rgb_frame = self.bridge.imgmsg_to_cv2(rgb_msg, desired_encoding='bgr8')
            depth_frame = self.bridge.imgmsg_to_cv2(depth_msg, desired_encoding='passthrough')
        except Exception as e:
            self.get_logger().error(f"cv_bridge conversion failed: {e}")
            return

        results = self.model(rgb_frame, classes=[3], verbose=False)
        annotated_frame = rgb_frame.copy()

        if len(results) > 0 and len(results[0].boxes) > 0:
            boxes = results[0].boxes
            annotated_frame = results[0].plot()

            selected_box = None
            selected_class_name = None
            selected_confidence = None

            for box in boxes:
                confidence = float(box.conf[0]) if len(box.conf) > 0 else 0.0
                class_id = int(box.cls[0]) if len(box.cls) > 0 else -1
                class_name = self._get_detection_label(class_id)

                if class_name != 'pedestrians':
                    continue

                selected_box = box
                selected_class_name = class_name
                selected_confidence = confidence
                break

            if selected_box is None:
                if self.show_gui:
                    cv2.putText(annotated_frame, "No pedestrian detections", (20, 40), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            else:
                x1, y1, x2, y2 = selected_box.xyxy[0].tolist()

                center_x_int = int((x1 + x2) / 2.0)
                center_y_int = int((y1 + y2) / 2.0)

                h, w = depth_frame.shape[:2]
                center_x_int = max(0, min(center_x_int, w - 1))
                center_y_int = max(0, min(center_y_int, h - 1))

                depth_val = depth_frame[center_y_int, center_x_int]

                if depth_frame.dtype == np.uint16:
                    depth_m = float(depth_val) / 1000.0
                else:
                    depth_m = float(depth_val)

                if depth_m <= 0.0 or np.isnan(depth_m):
                    depth_m = -1.0

                # Added image properties to the payload for lateral following calculations
                detection_dict = {
                    "class_name": selected_class_name,
                    "confidence": round(selected_confidence, 2),
                    "bbox_center": {"x": float(center_x_int), "y": float(center_y_int)},
                    "image_center": {"x": float(w / 2.0), "y": float(h / 2.0)},
                    "image_width": float(w),
                    "depth_m": round(depth_m, 2)
                }

                out_msg = String()
                out_msg.data = json.dumps(detection_dict)
                self.detection_pub.publish(out_msg)

        else:
            if self.show_gui:
                cv2.putText(annotated_frame, "No detections", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

        if self.show_gui:
            try:
                cv2.imshow(self.gui_window_name, annotated_frame)
                cv2.waitKey(1)
            except Exception as e:
                self.get_logger().warn(f"GUI display failed: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = RgbdYoloPerceptionNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.show_gui:
            cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()