# import sys
# import cv2
# import numpy as np
# import json
# from datetime import datetime
# from PySide6.QtWidgets import (
#     QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
#     QHBoxLayout, QFrame, QMessageBox
# )
# from PySide6.QtGui import QPixmap, QImage
# from PySide6.QtCore import Qt, QThread, Signal
# import warnings
# warnings.filterwarnings("ignore", category=DeprecationWarning)

# # -------------------------------------------------------------------------
# # DISPLAY SETTINGS FOR 7-inch 800×480 TOUCH SCREEN (preview only)
# # -------------------------------------------------------------------------
# PREVIEW_WIDTH  = FRAME_WIDTH = 1280
# PREVIEW_HEIGHT = 720

# # ============================================================================
# # CALIBRATION WORKER THREAD
# # ============================================================================
# class CalibrationWorker(QThread):
#     frame_ready = Signal(object)

#     def __init__(self, camera_index=0):
#         super().__init__()
#         self.camera_index = camera_index
#         self._running = True
#         self.cap = None

#     def stop(self):
#         self._running = False

#     def run(self):
#         self.cap = cv2.VideoCapture(self.camera_index)
#         if not self.cap.isOpened():
#             return

#         self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
#         self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

#         while self._running:
#             ret, frame = self.cap.read()
#             if ret:
#                 self.frame_ready.emit(frame)
#             self.msleep(33)

#         if self.cap:
#             self.cap.release()


# # ============================================================================
# # CALIBRATION WINDOW
# # ============================================================================
# class CalibrationWindow(QWidget):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("Camera Calibration")
#         self.resize(900, 600)  # Flexible window – buttons visible

#         # State variables
#         self.captured = False
#         self.drawing = False
#         self.start_point = None
#         self.end_point = None
#         self.current_frame = None
#         self.captured_frame = None
#         self.reference_length_mm = 20

#         # Worker thread
#         self.worker = None

#         self._build_ui()
#         self.setStyleSheet(self.stylesheet())

#     def _build_ui(self):
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(15, 15, 15, 15)
#         layout.setSpacing(10)

#         # Control buttons
#         ctrl = QHBoxLayout()
#         ctrl.setSpacing(12)
#         self.capture_btn = QPushButton("Capture")
#         self.save_btn = QPushButton("Save")
#         self.reset_btn = QPushButton("Reset")
#         self.quit_btn = QPushButton("Quit")

#         self.save_btn.setEnabled(False)
#         self.reset_btn.setEnabled(False)

#         self.capture_btn.clicked.connect(self.capture_image)
#         self.save_btn.clicked.connect(self.save_calibration)
#         self.reset_btn.clicked.connect(self.reset_calibration)
#         self.quit_btn.clicked.connect(self.quit_app)

#         ctrl.addWidget(self.capture_btn)
#         ctrl.addWidget(self.save_btn)
#         ctrl.addWidget(self.reset_btn)
#         ctrl.addStretch()
#         ctrl.addWidget(self.quit_btn)

#         # Instruction label
#         self.instruction_label = QLabel("Place ruler in camera view and click 'Capture'")
#         self.instruction_label.setAlignment(Qt.AlignCenter)
#         self.instruction_label.setStyleSheet(
#             "color: #00BFFF; font-size: 18px; font-weight: bold; padding: 10px;"
#         )

#         # Video display panel – fixed 400×480
#         self.video_panel = QFrame()
#         self.video_panel.setStyleSheet(
#             "background-color: #121A2C; border: 2px solid #1F2A40; border-radius: 18px;"
#         )
#         self.video_panel.setFixedSize(PREVIEW_WIDTH, PREVIEW_HEIGHT)

#         self.video_label = QLabel()
#         self.video_label.setAlignment(Qt.AlignCenter)
#         self.video_label.setScaledContents(False)  # Auto-scale 1280×720 → 400×480
#         self.video_label.setMouseTracking(True)
#         self.video_label.mousePressEvent = self.mouse_press
#         self.video_label.mouseMoveEvent = self.mouse_move
#         self.video_label.mouseReleaseEvent = self.mouse_release

