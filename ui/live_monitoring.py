import time
import os
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox
from PySide6.QtGui import QFont

from ui.camera_manager import CameraManager
from ui.video_grid import VideoGridWidget
from ui.components.event_feed import EventFeedWidget

class LiveMonitoringTab(QWidget):
    # Signals for orchestration (MainWindow will connect to these)
    scan_network_clicked = Signal()
    pause_ai_clicked = Signal(bool)
    take_snapshot_clicked = Signal(int)  # Emits camera_id to snapshot
    add_camera_clicked = Signal(str, str) # Emits name, url
    delete_camera_clicked = Signal(int) # Emits camera_id

    def __init__(self):
        super().__init__()
        self.active_camera_id = None
        self.ai_paused = False
        self.init_ui()

    def init_ui(self):
        # Outer horizontal layout to hold left panel, center panel, and right panel
        h_layout = QHBoxLayout(self)
        h_layout.setContentsMargins(12, 12, 12, 12)
        h_layout.setSpacing(12) # Gutter spacing from DESIGN.md

        # 1. Left Panel: Camera Manager
        self.camera_manager = CameraManager()
        self.camera_manager.add_camera_clicked.connect(self.add_camera_clicked.emit)
        self.camera_manager.delete_camera_clicked.connect(self.delete_camera_clicked.emit)
        h_layout.addWidget(self.camera_manager, 0)

        # 2. Center Panel (Video Grid & bottom actions)
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(12)

        self.video_grid = VideoGridWidget()
        center_layout.addWidget(self.video_grid, 1)

        # Grid Control Actions (Bottom Bar)
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_scan = QPushButton("📡 SCAN NETWORK (PLUG & PLAY)")
        self.btn_scan.setObjectName("primaryButton")
        self.btn_scan.setMinimumHeight(40)
        self.btn_scan.setCursor(Qt.PointingHandCursor)
        self.btn_scan.clicked.connect(self.scan_network_clicked.emit)
        
        self.btn_pause_ai = QPushButton("⏸️ PAUSE AI PIPELINE")
        self.btn_pause_ai.setMinimumHeight(40)
        self.btn_pause_ai.setCheckable(True)
        self.btn_pause_ai.setCursor(Qt.PointingHandCursor)
        self.btn_pause_ai.clicked.connect(self._toggle_ai_state)
        
        self.btn_snapshot = QPushButton("📸 TAKE SNAPSHOT")
        self.btn_snapshot.setMinimumHeight(40)
        self.btn_snapshot.setObjectName("primaryButton")
        self.btn_snapshot.setCursor(Qt.PointingHandCursor)
        self.btn_snapshot.clicked.connect(self._on_snapshot_clicked)
        
        controls_layout.addWidget(self.btn_scan)
        controls_layout.addWidget(self.btn_pause_ai)
        controls_layout.addWidget(self.btn_snapshot)
        
        center_layout.addLayout(controls_layout)
        h_layout.addWidget(center_container, 1) # Center grid spans to take space

        # 3. Right Panel: Detection Alert Log Feed
        self.event_feed = EventFeedWidget()
        h_layout.addWidget(self.event_feed, 0)

    def _toggle_ai_state(self):
        self.ai_paused = self.btn_pause_ai.isChecked()
        if self.ai_paused:
            self.btn_pause_ai.setText("▶️ RESUME AI PIPELINE")
            self.btn_pause_ai.setObjectName("successButton")
        else:
            self.btn_pause_ai.setText("⏸️ PAUSE AI PIPELINE")
            self.btn_pause_ai.setObjectName("")
            
        self.btn_pause_ai.style().polish(self.btn_pause_ai)
        self.pause_ai_clicked.emit(self.ai_paused)

    def _on_snapshot_clicked(self):
        if self.active_camera_id is None:
            QMessageBox.warning(self, "No Camera Selected", "Please select a camera feed in the grid first.")
            return
        self.take_snapshot_clicked.emit(self.active_camera_id)

    def select_camera(self, camera_id: int):
        if self.active_camera_id in self.video_grid.widgets:
            self.video_grid.widgets[self.active_camera_id].set_selected(False)
            
        self.active_camera_id = camera_id
        if camera_id in self.video_grid.widgets:
            self.video_grid.widgets[camera_id].set_selected(True)
            self.video_grid.active_camera_id = camera_id

    def update_camera_grid(self, cameras: list):
        self.video_grid.update_grid(cameras, self.select_camera)
        
        # Keep active selection aligned
        if cameras:
            if self.active_camera_id not in self.video_grid.widgets:
                self.select_camera(cameras[0]["id"])
            else:
                self.select_camera(self.active_camera_id)
        else:
            self.active_camera_id = None

    def refresh_camera_list(self, cameras: list):
        self.camera_manager.refresh_camera_list(cameras)
            
    def update_frame(self, camera_id: int, qimage):
        if camera_id in self.video_grid.widgets:
            self.video_grid.widgets[camera_id].set_frame(qimage)
            
    def update_detections(self, camera_id: int, detections: list, latency_ms: float):
        if camera_id in self.video_grid.widgets:
            self.video_grid.widgets[camera_id].set_detections(detections, latency_ms)
            
    def update_status(self, camera_id: int, connected: bool):
        if camera_id in self.video_grid.widgets:
            self.video_grid.widgets[camera_id].set_connection_status(connected)

    def update_vlm_text(self, camera_id: int, text: str, is_alert: bool):
        if camera_id in self.video_grid.widgets:
            self.video_grid.widgets[camera_id].set_vlm_response(text, is_alert)
