import cv2
import math
import json
import os

CAMERA_INDEX = 1          # 0 = built-in webcam, 1 = first USB camera, 2 = second, etc.
CALIBRATION_CYCLES = 5
CALIBRATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'calibration.json')


def get_two_points(image, window_name):
    points = []
    display = image.copy()

    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 2:
            points.append((x, y))
            cv2.circle(display, (x, y), 6, (0, 255, 0), -1)
            cv2.putText(display, str(len(points)), (x + 8, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            if len(points) == 2:
                cv2.line(display, points[0], points[1], (0, 255, 0), 2)
                px = math.dist(points[0], points[1])
                cv2.putText(display, f"{px:.1f} px", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.imshow(window_name, display)

    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, mouse_callback)
    cv2.imshow(window_name, display)

    print("  Click point 1, then point 2 on the image.")
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
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    print("=" * 45)
    print("       USB Camera Calibration (mm)")
    print("=" * 45)
    print(f"Running {CALIBRATION_CYCLES} calibration cycles.")
    print("In each cycle:")
    print("  1. Press ENTER in the camera window to capture.")
    print("  2. Click 2 points on the captured image.")
    print("  3. Type the actual distance (mm) in the terminal.")
    print()

    calibration_values = []

    for cycle in range(1, CALIBRATION_CYCLES + 1):
        print(f"--- Cycle {cycle} / {CALIBRATION_CYCLES} ---")
        print("  Live feed open. Press ENTER to capture a frame.")

        captured = None
        while True:
            ret, frame = cap.read()
            if not ret:
                print("  Error reading frame. Retrying...")
                continue
            cv2.putText(frame, "Press ENTER to capture", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
            cv2.imshow("Live Feed", frame)
            key = cv2.waitKey(1)
            if key == 13:  # Enter
                captured = frame.copy()
                break

        cv2.destroyWindow("Live Feed")
        print("  Frame captured.")

        points = get_two_points(captured, f"Cycle {cycle} — Mark 2 Points")

        px_dist = math.dist(points[0], points[1])
        print(f"  Pixel distance: {px_dist:.2f} px")

        while True:
            try:
                actual_mm = float(input("  Enter actual distance in mm: "))
                if actual_mm <= 0:
                    print("  Distance must be positive. Try again.")
                    continue
                break
            except ValueError:
                print("  Invalid input. Enter a number.")

        px_per_mm = px_dist / actual_mm
        calibration_values.append(px_per_mm)
        print(f"  Calibration value: {px_per_mm:.6f} px/mm\n")

    cap.release()
    cv2.destroyAllWindows()

    print("=" * 45)
    print("         Calibration Results")
    print("=" * 45)
    for i, val in enumerate(calibration_values, 1):
        print(f"  Cycle {i}: {val:.6f} px/mm")

    avg = sum(calibration_values) / len(calibration_values)
    mm_per_pixel = 1.0 / avg
    print(f"\n  Average: {avg:.6f} px/mm")

    data = {
        "pixels_per_mm": avg,
        "mm_per_pixel": mm_per_pixel,
        "unit": "mm",
        "cycles": calibration_values
    }
    with open(CALIBRATION_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nCalibration saved to '{CALIBRATION_FILE}'.")
    print("Run 'camera_measure.py' to measure distances.")


if __name__ == "__main__":
    main()