#         panel_layout = QVBoxLayout(self.video_panel)
#         panel_layout.addWidget(self.video_label)

#         layout.addLayout(ctrl)
#         layout.addWidget(self.instruction_label)
#         layout.addWidget(self.video_panel, alignment=Qt.AlignCenter)

#         # Start camera
#         self.start_camera()

#     def stylesheet(self):
#         return """
#             QWidget {
#                 background-color: #0A0F1F;
#                 color: #E6E9EF;
#                 font-size: 18px;
#             }
            
#             QPushButton {
#                 background-color: #3A5A9C;
#                 color: white;
#                 border: 2px solid #1F2A40;
#                 padding: 12px 18px;           /* BIGGER PADDING */
#                 border-radius: 15px;
#                 font-size: 16px;              /* BIG TEXT */
#                 font-weight: bold;
#                 min-height: 60px;            /* TALL BUTTON */
#                 min-width: 120px;             /* WIDE BUTTON */
#             }
            
#             QPushButton:hover {
#                 background-color: #4C6FB5;
#             }
            
#             QPushButton:pressed {
#                 background-color: #2E4A80;
#             }
            
#             QPushButton:disabled {
#                 background-color: #2A3A5C;
#                 color: #6A7A9F;
#                 border: 2px solid #1F2A40;
#             }
            
#             QLabel {
#                 font-size: 20px;
#                 padding: 10px;
#             }
#             """

#     def start_camera(self):
#         self.worker = CalibrationWorker(camera_index=0)
#         self.worker.frame_ready.connect(self.update_frame)
#         self.worker.start()

#     def update_frame(self, frame):
#         if not self.captured:
#             self.current_frame = frame.copy()
#             display_frame = frame
#         else:
#             display_frame = self.captured_frame.copy()

#             if self.start_point and self.end_point:
#                 cv2.line(display_frame, self.start_point, self.end_point, (0, 255, 0), 3)
#                 cv2.circle(display_frame, self.start_point, 8, (0, 0, 255), -1)
#                 cv2.circle(display_frame, self.end_point, 8, (0, 0, 255), -1)

#                 pixel_length = np.sqrt(
#                     (self.end_point[0] - self.start_point[0])**2 +
#                     (self.end_point[1] - self.start_point[1])**2
#                 )

#                 mid_point = (
#                     (self.start_point[0] + self.end_point[0]) // 2,
#                     (self.start_point[1] + self.end_point[1]) // 2
#                 )

#                 text = f"{pixel_length:.1f} px"
#                 font = cv2.FONT_HERSHEY_SIMPLEX
#                 text_size = cv2.getTextSize(text, font, 0.7, 2)[0]

#                 cv2.rectangle(
#                     display_frame,
#                     (mid_point[0] - text_size[0]//2 - 5, mid_point[1] - text_size[1] - 10),
#                     (mid_point[0] + text_size[0]//2 + 5, mid_point[1] + 5),
#                     (0, 0, 0),
#                     -1
#                 )
#                 cv2.putText(
#                     display_frame,
#                     text,
#                     (mid_point[0] - text_size[0]//2, mid_point[1]),
#                     font,
#                     0.7,
#                     (0, 255, 0),
#                     2
#                 )

#         self.display_image(display_frame)

#     def display_image(self, frame):
#         rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#         h, w, ch = rgb.shape
#         qt_image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
#         pixmap = QPixmap.fromImage(qt_image)
#         self.video_label.setPixmap(pixmap)  # QLabel auto-scales due to setScaledContents(True)

#     def capture_image(self):
#         if self.current_frame is not None:
#             self.captured_frame = self.current_frame.copy()
#             self.captured = True
#             self.capture_btn.setEnabled(False)
#             self.save_btn.setEnabled(False)
#             self.reset_btn.setEnabled(True)

#             self.instruction_label.setText("Click and drag to mark a 20mm distance on the ruler")
#             self.instruction_label.setStyleSheet(
#                 "color: #00FF00; font-size: 18px; font-weight: bold; padding: 10px;"
#             )
#             self.display_image(self.captured_frame)

#     def mouse_press(self, event):
#         if not self.captured:
#             return

