import cv2
import numpy as np
from ultralytics import YOLO
import time
import os
import sys
import json
from datetime import datetime
from pathlib import Path

class RealtimeYOLOv8Detector:
    def __init__(self, model_path='best.pt', capture_interval=2, 
                 threshold_defect=0.25, threshold_stitches=0.30, threshold_top=0.35,
                 nms_iou=0.45, calibration_file='calibration.json'):
        """
        Initialize the real-time YOLOv8 detector with distance measurement
        
        Args:
            model_path: Path to the YOLOv8 model file
            capture_interval: Time interval between captures in seconds
            threshold_defect: Confidence threshold for defect_stitches class
            threshold_stitches: Confidence threshold for stitches class
            threshold_top: Confidence threshold for top class
            nms_iou: IoU threshold for Non-Maximum Suppression
            calibration_file: Path to calibration JSON file
        """
        # Load YOLOv8 model
        print(f"Loading model from {model_path}...")
        self.model = YOLO(model_path)
        
        # Load calibration data
        self.load_calibration(calibration_file)
        
        # Set capture interval
        self.capture_interval = capture_interval
        
        # Set NMS IoU threshold
        self.nms_iou = nms_iou
        
        # Create output directories
        self.setup_directories()
        
        # Class names
        self.class_names = ['dfct', 's', 'top']
        
        # Confidence thresholds for each class
        self.thresholds = {
            'dfct': threshold_defect,
            's': threshold_stitches,
            'top': threshold_top
        }
        
        print(f"\nClass-specific confidence thresholds:")
        print(f"  - dfct: {threshold_defect}")
        print(f"  - s: {threshold_stitches}")
        print(f"  - top: {threshold_top}")
        print(f"\nNMS IoU threshold: {nms_iou}")
        
        # Colors for different classes (BGR format)
        self.colors = {
            'dfct': (0, 0, 255),    # Red
            's': (0, 255, 0),            # Green
            'top': (255, 0, 0)                  # Blue
        }
        
    def load_calibration(self, calibration_file):
        """Load calibration data from JSON file"""
        try:
            if os.path.exists(calibration_file):
                with open(calibration_file, 'r') as f:
                    self.calibration = json.load(f)
                self.pixels_per_mm = self.calibration['pixels_per_mm']
                self.mm_per_pixel = self.calibration.get('mm_per_pixel') or (1.0 / self.pixels_per_mm)
                print(f"\nCalibration loaded from {calibration_file}:")
                print(f"  - mm_per_pixel: {self.mm_per_pixel}")
                print(f"  - pixels_per_mm: {self.pixels_per_mm}")
            else:
                print(f"\nWarning: Calibration file '{calibration_file}' not found!")
                print("Using default calibration (no conversion)")
                self.mm_per_pixel = 1.0
                self.pixels_per_mm = 1.0
                self.calibration = None
        except Exception as e:
            print(f"Error loading calibration: {e}")
            self.mm_per_pixel = 1.0
            self.pixels_per_mm = 1.0
            self.calibration = None
        
    def setup_directories(self):
        """Create directories for saving images"""
        # Use fixed directory names
        self.captured_dir = 'captured_images'
        self.results_dir = 'detection_results'
        
        os.makedirs(self.captured_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        
        print(f"Output directories:")
        print(f"  - Captured images: {self.captured_dir}")
        print(f"  - Detection results: {self.results_dir}")
    
    def fit_line_to_top_edge(self, top_edge_points):
        """
        Fit a line to the top edge points using least squares
        
        Args:
            top_edge_points: Array of (x, y) points
            
        Returns:
            Tuple (a, b, c) where ax + by + c = 0, or None if fitting fails
        """
        if len(top_edge_points) < 2:
            return None
        
        points = np.array(top_edge_points, dtype=np.float32)
        
        # Use cv2.fitLine for robust line fitting
        [vx, vy, x, y] = cv2.fitLine(points, cv2.DIST_L2, 0, 0.01, 0.01)
        
        # Convert to line equation: ax + by + c = 0
        a = -vy[0]
        b = vx[0]
        c = -(a * x[0] + b * y[0])
        
        return (a, b, c)
    
    def perpendicular_distance_to_line(self, point, line_params):
        """
        Calculate perpendicular distance from point to line
        
        Args:
            point: (x, y) coordinates
            line_params: (a, b, c) where ax + by + c = 0
            
        Returns:
            Tuple (distance_pixels, distance_mm)
        """
        x0, y0 = point
        a, b, c = line_params
        
        # Distance formula: |ax0 + by0 + c| / sqrt(a^2 + b^2)
        distance_pixels = abs(a * x0 + b * y0 + c) / np.sqrt(a**2 + b**2)
        distance_mm = distance_pixels * self.mm_per_pixel
        
        return distance_pixels, distance_mm
    
    def get_perpendicular_foot(self, point, line_params):
        """
        Get the foot of perpendicular from point to line
        
        Args:
            point: (x, y) coordinates
            line_params: (a, b, c) where ax + by + c = 0
            
        Returns:
            (x_foot, y_foot) coordinates
        """
        x0, y0 = point
        a, b, c = line_params
        
        # Foot of perpendicular formula
        denominator = a**2 + b**2
        x_foot = (b * (b * x0 - a * y0) - a * c) / denominator
        y_foot = (a * (-b * x0 + a * y0) - b * c) / denominator
        
        return (int(x_foot), int(y_foot))
        
    def draw_detection(self, image, results):
        """
        Draw bounding boxes, masks, center points, top edge lines, and distance measurements
        
        Args:
            image: Input image
            results: YOLO detection results
            
        Returns:
            Tuple of (annotated image, defect_count, stitch_count)
        """
        annotated_image = image.copy()
        defect_count = 0
        stitch_count = 0
        
        if results[0].masks is None:
            return annotated_image, defect_count, stitch_count, 0.0
        
        # Get masks, boxes, and classes
        masks = results[0].masks.data.cpu().numpy()
        boxes = results[0].boxes.xyxy.cpu().numpy()
        classes = results[0].boxes.cls.cpu().numpy()
        confidences = results[0].boxes.conf.cpu().numpy()
        
        # Get original image dimensions
        h, w = image.shape[:2]
        
        # First pass: collect top edge points and stitch centers
        top_edge_points = []
        stitch_centers = []
        
        for i, (mask, box, cls, conf) in enumerate(zip(masks, boxes, classes, confidences)):
            cls_idx = int(cls)
            class_name = self.class_names[cls_idx]
            
            # Apply class-specific threshold filter
            if conf < self.thresholds[class_name]:
                continue
            
            # Resize mask to image dimensions
            mask_resized = cv2.resize(mask, (w, h))
            mask_binary = (mask_resized > 0.5).astype(np.uint8)
            
            # Collect top edge points
            if class_name == 'top':
                mask_points = np.column_stack(np.where(mask_binary == 1))
                
                if len(mask_points) > 0:
                    # Get top edge points (minimum y-coordinates for each x)
                    for x in range(w):
                        y_coords = mask_points[mask_points[:, 1] == x][:, 0]
                        if len(y_coords) > 0:
                            top_y = np.min(y_coords)
                            top_edge_points.append((x, top_y))
            
            # Collect stitch centers
            if class_name in ['s', 'dfct']:
                x1, y1, x2, y2 = map(int, box)
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                stitch_centers.append((center_x, center_y, class_name))
        
        # Fit line to top edge if points exist
        top_line_params = None
        if len(top_edge_points) > 1:
            top_line_params = self.fit_line_to_top_edge(top_edge_points)
        
        # Second pass: draw everything
        all_distances_mm = []  # Collect all stitch-to-top distances for averaging
        for i, (mask, box, cls, conf) in enumerate(zip(masks, boxes, classes, confidences)):
            cls_idx = int(cls)
            class_name = self.class_names[cls_idx]
            color = self.colors[class_name]
            
            # Apply class-specific threshold filter
            if conf < self.thresholds[class_name]:
                continue  # Skip this detection if below threshold
            
            # Count defects and stitches
            if class_name == 'dfct':
                defect_count += 1
            elif class_name == 's':
                stitch_count += 1
            
            # Resize mask to image dimensions
            mask_resized = cv2.resize(mask, (w, h))
            mask_binary = (mask_resized > 0.5).astype(np.uint8)
            
            # Draw mask overlay (semi-transparent)
            colored_mask = np.zeros_like(image)
            colored_mask[mask_binary == 1] = color
            annotated_image = cv2.addWeighted(annotated_image, 1, colored_mask, 0.4, 0)
            
            # Draw bounding box
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(annotated_image, (x1, y1), (x2, y2), color, 2)
            
            # Add label with confidence (DISABLED)
            # label = f"{class_name}: {conf:.2f}"
            # label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            # cv2.rectangle(annotated_image, (x1, y1 - label_size[1] - 10), 
            #              (x1 + label_size[0], y1), color, -1)
            # cv2.putText(annotated_image, label, (x1, y1 - 5), 
            #            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            # Mark center point for 'stitches' and 'defect_stitches' classes
            if class_name in ['s', 'dfct']:
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                
                # Draw center point
                cv2.circle(annotated_image, (center_x, center_y), 5, (255, 255, 0), -1)
                cv2.circle(annotated_image, (center_x, center_y), 7, (0, 0, 0), 2)
                
                # Add center point coordinates (DISABLED)
                # coord_text = f"({center_x}, {center_y})"
                # cv2.putText(annotated_image, coord_text, (center_x + 10, center_y - 10),
                #            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
                
                # Calculate perpendicular distance to top edge line and collect for grouping
                if top_line_params is not None:
                    dist_pixels, dist_mm = self.perpendicular_distance_to_line(
                        (center_x, center_y), top_line_params
                    )
                    all_distances_mm.append((center_x, center_y, dist_mm))
            
            # Draw top edge line for 'top' class
            if class_name == 'top':
                # Find the top edge of the mask
                mask_points = np.column_stack(np.where(mask_binary == 1))
                
                if len(mask_points) > 0:
                    # Get top edge points (minimum y-coordinates for each x)
                    edge_points = []
                    for x in range(w):
                        y_coords = mask_points[mask_points[:, 1] == x][:, 0]
                        if len(y_coords) > 0:
                            top_y = np.min(y_coords)
                            edge_points.append((x, top_y))
                    
                    # Draw the top edge line in YELLOW
                    if len(edge_points) > 1:
                        edge_points_array = np.array(edge_points, dtype=np.int32)
                        cv2.polylines(annotated_image, [edge_points_array], False, 
                                    (0, 255, 255), 3)  # Yellow line
                        
                        # Add label for top edge
                        cv2.putText(annotated_image, "Top Edge", 
                                  (edge_points[0][0], edge_points[0][1] - 10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        
        # After loop: compute single average distance (top-edge to stitches)
        avg_dist_mm = 0.0
        if all_distances_mm:
            avg_dist_mm = sum(d for _, _, d in all_distances_mm) / len(all_distances_mm)

        return annotated_image, defect_count, stitch_count, avg_dist_mm
    
    def run_webcam(self, camera_index=0):
        """
        Run real-time detection with webcam
        
        Args:
            camera_index: Camera index (0 for default camera)
        """
        # Open webcam
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            print(f"Error: Could not open camera {camera_index}")
            return
        
        # Get camera properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"\nCamera initialized:")
        print(f"  - Resolution: {width}x{height}")
        print(f"  - FPS: {fps}")
        print(f"\nControls:")
        print("  - Press 'q' to quit")
        print("  - Press 'c' to manually capture frame")
        print(f"  - Automatic capture every {self.capture_interval} seconds")
        
        last_capture_time = time.time()
        frame_count = 0
        current_defect_count = 0
        current_stitch_count = 0
        current_avg_dist = 0.0
        
        # Create named window in fullscreen mode
        window_name = 'YOLOv8 Real-time Detection'
        cv2.namedWindow(window_name, cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        
        try:
            while True:
                ret, frame = cap.read()
                
                if not ret:
                    print("Error: Failed to capture frame")
                    break
                
                current_time = time.time()
                
                # Always process frame with detection (for display)
                results = self.model(frame, conf=0.1, iou=self.nms_iou)
                display_frame, current_defect_count, current_stitch_count, current_avg_dist = self.draw_detection(frame, results)
                
                # Check if it's time to save captured images
                if current_time - last_capture_time >= self.capture_interval:
                    frame_count += 1
                    print(f"\nSaving frame {frame_count}...")
                    
                    # Save images
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    
                    # Save captured image
                    captured_path = os.path.join(self.captured_dir, f'captured_{timestamp}.jpg')
                    cv2.imwrite(captured_path, frame)
                    
                    # Save result image
                    result_path = os.path.join(self.results_dir, f'result_{timestamp}.jpg')
                    cv2.imwrite(result_path, display_frame)
                    
                    # Print detection summary
                    if results[0].masks is not None:
                        # Filter by class-specific thresholds for accurate count
                        classes = results[0].boxes.cls.cpu().numpy()
                        confidences = results[0].boxes.conf.cpu().numpy()
                        
                        filtered_detections = []
                        for cls, conf in zip(classes, confidences):
                            cls_idx = int(cls)
                            class_name = self.class_names[cls_idx]
                            if conf >= self.thresholds[class_name]:
                                filtered_detections.append(cls_idx)
                        
                        if len(filtered_detections) > 0:
                            print(f"\nFrame {frame_count} - Detections: {len(filtered_detections)}")
                            
                            for cls_idx in range(len(self.class_names)):
                                count = filtered_detections.count(cls_idx)
                                if count > 0:
                                    print(f"  - {self.class_names[cls_idx]}: {count}")
                    
                    last_capture_time = current_time
                
                # Get frame dimensions
                h, w = display_frame.shape[:2]
                
                # Create semi-transparent overlay for count display (top right)
                overlay = display_frame.copy()
                
                # Calculate text sizes for proper background sizing
                defect_text = f"Defects: {current_defect_count}"
                stitch_text = f"Stitches: {current_stitch_count}"
                avg_text    = f"Avg Dist: {current_avg_dist:.2f} mm" if current_avg_dist > 0 else "Avg Dist: --"
                
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.8
                font_thickness = 2
                
                (defect_w, defect_h), _ = cv2.getTextSize(defect_text, font, font_scale, font_thickness)
                (stitch_w, stitch_h), _ = cv2.getTextSize(stitch_text, font, font_scale, font_thickness)
                (avg_w,    avg_h),    _ = cv2.getTextSize(avg_text,    font, font_scale, font_thickness)
                
                # Determine background dimensions
                max_text_width = max(defect_w, stitch_w, avg_w)
                total_height = defect_h + stitch_h + avg_h + 45  # extra padding for 3 lines
                
                # Draw semi-transparent background (top right corner)
                bg_x1 = w - max_text_width - 30
                bg_y1 = 10
                bg_x2 = w - 10
                bg_y2 = bg_y1 + total_height
                
                cv2.rectangle(overlay, (bg_x1, bg_y1), (bg_x2, bg_y2), (0, 0, 0), -1)
                display_frame = cv2.addWeighted(display_frame, 0.7, overlay, 0.3, 0)
                
                # Draw count text (top right)
                text_x = w - max_text_width - 20
                defect_y = bg_y1 + defect_h + 10
                stitch_y = defect_y + stitch_h + 10
                
                # Defect count in red
                cv2.putText(display_frame, defect_text, (text_x, defect_y),
                           font, font_scale, (0, 0, 255), font_thickness)
                
                # Stitch count in green
                cv2.putText(display_frame, stitch_text, (text_x, stitch_y),
                           font, font_scale, (0, 255, 0), font_thickness)

                # Average distance in cyan, below stitch count
                avg_y = stitch_y + stitch_h + 10
                cv2.putText(display_frame, avg_text, (text_x, avg_y),
                           font, font_scale, (0, 255, 255), font_thickness)
                
                # Add FPS and status info (bottom left)
                time_until_next = self.capture_interval - (current_time - last_capture_time)
                status_text = f"Next capture in: {time_until_next:.1f}s | Frame: {frame_count}"
                cv2.putText(display_frame, status_text, (10, h - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Display the frame
                cv2.imshow(window_name, display_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    print("\nQuitting...")
                    break
                elif key == ord('c'):
                    # Manual capture
                    frame_count += 1
                    print(f"\nManual capture - Frame {frame_count}...")
                    
                    # Save images
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    
                    # Save captured image
                    captured_path = os.path.join(self.captured_dir, f'captured_{timestamp}.jpg')
                    cv2.imwrite(captured_path, frame)
                    
                    # Save result image
                    result_path = os.path.join(self.results_dir, f'result_{timestamp}.jpg')
                    cv2.imwrite(result_path, display_frame)
                    
                    last_capture_time = current_time
        
        finally:
            # Cleanup
            cap.release()
            cv2.destroyAllWindows()
            print(f"\nSession complete. Results saved to:")
            print(f"  - Captured images: {self.captured_dir}")
            print(f"  - Detection results: {self.results_dir}")
    


def main():
    """Main function to run the detector"""
    
    # Configuration
    MODEL_PATH = 'stitches.pt'      # Path to your YOLOv8 model
    CALIBRATION_FILE = 'calibration.json'  # Path to calibration file
    CAPTURE_INTERVAL = 2           # Seconds between captures
    CAMERA_INDEX = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    
    # Class-specific confidence thresholds
    THRESHOLD_DEFECT_STITCHES = 0.45  # Threshold for defect_stitches class
    THRESHOLD_STITCHES = 0.40         # Threshold for stitches class
    THRESHOLD_TOP = 0.35              # Threshold for top class
    
    # NMS (Non-Maximum Suppression) IoU threshold
    NMS_IOU_THRESHOLD = 0.45      # Higher = more overlap allowed, Lower = stricter separation
    
    # Check if model exists
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model file '{MODEL_PATH}' not found!")
        print("Please ensure your best.pt file is in the current directory.")
        return
    
    # Initialize detector
    detector = RealtimeYOLOv8Detector(
        model_path=MODEL_PATH,
        capture_interval=CAPTURE_INTERVAL,
        threshold_defect=THRESHOLD_DEFECT_STITCHES,
        threshold_stitches=THRESHOLD_STITCHES,
        threshold_top=THRESHOLD_TOP,
        nms_iou=NMS_IOU_THRESHOLD,
        calibration_file=CALIBRATION_FILE
    )
    
    # Run with webcam
    print("\nStarting webcam detection...")
    detector.run_webcam(camera_index=CAMERA_INDEX)


if __name__ == "__main__":
    main()