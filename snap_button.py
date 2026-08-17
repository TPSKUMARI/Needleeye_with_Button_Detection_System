

"""
Ultra-Simple Button Detection System
Three Main Functions:
1. Button Detection & Count - Detect buttons and return count
2. Distance Measurement - Calculate distances (with calibration)
3. YOLO Defect Detection - Detect only YOLO-based defects

Returns: Button Count, Distances, YOLO Defects
No UI, No Style Selection, No Extra Defects
"""

import cv2
import numpy as np
import os
import sys
import json
import math
import time
from datetime import datetime
from ultralytics import YOLO

# ============================================================================
# CONFIGURATION
# ============================================================================
MODEL_PATH = "snap_button_defects.pt"  # YOLO model for buttons and defects
CALIBRATION_FILE = "calibration.json"

# Camera settings
CAMERA_INDEX = int(sys.argv[1]) if len(sys.argv) > 1 else 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# Detection settings - Individual threshold for each class
CLASS_CONFIDENCE = {
    0: 0.6,  # button
    1: 0.5,  # defect1 (bend/round)
    2: 0.95   # defect2 (machine)
}
NMS_IOU_THRESHOLD = 0.45

# Class colors (dark colors for visibility)
CLASS_COLORS = {
    0: (0, 100, 0),      # Dark green for buttons
    1: (139, 0, 0),      # Dark red for defect1
    2: (139, 69, 0)      # Dark orange for defect2
}

# Class names
CLASS_NAMES = {
    0: "Button",
    1: "Bend/Round",
    2: "Machine"
}

# Motion detection
PIXEL_CHANGE_THRESHOLD = 200000
FRAME_DIFF_THRESHOLD = 25
COOLDOWN_SECONDS = 0.3
CAPTURE_DELAY = 0.5

# Output folders
CAPTURED_FOLDER = "captured_images"
DETECTED_FOLDER = "detected_images"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_folders():
    """Create output folders if they don't exist"""
    os.makedirs(CAPTURED_FOLDER, exist_ok=True)
    os.makedirs(DETECTED_FOLDER, exist_ok=True)
    print(f" Folders ready: {CAPTURED_FOLDER}, {DETECTED_FOLDER}")


def load_calibration():
    """Load mm_per_pixel from calibration file"""
    if not os.path.exists(CALIBRATION_FILE):
        print(f"⚠ Warning: {CALIBRATION_FILE} not found - distances will be in pixels")
        return None

    with open(CALIBRATION_FILE, 'r') as f:
        cal = json.load(f)

    mm_per_pixel = cal.get('mm_per_pixel')
    if mm_per_pixel is None:
        pixels_per_mm = cal.get('pixels_per_mm')
        if pixels_per_mm:
            mm_per_pixel = 1.0 / pixels_per_mm
        else:
            print("⚠ Warning: calibration.json has no usable calibration data - distances will be in pixels")
            return None

    print(f" Calibration loaded: {mm_per_pixel:.4f} mm/pixel")
    return mm_per_pixel


def detect_motion(frame1, frame2):
    """Detect motion between two frames"""
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
    gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)
    
    diff = cv2.absdiff(gray1, gray2)
    _, thresh = cv2.threshold(diff, FRAME_DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)
    thresh = cv2.dilate(thresh, None, iterations=2)
    
    changed_pixels = np.sum(thresh == 255)
    return changed_pixels >= PIXEL_CHANGE_THRESHOLD


# ============================================================================
# FUNCTION 1: BUTTON DETECTION & COUNT
# ============================================================================

