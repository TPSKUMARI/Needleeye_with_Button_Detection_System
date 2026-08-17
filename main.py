"""
Simple UI for Button Detection System
Click a button to automatically run the corresponding detection script
"""

import sys
import subprocess
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton,
                               QVBoxLayout, QWidget, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
import os

# ============================================================
# CAMERA CONFIGURATION - change this to switch camera
# 0 = built-in webcam, 1 = first external camera, 2 = second external, etc.
CAMERA_INDEX = 0
# ============================================================


class DetectionSelectorUI(QMainWindow):
    def __init__(self):
        super().__init__()

        # Script paths - CHANGE THESE TO MATCH YOUR FILES
        self.needle_eye_script = "stitches.py"
        self.snap_button_script = "snap_button.py"
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Button Detection System")
        self.setGeometry(100, 100, 700, 500)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout()
        layout.setSpacing(40)
        layout.setContentsMargins(50, 50, 50, 50)
        
        # Title
        title = QLabel("BUTTON DETECTION SYSTEM")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont("Arial", 32, QFont.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #2C3E50; margin-bottom: 30px;")
        layout.addWidget(title)
        
        # Needle Eye Button
        self.needle_eye_btn = QPushButton("NEEDLE EYE DETECTION")
        self.needle_eye_btn.setMinimumHeight(150)
        self.needle_eye_btn.setFont(QFont("Arial", 22, QFont.Bold))
        self.needle_eye_btn.clicked.connect(self.run_needle_eye)
        self.needle_eye_btn.setStyleSheet("""
            QPushButton {
                background-color:  #023879;
                color: white;
                border: 3px solid #2980B9;
                border-radius: 10px;
                padding: 20px;
            }
            QPushButton:hover {
                background-color: #2980B9;
                border: 3px solid #21618C;
            }
            QPushButton:pressed {
                background-color: #1E8449;
            }
        """)
        layout.addWidget(self.needle_eye_btn)
        
        # Snap Button
        self.snap_button_btn = QPushButton("SNAP BUTTON DETECTION")
        self.snap_button_btn.setMinimumHeight(150)
        self.snap_button_btn.setFont(QFont("Arial", 22, QFont.Bold))
        self.snap_button_btn.clicked.connect(self.run_snap_button)
        self.snap_button_btn.setStyleSheet("""
            QPushButton {
                background-color: #023879;
                color: white;
                border: 3px solid #2980B9;
                border-radius: 10px;
                padding: 20px;
            }
            QPushButton:hover {
                background-color: #2980B9;
                border: 3px solid #21618C;
            }
            QPushButton:pressed {
                background-color: #21618C;
            }
        """)
        layout.addWidget(self.snap_button_btn)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 14))
        self.status_label.setStyleSheet("color: #7F8C8D; margin-top: 20px;")
        layout.addWidget(self.status_label)
        
        central_widget.setLayout(layout)
        
        # Set window style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ECF0F1;
            }
        """)
        
        # Add keyboard shortcuts
        # Press '1' to trigger Needle Eye Detection
        shortcut_1 = QShortcut(QKeySequence('1'), self)
        shortcut_1.activated.connect(self.run_needle_eye)
        
        # Press '2' to trigger Snap Button Detection
        shortcut_2 = QShortcut(QKeySequence('2'), self)
        shortcut_2.activated.connect(self.run_snap_button)
        
        # Press 'ESC' to exit fullscreen (or close if not fullscreen)
        shortcut_esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        shortcut_esc.activated.connect(self.toggle_fullscreen)
    
    def toggle_fullscreen(self):
        """Toggle between fullscreen and normal mode"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def run_needle_eye(self):
        """Run Needle Eye detection script"""
        script_path = self.needle_eye_script
        mode_name = "Needle Eye Detection"
        
        # Check if script exists
        if not os.path.exists(script_path):
            self.status_label.setText(f"ERROR: {script_path} not found!")
            self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 16px;")
            print(f"Error: Script not found: {script_path}")
            return
        
        # Update status
        self.status_label.setText(f"Running {mode_name}...")
        self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 16px;")
        QApplication.processEvents()
        
        # Hide main window
        self.hide()
        
        try:
            print(f"\n{'='*70}")
            print(f"Starting {mode_name}")
            print(f"Running: {script_path}")
            print(f"{'='*70}\n")
            
            # Run script and wait for it to complete
            result = subprocess.run(
                [sys.executable, script_path, str(CAMERA_INDEX)],
                cwd=os.getcwd()
            )
            
            print(f"\n{'='*70}")
            print(f"{mode_name} completed")
            print(f"Return code: {result.returncode}")
            print(f"{'='*70}\n")
            
        except Exception as e:
            print(f"Error running script: {e}")
            self.status_label.setText(f"ERROR: {str(e)}")
            self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 16px;")
        
        finally:
            # Show main window again
            self.show()
            self.status_label.setText("")
            self.status_label.setStyleSheet("color: #7F8C8D; margin-top: 20px; font-size: 14px;")
    
    def run_snap_button(self):
        """Run Snap Button detection script"""
        script_path = self.snap_button_script
        mode_name = "Snap Button Detection"
        
        # Check if script exists
        if not os.path.exists(script_path):
            self.status_label.setText(f"ERROR: {script_path} not found!")
            self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 16px;")
            print(f"Error: Script not found: {script_path}")
            return
        
        # Update status
        self.status_label.setText(f"Running {mode_name}...")
        self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 16px;")
        QApplication.processEvents()
        
        # Hide main window
        self.hide()
        
        try:
            print(f"\n{'='*70}")
            print(f"Starting {mode_name}")
            print(f"Running: {script_path}")
            print(f"{'='*70}\n")
            
            # Run script and wait for it to complete
            result = subprocess.run(
                [sys.executable, script_path, str(CAMERA_INDEX)],
                cwd=os.getcwd()
            )
            
            print(f"\n{'='*70}")
            print(f"{mode_name} completed")
            print(f"Return code: {result.returncode}")
            print(f"{'='*70}\n")
            
        except Exception as e:
            print(f"Error running script: {e}")
            self.status_label.setText(f"ERROR: {str(e)}")
            self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 16px;")
        
        finally:
            # # Show main window again
            self.show()
            self.status_label.setText("")
            self.status_label.setStyleSheet("color: #7F8C8D; margin-top: 20px; font-size: 14px;")


def main():
    """Main function to run the application"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = DetectionSelectorUI()
    window.showFullScreen()  # Start in fullscreen mode
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()