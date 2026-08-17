import cv2
import math
import json
import os

CAMERA_INDEX = 1          # 0 = built-in webcam, 1 = first USB camera, 2 = second, etc.
CALIBRATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'calibration.json')


def load_calibration():
    try:
        with open(CALIBRATION_FILE, "r") as f:
            data = json.load(f)
        return data["pixels_per_mm"]
    except FileNotFoundError:
        print(f"Error: '{CALIBRATION_FILE}' not found.")
        print("Run 'camera_calibrate.py' first to generate calibration data.")
        return None
    except KeyError:
        print(f"Error: Calibration file is missing 'pixels_per_mm'. Re-run calibration.")
        return None


def get_two_points(image, window_name, px_per_mm):
    points = []
    display = image.copy()

    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 2:
            points.append((x, y))
            cv2.circle(display, (x, y), 6, (255, 80, 0), -1)
            cv2.putText(display, str(len(points)), (x + 8, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 80, 0), 2)
            if len(points) == 2:
                cv2.line(display, points[0], points[1], (255, 80, 0), 2)
                px = math.dist(points[0], points[1])
                mm = px / px_per_mm
                mid = ((points[0][0] + points[1][0]) // 2,
                       (points[0][1] + points[1][1]) // 2)
                cv2.putText(display, f"{mm:.2f} mm", (mid[0] - 40, mid[1] - 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                cv2.putText(display, f"({px:.1f} px)", (mid[0] - 40, mid[1] + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
            cv2.imshow(window_name, display)

    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, mouse_callback)
    cv2.imshow(window_name, display)

    print("  Click point 1, then point 2 to measure.")
    print("  Press any key after marking both points to continue.")
    while len(points) < 2:
        if cv2.waitKey(10) != -1:
            break
    while len(points) < 2:
        cv2.waitKey(10)
    cv2.waitKey(0)
    cv2.destroyWindow(window_name)
    return points


def main():
    px_per_mm = load_calibration()
    if px_per_mm is None:
        return

    print("=" * 45)
    print("       Distance Measurement (mm)")
    print("=" * 45)
    print(f"Calibration loaded: {px_per_mm:.6f} px/mm")
    print("Press ENTER in the camera window to capture.")
    print("Press Q in the camera window to quit.\n")

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    measurement_num = 0

    while True:
        measurement_num += 1
        print(f"--- Measurement {measurement_num} ---")
        print("  Live feed open. Press ENTER to capture, Q to quit.")

        captured = None
        quit_requested = False
        while True:
            ret, frame = cap.read()
            if not ret:
                print("  Error reading frame. Retrying...")
                continue
            cv2.putText(frame, "ENTER=capture  Q=quit", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
            cv2.imshow("Live Feed", frame)
            key = cv2.waitKey(1)
            if key == 13:  # Enter
                captured = frame.copy()
                break
            elif key in (ord('q'), ord('Q')):
                quit_requested = True
                break

        cv2.destroyWindow("Live Feed")

        if quit_requested:
            print("\nSession ended by user.")
            break

        print("  Frame captured.")
        points = get_two_points(captured, f"Measurement {measurement_num}", px_per_mm)

        px_dist = math.dist(points[0], points[1])
        mm_dist = px_dist / px_per_mm

        print(f"  Pixel distance : {px_dist:.2f} px")
        print(f"  Measured distance: {mm_dist:.2f} mm\n")

        again = input("  Measure again? (y / n): ").strip().lower()
        if again != 'y':
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nTotal measurements taken: {measurement_num}")


if __name__ == "__main__":
    main()
