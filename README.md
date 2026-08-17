# Button Detection System

A computer vision system for detecting and inspecting sewing needle-eye stitches and snap buttons using YOLOv8, with camera-based distance measurement.

## Features

- **Needle Eye Detection** (`stitches.py`) — Detects stitches and stitch defects in real time from a camera feed, with distance measurement using calibration.
- **Snap Button Detection** (`snap_button.py`) — Detects snap buttons and button defects (bend/round, machine), with distance measurement.
- **Simple UI** (`main.py`) — A PySide6 desktop app with two buttons to launch either detection mode.
- **Calibration** (`calibration.py`, `New callibration/`) — Tools for calibrating the camera to enable real-world distance measurements.

## Requirements

- Python 3
- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)
- OpenCV (`opencv-python`)
- PySide6
- NumPy

Install dependencies:
```bash
pip install ultralytics opencv-python PySide6 numpy
```

## Usage

Run the main UI:
```bash
python main.py
```

Or run a detection script directly:
```bash
python stitches.py [camera_index]
python snap_button.py [camera_index]
```

## Project Structure

- `stitches.pt`, `snap_button_defects.pt` — Trained YOLOv8 model weights
- `calibration.json` — Camera calibration data used for distance measurement
- `captured_images/` — Raw captured frames
- `detection_results/`, `detected_images/` — Output images with detection annotations