#         pos = event.pos()
#         pixmap = self.video_label.pixmap()
#         if not pixmap:
#             return

#         # Map click from label (400×480) → original image (1280×720)
#         scale_x = 1280 / PREVIEW_WIDTH
#         scale_y = 720 / PREVIEW_HEIGHT

#         x = int((pos.x()) * scale_x)
#         y = int((pos.y()) * scale_y)

#         # Clamp to image bounds
#         x = max(0, min(x, 1279))
#         y = max(0, min(y, 719))

#         self.start_point = (x, y)
#         self.end_point = (x, y)
#         self.drawing = True

#         self.instruction_label.setText("Drawing... Release mouse to finish")
#         self.instruction_label.setStyleSheet(
#             "color: #FFD700; font-size: 18px; font-weight: bold; padding: 10px;"
#         )

#     def mouse_move(self, event):
#         if not self.drawing or not self.captured:
#             return

#         pos = event.pos()
#         pixmap = self.video_label.pixmap()
#         if not pixmap:
#             return

#         scale_x = 1280 / PREVIEW_WIDTH
#         scale_y = 720 / PREVIEW_HEIGHT

#         x = int(pos.x() * scale_x)
#         y = int(pos.y() * scale_y)
#         x = max(0, min(x, 1279))
#         y = max(0, min(y, 719))

#         self.end_point = (x, y)

#         # Redraw with live feedback
#         display_frame = self.captured_frame.copy()
#         cv2.line(display_frame, self.start_point, self.end_point, (0, 255, 0), 3)
#         cv2.circle(display_frame, self.start_point, 8, (0, 0, 255), -1)
#         cv2.circle(display_frame, self.end_point, 8, (0, 0, 255), -1)

#         pixel_length = np.sqrt(
#             (self.end_point[0] - self.start_point[0])**2 +
#             (self.end_point[1] - self.start_point[1])**2
#         )

#         mid_point = (
#             (self.start_point[0] + self.end_point[0]) // 2,
#             (self.start_point[1] + self.end_point[1]) // 2
#         )

#         text = f"{pixel_length:.1f} px"
#         font = cv2.FONT_HERSHEY_SIMPLEX
#         text_size = cv2.getTextSize(text, font, 0.7, 2)[0]

#         cv2.rectangle(
#             display_frame,
#             (mid_point[0] - text_size[0]//2 - 5, mid_point[1] - text_size[1] - 10),
#             (mid_point[0] + text_size[0]//2 + 5, mid_point[1] + 5),
#             (0, 0, 0),
#             -1
#         )
#         cv2.putText(
#             display_frame,
#             text,
#             (mid_point[0] - text_size[0]//2, mid_point[1]),
#             font,
#             0.7,
#             (0, 255, 0),
#             2
#         )

#         self.display_image(display_frame)

#     def mouse_release(self, event):
#         if self.drawing:
#             self.drawing = False
#             if self.start_point and self.end_point:
#                 pixel_length = np.sqrt(
#                     (self.end_point[0] - self.start_point[0])**2 +
#                     (self.end_point[1] - self.start_point[1])**2
#                 )
#                 if pixel_length > 10:
#                     self.save_btn.setEnabled(True)
#                     self.instruction_label.setText(
#                         f"Line drawn ({pixel_length:.1f} pixels for 20mm). Click 'Save' to save calibration"
#                     )
#                     self.instruction_label.setStyleSheet(
#                         "color: #00FF00; font-size: 18px; font-weight: bold; padding: 10px;"
#                     )
#                 else:
#                     self.instruction_label.setText("Line too short! Please draw again")
#                     self.instruction_label.setStyleSheet(
#                         "color: #FF5252; font-size: 18px; font-weight: bold; padding: 10px;"
#                     )
#                     self.start_point = None
#                     self.end_point = None

#     def save_calibration(self):
#         if not self.start_point or not self.end_point:
#             QMessageBox.warning(self, "Warning", "Please draw a line on the 20mm ruler distance first!")
#             return

#         pixel_length = np.sqrt(
#             (self.end_point[0] - self.start_point[0])**2 +
#             (self.end_point[1] - self.start_point[1])**2
#         )