def detect_circle_in_button(image, bbox):
    """
    Apply edge detection and circle detection within button bounding box
    Returns the center point of detected circle
    """
    x1, y1, x2, y2 = bbox
    
    # Extract button region
    button_roi = image[y1:y2, x1:x2]
    
    if button_roi.size == 0:
        # Return bbox center if ROI is invalid
        return ((x1 + x2) // 2, (y1 + y2) // 2), None
    
    # Convert to grayscale
    gray = cv2.cvtColor(button_roi, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    
    # Detect circles using HoughCircles
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=20,
        param1=50,
        param2=30,
        minRadius=5,
        maxRadius=100
    )
    
    if circles is not None:
        circles = np.uint16(np.around(circles))
        # Get the first (most prominent) circle
        circle = circles[0][0]
        circle_x, circle_y, radius = circle
        
        # Convert to absolute image coordinates
        abs_x = x1 + circle_x
        abs_y = y1 + circle_y
        
        return (abs_x, abs_y), (circle_x, circle_y, radius)
    
    # If no circle detected, return bbox center
    return ((x1 + x2) // 2, (y1 + y2) // 2), None


def detect_buttons(model, image):
    """
    Detect buttons and defects using YOLO model with individual class thresholds
    Then apply edge detection and circle detection to find button centers
    
    Returns:
        button_data: List of dicts with bbox, center, confidence, circle_info
        yolo_defects: List of tuples (class_id, confidence, bbox)
    """
    results = model(
        image,
        conf=min(CLASS_CONFIDENCE.values()),  # Use lowest confidence
        iou=NMS_IOU_THRESHOLD,
        verbose=False
    )
    
    button_data = []
    yolo_defects = []
    
    if len(results) > 0 and results[0].boxes is not None:
        for box in results[0].boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            bbox = box.xyxy[0].cpu().numpy()
            
            # Check individual threshold for each class
            if class_id in CLASS_CONFIDENCE and confidence >= CLASS_CONFIDENCE[class_id]:
                if class_id == 0:  # Button
                    x1, y1, x2, y2 = map(int, bbox)
                    
                    # Apply edge detection and circle detection
                    circle_center, circle_info = detect_circle_in_button(image, [x1, y1, x2, y2])
                    
                    button_data.append({
                        'bbox': [x1, y1, x2, y2],
                        'center': circle_center,  # Use circle center
                        'confidence': confidence,
                        'circle_info': circle_info  # Store circle details
                    })
                
                elif class_id == 1:  # defect1
                    x1, y1, x2, y2 = map(int, bbox)
                    yolo_defects.append({
                        'class': 1,
                        'type': 'Bend/Round',
                        'confidence': confidence,
                        'bbox': [x1, y1, x2, y2]
                    })
                
                elif class_id == 2:  # defect2
                    x1, y1, x2, y2 = map(int, bbox)
                    yolo_defects.append({
                        'class': 2,
                        'type': 'Machine',
                        'confidence': confidence,
                        'bbox': [x1, y1, x2, y2]
                    })
    
    # Sort buttons by x-coordinate (left to right)
    button_data.sort(key=lambda b: b['center'][0])
    
    return button_data, yolo_defects


# ============================================================================
# FUNCTION 2: DISTANCE CALCULATION
# ============================================================================

def calculate_distances(button_data, mm_per_pixel):
    """
    Calculate only adjacent distances between buttons (1-2, 2-3, 3-4, etc.)
    Display only the maximum distance among these pairs
    
    Returns:
        dict with adjacent distances and max distance
    """
    num_buttons = len(button_data)
    
    if num_buttons < 2:
        return {
            'pairs': [],
            'max_distance': 0.0,
            'max_pair': None,
            'unit': 'pixels' if mm_per_pixel is None else 'mm'
        }
    
    centers = [b['center'] for b in button_data]
    unit = 'mm' if mm_per_pixel else 'px'
    scale = mm_per_pixel if mm_per_pixel else 1.0
    
    # Calculate only adjacent pairs (1-2, 2-3, 3-4, etc.)
    distances = []
    for i in range(num_buttons - 1):
        x1, y1 = centers[i]
        x2, y2 = centers[i + 1]
        
        pixel_dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        distance = pixel_dist * scale
        
        distances.append({
            'button1': i + 1,
            'button2': i + 2,
            'distance': distance,
            'unit': unit
        })
    
    # Find max distance and corresponding pair
    max_dist = 0.0
    max_pair = None
    if distances:
        max_entry = max(distances, key=lambda d: d['distance'])
        max_dist = max_entry['distance']
        max_pair = f"B{max_entry['button1']}-B{max_entry['button2']}"
    
    return {
        'pairs': distances,
        'max_distance': max_dist,
        'max_pair': max_pair,
        'unit': unit
    }


# ============================================================================
# FUNCTION 3: DEFECT DETECTION (YOLO ONLY)
# ============================================================================

def check_defects(button_count, yolo_defects):
    """
    Check for defects - YOLO only
    
    Returns:
        dict with defect information
    """
    defects = []
    
    # YOLO defects
    for defect in yolo_defects:
        defect_type = defect['type']
        conf = defect['confidence']
        defects.append(f"{defect_type} defect detected (conf: {conf:.2f})")
    
    return {
        'has_defect': len(defects) > 0,
        'total_defects': len(defects),
        'defects': defects,
        'button_count': button_count,
        'yolo_defects': yolo_defects
    }


# ============================================================================
# VISUALIZATION
# ============================================================================

def draw_results(image, button_data, distances, defect_info):
    """
    Draw detection results on image
    - No bars
    - Results in top right corner
    - Dark colors for class names
    - Black lines for distances
    - Black font for distance text
    - Show detected circles and center points
    """
    img = image.copy()
    h, w = img.shape[:2]
    
    # Draw buttons with dark colored boxes and labels
    for idx, button in enumerate(button_data):
        x1, y1, x2, y2 = button['bbox']
        conf = button['confidence']
        center = button['center']
        circle_info = button.get('circle_info')
        
        # Draw bounding box with dark green color
        color = CLASS_COLORS[0]
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        
        # Draw detected circle if available
        if circle_info is not None:
            circle_x, circle_y, radius = circle_info
            abs_x = x1 + circle_x
            abs_y = y1 + circle_y
            # Draw circle in dark green
            cv2.circle(img, (abs_x, abs_y), radius, color, 2)
            # Draw center point in red for visibility
            cv2.circle(img, center, 5, (0, 0, 255), -1)
        else:
            # Draw center point if no circle detected
            cv2.circle(img, center, 5, (0, 0, 255), -1)
        
        # Draw label with dark background (confidence removed)
        label = f"{CLASS_NAMES[0]} {idx+1}"
        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
        
        cv2.rectangle(img, (x1, y1 - text_size[1] - 8), 
                     (x1 + text_size[0] + 6, y1), color, -1)
        cv2.putText(img, label, (x1 + 3, y1 - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    
    # Draw defects with their specific dark colors
    for defect in defect_info['yolo_defects']:
        x1, y1, x2, y2 = defect['bbox']
        class_id = defect['class']
        conf = defect['confidence']
        
        # Draw bounding box with class-specific dark color
        color = CLASS_COLORS[class_id]
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        
        # Draw label (confidence removed)
        label = f"{CLASS_NAMES[class_id]}"
        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
        
        cv2.rectangle(img, (x1, y1 - text_size[1] - 8), 
                     (x1 + text_size[0] + 6, y1), color, -1)
        cv2.putText(img, label, (x1 + 3, y1 - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    
    # Draw distance lines with BLACK color and BLACK font
    if len(button_data) >= 2 and distances['pairs']:
        for pair in distances['pairs']:
            b1_idx = pair['button1'] - 1
            b2_idx = pair['button2'] - 1
            
            if b1_idx < len(button_data) and b2_idx < len(button_data):
                x1, y1 = button_data[b1_idx]['center']
                x2, y2 = button_data[b2_idx]['center']
                
                # Draw line in BLACK
                cv2.line(img, (x1, y1), (x2, y2), (0, 0, 0), 2)
                
                # Draw distance text at midpoint
                mid_x = (x1 + x2) // 2
                mid_y = (y1 + y2) // 2
                
                dist_text = f"{pair['distance']:.1f}{pair['unit']}"
                text_size = cv2.getTextSize(dist_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                
                # White background for text
                bg_x1 = mid_x - text_size[0]//2 - 3
                bg_y1 = mid_y - text_size[1] - 3
                bg_x2 = mid_x + text_size[0]//2 + 3
                bg_y2 = mid_y + 3
                cv2.rectangle(img, (bg_x1, bg_y1), (bg_x2, bg_y2), (255, 255, 255), -1)
                
                # Distance text in BLACK
                cv2.putText(img, dist_text,
                           (mid_x - text_size[0]//2, mid_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    
    # Draw results info panel at TOP RIGHT (no bars, compact info)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness = 2
    line_height = 30
    padding = 10
    
    # Prepare text lines
    info_lines = [
        f"Buttons: {defect_info['button_count']}",
        f"Defects: {defect_info['total_defects']}"
    ]
    
    # Add max distance info
    if distances['max_distance'] > 0:
        max_text = f"Max: {distances['max_distance']:.1f}{distances['unit']}"
        if distances['max_pair']:
            max_text += f" ({distances['max_pair']})"
        info_lines.append(max_text)
    
    # Calculate panel size
    max_width = 0
    for line in info_lines:
        text_size = cv2.getTextSize(line, font, font_scale, thickness)[0]
        max_width = max(max_width, text_size[0])
    
    panel_width = max_width + 2 * padding
    panel_height = len(info_lines) * line_height + 2 * padding
    
    # Position at top right
    panel_x = w - panel_width - 20
    panel_y = 20
    
    # Draw semi-transparent background
    overlay = img.copy()
    cv2.rectangle(overlay, (panel_x, panel_y), 
                 (panel_x + panel_width, panel_y + panel_height),
                 (40, 40, 40), -1)
    img = cv2.addWeighted(img, 0.7, overlay, 0.3, 0)
    
    # Draw text lines
    y_offset = panel_y + padding + 20
    for line in info_lines:
        # Determine color based on content
        if "Defects:" in line and defect_info['total_defects'] > 0:
            text_color = (0, 0, 200)  # Dark red for defects
        else:
            text_color = (255, 255, 255)  # White for others
        
        cv2.putText(img, line, (panel_x + padding, y_offset),
                   font, font_scale, text_color, thickness)
        y_offset += line_height
    
    return img


# ============================================================================
# MAIN DETECTION LOOP
# ============================================================================

def main():
    """Main detection loop"""
    print("\n" + "="*70)
    print("BUTTON DETECTION SYSTEM")
    print("3 Functions: Button Detection | Distance Measurement | YOLO Defects")
    print("="*70)
    
    # Setup
    create_folders()
    mm_per_pixel = load_calibration()
    
    # Load model
    print("\n Loading YOLO model...")
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Model not found: {MODEL_PATH}")
        return
    
    model = YOLO(MODEL_PATH)
    print(f"✓ Loaded model: {MODEL_PATH}")
    
    # Open camera
    print("\n📷 Opening camera...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    
    if not cap.isOpened():
        print("❌ Cannot open camera")
        return
        
    # Get actual camera resolution (like in stitches.py) to ensure calibration matches
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"✓ Camera opened at {actual_width}x{actual_height}")
    print("\n Starting detection... Press 'q' to quit")
    print("="*70 + "\n")
    
    # Create named window in fullscreen mode
    window_name = "Detection Monitor"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    # Initialize
    prev_frame = None
    last_capture_time = 0
    capture_count = 0
    last_result_image = None  # Store last detection result
    
    # Create black screen for initial display using actual dimensions
    black_screen = np.zeros((actual_height, actual_width, 3), dtype=np.uint8)
    cv2.putText(black_screen, "MONITORING... Waiting for detection",
               (actual_width//2 - 250, actual_height//2), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Cannot read frame")
            break
        
        # Display either last detection result OR black screen
        if last_result_image is not None:
            # Show last detection result ONLY
            display_frame = last_result_image.copy()
        else:
            # Show black screen with monitoring message
            display_frame = black_screen.copy()
            cv2.putText(display_frame, f"Captures: {capture_count}",
                       (actual_width//2 - 80, actual_height//2 + 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        cv2.imshow(window_name, display_frame)
        
        # Check for quit
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("\n⏹ Stopping...")
            break
        
        # Motion detection
        if prev_frame is not None:
            current_time = time.time()
            
            if detect_motion(prev_frame, frame):
                if current_time - last_capture_time >= COOLDOWN_SECONDS:
                    print(f"\n{'='*70}")
                    print(f"📸 MOTION DETECTED - Capture #{capture_count + 1}")
                    print(f"{'='*70}")
                    
                    # Wait for object to stabilize
                    time.sleep(CAPTURE_DELAY)
                    ret, captured_frame = cap.read()
                    if not ret:
                        continue
                    
                    # Generate timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    
                    # Save captured image
                    captured_path = os.path.join(CAPTURED_FOLDER, f"captured_{timestamp}.jpg")
                    cv2.imwrite(captured_path, captured_frame)
                    print(f" Saved: {captured_path}")
                    
                    # ========== FUNCTION 1: BUTTON DETECTION ==========
                    print("\n1️⃣ BUTTON DETECTION:")
                    button_data, yolo_defects = detect_buttons(model, captured_frame)
                    print(f"   Detected {len(button_data)} button(s)")
                    if yolo_defects:
                        print(f"  ⚠ YOLO defects: {len(yolo_defects)}")
                    
                    # ========== FUNCTION 2: DISTANCE CALCULATION ==========
                    print("\n2️⃣ DISTANCE CALCULATION:")
                    distances = calculate_distances(button_data, mm_per_pixel)
                    if distances['max_distance'] > 0:
                        unit = distances['unit']
                        print(f"   Max distance: {distances['max_distance']:.1f}{unit} ({distances['max_pair']})")
                        print(f"   Measured pairs:")
                        for pair in distances['pairs']:
                            print(f"    B{pair['button1']}-B{pair['button2']}: {pair['distance']:.1f}{pair['unit']}")
                    else:
                        print("  ⚠ No distances calculated (need at least 2 buttons)")
                    
                    # ========== FUNCTION 3: DEFECT DETECTION ==========
                    print("\n3️⃣ YOLO DEFECT DETECTION:")
                    defect_info = check_defects(len(button_data), yolo_defects)
                    
                    if defect_info['has_defect']:
                        print(f"  ❌ TOTAL DEFECTS: {defect_info['total_defects']}")
                    else:
                        print("  ✓ NO DEFECTS - PASS")
                    
                    # Draw results and save
                    result_image = draw_results(
                        captured_frame, button_data, distances, defect_info
                    )
                    
                    # Store as last result to display continuously
                    last_result_image = result_image
                    
                    detected_path = os.path.join(DETECTED_FOLDER, f"detected_{timestamp}.jpg")
                    cv2.imwrite(detected_path, result_image)
                    print(f"\n Saved: {detected_path}")
                    print(f"{'='*70}\n")
                    
                    capture_count += 1
                    last_capture_time = current_time
        
        prev_frame = frame.copy()
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print(f"\n✓ Detection stopped. Total captures: {capture_count}")


if __name__ == "__main__":
    main()