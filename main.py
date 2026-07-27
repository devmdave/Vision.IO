import sys
import os
import traceback
import cv2
import numpy as np
from PySide6.QtWidgets import QApplication, QMessageBox
from db import sqlite_db
from ui.main_window import MainWindow

def global_exception_hook(exctype, value, tb):
    """
    Global interceptor for unhandled thread exceptions.
    Prevents silent crashes, logs full traceback to stderr, and presents a GUI critical dialog.
    """
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    print(f"\n[CRITICAL ERROR CRASH]:\n{error_msg}", file=sys.stderr)
    
    app = QApplication.instance()
    if app:
        try:
            QMessageBox.critical(
                None, 
                "Vision.IO - Critical Operations Crash",
                f"A fatal unhandled thread error occurred:\n\n{value}\n\n"
                f"The application logs contain the complete traceback."
            )
        except Exception:
            pass
            
    sys.__excepthook__(exctype, value, tb)

def generate_default_assets(project_root):
    """Generates a high-quality mock camera snapshot if not present on disk."""
    mock_path = os.path.join(project_root, "mock_snapshot.jpg")
    if not os.path.exists(mock_path):
        print("[System] Generating default mock_snapshot.jpg visual asset...")
        # Create a mock 640x480 surveillance frame
        h, w = 480, 640
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        
        # Draw tech grid
        for y in range(0, h, 30):
            cv2.line(frame, (0, y), (w, y), (20, 20, 20), 1)
        for x in range(0, w, 30):
            cv2.line(frame, (x, 0), (x, h), (20, 20, 20), 1)
            
        # Draw mock person outline
        # Body
        cv2.rectangle(frame, (280, 180), (360, 420), (100, 100, 220), -1)
        # Head
        cv2.circle(frame, (320, 140), 30, (200, 170, 150), -1)
        # Bounding box representing YOLO detection
        cv2.rectangle(frame, (270, 100), (370, 430), (0, 0, 255), 2)
        cv2.putText(frame, "PERSON 94%", (270, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Telemetry overlays
        cv2.putText(frame, "CAM01 - ENTRY WAY DETECT", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 102), 2)
        cv2.putText(frame, "RECORDING - EDGE ENGINE ACTIVE", (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
        cv2.putText(frame, "SEEDED INCIDENT HISTORY SNAPSHOT", (20, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 122, 255), 1)
        
        cv2.imwrite(mock_path, frame)
        print(f"[System] Seeded asset saved to: {mock_path}")

def main():
    # Set sys exception hook
    sys.excepthook = global_exception_hook

    # Initialize PySide6 Application
    app = QApplication(sys.argv)
    app.setApplicationName("Vision.IO Desktop")
    
    # Enable quit when window closes
    app.setQuitOnLastWindowClosed(True)

    # Project Root identification
    project_root = os.path.dirname(os.path.abspath(__file__))

    # Initialize SQLite Database & Tables
    print("[System] Initializing database registry...")
    sqlite_db.init_db()

    # Generate mock assets
    generate_default_assets(project_root)

    # Launch GUI
    print("[System] Constructing SOC MainWindow...")
    window = MainWindow()
    window.show()

    print("[System] Application started successfully.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