#         if pixel_length <= 0:
#             QMessageBox.warning(self, "Warning", "Invalid line length!")
#             return

#         pixels_per_mm = pixel_length / self.reference_length_mm
#         mm_per_pixel = 1 / pixels_per_mm

#         calibration_data = {
#             "pixels_per_mm": pixels_per_mm,
#             "mm_per_pixel": mm_per_pixel,
#             "reference_length_mm": self.reference_length_mm,
#             "calibration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         }

#         try:
#             with open('calibration.json', 'w') as f:
#                 json.dump(calibration_data, f, indent=4)

#             msg = f"Calibration saved successfully!\n\n"
#             msg += f"Pixels per mm: {pixels_per_mm:.2f}\n"
#             msg += f"mm per pixel: {mm_per_pixel:.4f}"

#             QMessageBox.information(self, "Success", msg)
#             print(f"Calibration result: {pixels_per_mm:.2f} pixels per mm")
#             print(f"Conversion factor: {mm_per_pixel:.4f} mm per pixel")
#             print(f"Calibration data saved to 'calibration.json'")

#             self.instruction_label.setText("Calibration saved successfully! You can close this window.")
#             self.instruction_label.setStyleSheet(
#                 "color: #4CAF50; font-size: 18px; font-weight: bold; padding: 10px;"
#             )

#         except Exception as e:
#             QMessageBox.critical(self, "Error", f"Failed to save calibration: {str(e)}")

#     def reset_calibration(self):
#         self.captured = False
#         self.drawing = False
#         self.start_point = None
#         self.end_point = None
#         self.captured_frame = None

#         self.capture_btn.setEnabled(True)
#         self.save_btn.setEnabled(False)
#         self.reset_btn.setEnabled(False)

#         self.instruction_label.setText("Place ruler in camera view and click 'Capture'")
#         self.instruction_label.setStyleSheet(
#             "color: #00BFFF; font-size: 18px; font-weight: bold; padding: 10px;"
#         )

#     def quit_app(self):
#         if self.worker:
#             self.worker.stop()
#             self.worker.wait()
#         self.close()

#     def closeEvent(self, event):
#         if self.worker:
#             self.worker.stop()
#             self.worker.wait()
#         event.accept()


# # ============================================================================
# # MAIN
# # ============================================================================
# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = CalibrationWindow()
#     #window.show()
#     window.showFullScreen()
#     sys.exit(app.exec())


import sys
import cv2
import numpy as np
import json
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QFrame, QMessageBox
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QThread, Signal
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# -------------------------------------------------------------------------
# DISPLAY SETTINGS - FIXED TO MATCH CAMERA ASPECT RATIO (16:9)
# -------------------------------------------------------------------------
# Camera resolution: 1280×720 (16:9)
# Preview resolution: Must maintain 16:9 aspect ratio
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

# Preview size - maintains 16:9 aspect ratio
PREVIEW_WIDTH  = 640   # Half of camera width
PREVIEW_HEIGHT = 360   # Half of camera height (640/16*9 = 360)

# ============================================================================
# CALIBRATION WORKER THREAD
# ============================================================================
class CalibrationWorker(QThread):
    frame_ready = Signal(object)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self._running = True
        self.cap = None

    def stop(self):
        self._running = False

    def run(self):
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

        while self._running:
            ret, frame = self.cap.read()
            if ret:
                self.frame_ready.emit(frame)
            self.msleep(33)

        if self.cap:
            self.cap.release()


# ============================================================================
# CALIBRATION WINDOW
# ============================================================================
class CalibrationWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Calibration")
        
        # State variables
        self.captured = False
        self.drawing = False
        self.start_point = None
        self.end_point = None
        self.current_frame = None
        self.captured_frame = None
        self.reference_length_mm = 20

        # Worker thread
        self.worker = None

        self._build_ui()
        self.setStyleSheet(self.stylesheet())

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Control buttons
        ctrl = QHBoxLayout()
        ctrl.setSpacing(12)
        self.capture_btn = QPushButton("Capture")
        self.save_btn = QPushButton("Save")
        self.reset_btn = QPushButton("Reset")
        self.quit_btn = QPushButton("Quit")

        self.save_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)

        self.capture_btn.clicked.connect(self.capture_image)
        self.save_btn.clicked.connect(self.save_calibration)
        self.reset_btn.clicked.connect(self.reset_calibration)
        self.quit_btn.clicked.connect(self.quit_app)

        ctrl.addWidget(self.capture_btn)
        ctrl.addWidget(self.save_btn)
        ctrl.addWidget(self.reset_btn)
        ctrl.addStretch()
        ctrl.addWidget(self.quit_btn)

        # Instruction label
        self.instruction_label = QLabel("Place ruler in camera view and click 'Capture'")
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setStyleSheet(
            "color: #00BFFF; font-size: 18px; font-weight: bold; padding: 10px;"
        )

        # Camera info label
        self.info_label = QLabel(f"Camera: {CAMERA_WIDTH}×{CAMERA_HEIGHT} | Preview: {PREVIEW_WIDTH}×{PREVIEW_HEIGHT}")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet(
            "color: #888888; font-size: 14px; padding: 5px;"
        )

        # Video display panel - FIXED SIZE with correct aspect ratio
        self.video_panel = QFrame()
        self.video_panel.setStyleSheet(
            "background-color: #121A2C; border: 2px solid #1F2A40; border-radius: 18px;"
        )
        self.video_panel.setFixedSize(PREVIEW_WIDTH, PREVIEW_HEIGHT)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setScaledContents(False)  # FIXED: Don't stretch - maintain aspect ratio
        self.video_label.setMouseTracking(True)
        self.video_label.mousePressEvent = self.mouse_press
        self.video_label.mouseMoveEvent = self.mouse_move
        self.video_label.mouseReleaseEvent = self.mouse_release

        panel_layout = QVBoxLayout(self.video_panel)
        panel_layout.addWidget(self.video_label)

        layout.addLayout(ctrl)
        layout.addWidget(self.instruction_label)
        layout.addWidget(self.info_label)
        layout.addWidget(self.video_panel, alignment=Qt.AlignCenter)

        # Start camera
        self.start_camera()

    def stylesheet(self):
        return """
            QWidget {
                background-color: #0A0F1F;
                color: #E6E9EF;
                font-size: 18px;
            }
            
            QPushButton {
                background-color: #3A5A9C;
                color: white;
                border: 2px solid #1F2A40;
                padding: 12px 18px;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
                min-height: 60px;
                min-width: 120px;
            }
            
            QPushButton:hover {
                background-color: #4C6FB5;
            }
            
            QPushButton:pressed {
                background-color: #2E4A80;
            }
            
            QPushButton:disabled {
                background-color: #2A3A5C;
                color: #6A7A9F;
                border: 2px solid #1F2A40;
            }
            
            QLabel {
                font-size: 20px;
                padding: 10px;
            }
            """

    def start_camera(self):
        self.worker = CalibrationWorker(camera_index=0)
        self.worker.frame_ready.connect(self.update_frame)
        self.worker.start()

    def update_frame(self, frame):
        if not self.captured:
            self.current_frame = frame.copy()
            display_frame = frame
        else:
            display_frame = self.captured_frame.copy()

            if self.start_point and self.end_point:
                cv2.line(display_frame, self.start_point, self.end_point, (0, 255, 0), 3)
                cv2.circle(display_frame, self.start_point, 8, (0, 0, 255), -1)
                cv2.circle(display_frame, self.end_point, 8, (0, 0, 255), -1)

                pixel_length = np.sqrt(
                    (self.end_point[0] - self.start_point[0])**2 +
                    (self.end_point[1] - self.start_point[1])**2
                )

                mid_point = (
                    (self.start_point[0] + self.end_point[0]) // 2,
                    (self.start_point[1] + self.end_point[1]) // 2
                )

                text = f"{pixel_length:.1f} px"
                font = cv2.FONT_HERSHEY_SIMPLEX
                text_size = cv2.getTextSize(text, font, 0.7, 2)[0]

                cv2.rectangle(
                    display_frame,
                    (mid_point[0] - text_size[0]//2 - 5, mid_point[1] - text_size[1] - 10),
                    (mid_point[0] + text_size[0]//2 + 5, mid_point[1] + 5),
                    (0, 0, 0),
                    -1
                )
                cv2.putText(
                    display_frame,
                    text,
                    (mid_point[0] - text_size[0]//2, mid_point[1]),
                    font,
                    0.7,
                    (0, 255, 0),
                    2
                )

        self.display_image(display_frame)

    def display_image(self, frame):
        """Display image with proper scaling - maintains aspect ratio"""
        # Resize frame to preview size while maintaining quality
        resized = cv2.resize(frame, (PREVIEW_WIDTH, PREVIEW_HEIGHT), interpolation=cv2.INTER_LINEAR)
        
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qt_image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        self.video_label.setPixmap(pixmap)

    def capture_image(self):
        if self.current_frame is not None:
            self.captured_frame = self.current_frame.copy()
            self.captured = True
            self.capture_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            self.reset_btn.setEnabled(True)

            self.instruction_label.setText("Click and drag to mark a 20mm distance on the ruler")
            self.instruction_label.setStyleSheet(
                "color: #00FF00; font-size: 18px; font-weight: bold; padding: 10px;"
            )
            self.display_image(self.captured_frame)

    def mouse_press(self, event):
        if not self.captured:
            return

        pos = event.pos()
        
        # FIXED: Proper coordinate mapping
        # Since we resize the image to PREVIEW_WIDTH × PREVIEW_HEIGHT before display,
        # we need to map back to camera resolution
        scale_x = CAMERA_WIDTH / PREVIEW_WIDTH
        scale_y = CAMERA_HEIGHT / PREVIEW_HEIGHT

        x = int(pos.x() * scale_x)
        y = int(pos.y() * scale_y)

        # Clamp to camera resolution bounds
        x = max(0, min(x, CAMERA_WIDTH - 1))
        y = max(0, min(y, CAMERA_HEIGHT - 1))

        self.start_point = (x, y)
        self.end_point = (x, y)
        self.drawing = True

        self.instruction_label.setText("Drawing... Release mouse to finish")
        self.instruction_label.setStyleSheet(
            "color: #FFD700; font-size: 18px; font-weight: bold; padding: 10px;"
        )

    def mouse_move(self, event):
        if not self.drawing or not self.captured:
            return

        pos = event.pos()
        
        # FIXED: Proper coordinate mapping
        scale_x = CAMERA_WIDTH / PREVIEW_WIDTH
        scale_y = CAMERA_HEIGHT / PREVIEW_HEIGHT

        x = int(pos.x() * scale_x)
        y = int(pos.y() * scale_y)
        x = max(0, min(x, CAMERA_WIDTH - 1))
        y = max(0, min(y, CAMERA_HEIGHT - 1))

        self.end_point = (x, y)

        # Redraw with live feedback
        display_frame = self.captured_frame.copy()
        cv2.line(display_frame, self.start_point, self.end_point, (0, 255, 0), 3)
        cv2.circle(display_frame, self.start_point, 8, (0, 0, 255), -1)
        cv2.circle(display_frame, self.end_point, 8, (0, 0, 255), -1)

        pixel_length = np.sqrt(
            (self.end_point[0] - self.start_point[0])**2 +
            (self.end_point[1] - self.start_point[1])**2
        )

        mid_point = (
            (self.start_point[0] + self.end_point[0]) // 2,
            (self.start_point[1] + self.end_point[1]) // 2
        )

        text = f"{pixel_length:.1f} px"
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(text, font, 0.7, 2)[0]

        cv2.rectangle(
            display_frame,
            (mid_point[0] - text_size[0]//2 - 5, mid_point[1] - text_size[1] - 10),
            (mid_point[0] + text_size[0]//2 + 5, mid_point[1] + 5),
            (0, 0, 0),
            -1
        )
        cv2.putText(
            display_frame,
            text,
            (mid_point[0] - text_size[0]//2, mid_point[1]),
            font,
            0.7,
            (0, 255, 0),
            2
        )

        self.display_image(display_frame)

    def mouse_release(self, event):
        if self.drawing:
            self.drawing = False
            if self.start_point and self.end_point:
                pixel_length = np.sqrt(
                    (self.end_point[0] - self.start_point[0])**2 +
                    (self.end_point[1] - self.start_point[1])**2
                )
                if pixel_length > 10:
                    self.save_btn.setEnabled(True)
                    
                    # Calculate and show calibration preview
                    pixels_per_mm = pixel_length / self.reference_length_mm
                    mm_per_pixel = 1 / pixels_per_mm
                    
                    self.instruction_label.setText(
                        f"Line: {pixel_length:.1f}px for 20mm | "
                        f"Calibration: {mm_per_pixel:.4f} mm/px | Click 'Save'"
                    )
                    self.instruction_label.setStyleSheet(
                        "color: #00FF00; font-size: 16px; font-weight: bold; padding: 10px;"
                    )
                else:
                    self.instruction_label.setText("Line too short! Please draw again")
                    self.instruction_label.setStyleSheet(
                        "color: #FF5252; font-size: 18px; font-weight: bold; padding: 10px;"
                    )
                    self.start_point = None
                    self.end_point = None

    def save_calibration(self):
        if not self.start_point or not self.end_point:
            QMessageBox.warning(self, "Warning", "Please draw a line on the 20mm ruler distance first!")
            return

        pixel_length = np.sqrt(
            (self.end_point[0] - self.start_point[0])**2 +
            (self.end_point[1] - self.start_point[1])**2
        )

        if pixel_length <= 0:
            QMessageBox.warning(self, "Warning", "Invalid line length!")
            return

        pixels_per_mm = pixel_length / self.reference_length_mm
        mm_per_pixel = 1 / pixels_per_mm

        calibration_data = {
            "pixels_per_mm": pixels_per_mm,
            "mm_per_pixel": mm_per_pixel,
            "reference_length_mm": self.reference_length_mm,
            "camera_resolution": f"{CAMERA_WIDTH}x{CAMERA_HEIGHT}",
            "calibration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            with open('calibration.json', 'w') as f:
                json.dump(calibration_data, f, indent=4)

            msg = f"Calibration saved successfully!\n\n"
            msg += f"Camera Resolution: {CAMERA_WIDTH}×{CAMERA_HEIGHT}\n"
            msg += f"Line Length: {pixel_length:.1f} pixels\n"
            msg += f"Reference: {self.reference_length_mm}mm\n\n"
            msg += f"Pixels per mm: {pixels_per_mm:.2f}\n"
            msg += f"mm per pixel: {mm_per_pixel:.4f}\n\n"
            msg += f"Saved to: calibration.json"

            QMessageBox.information(self, "Success", msg)
            print(f"\n{'='*60}")
            print(f"CALIBRATION SUCCESSFUL")
            print(f"{'='*60}")
            print(f"Camera Resolution: {CAMERA_WIDTH}×{CAMERA_HEIGHT}")
            print(f"Line Length: {pixel_length:.1f} pixels")
            print(f"Reference Length: {self.reference_length_mm}mm")
            print(f"Pixels per mm: {pixels_per_mm:.2f}")
            print(f"mm per pixel: {mm_per_pixel:.4f}")
            print(f"Calibration data saved to 'calibration.json'")
            print(f"{'='*60}\n")

            self.instruction_label.setText("Calibration saved! You can close this window.")
            self.instruction_label.setStyleSheet(
                "color: #4CAF50; font-size: 18px; font-weight: bold; padding: 10px;"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save calibration: {str(e)}")

    def reset_calibration(self):
        self.captured = False
        self.drawing = False
        self.start_point = None
        self.end_point = None
        self.captured_frame = None

        self.capture_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)

        self.instruction_label.setText("Place ruler in camera view and click 'Capture'")
        self.instruction_label.setStyleSheet(
            "color: #00BFFF; font-size: 18px; font-weight: bold; padding: 10px;"
        )

    def quit_app(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        self.close()

    def closeEvent(self, event):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        event.accept()


# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CalibrationWindow()
    
    # Enable fullscreen mode
    window.showFullScreen()
    
    sys.exit(app.exec())