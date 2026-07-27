import os
import numpy as np
from PySide6.QtCore import Qt, Signal, Slot, QThread, QUrl
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QHBoxLayout, QWidget, 
    QMessageBox, QProgressDialog, QSystemTrayIcon, QStyle,
    QFileDialog, QPushButton, QLabel
)
from PySide6.QtGui import QIcon

from db import sqlite_db
from utils import discovery
from workers.camera_worker import CameraWorker
from workers.yolo_worker import YOLOInferenceWorker
from workers.cloud_vlm_worker import CloudVLMWorker
from workers.vector_worker import VectorIndexingWorker
from services.alert_dispatcher import AlertDispatcher

# Background Scanner Worker Thread
class CameraScanWorker(QThread):
    scan_finished = Signal(list)

    def run(self):
        print("[CameraScanWorker] Initiating Plug-and-Play Discovery Scan...")
        usb_cams = discovery.discover_usb_cameras()
        onvif_cams = discovery.discover_onvif_cameras()
        all_discovered = usb_cams + onvif_cams
        self.scan_finished.emit(all_discovered)


# Background thread cleanup worker to prevent main thread blocking
class ThreadCleanupWorker(QThread):
    cleanup_finished = Signal(int)

    def __init__(self, camera_id: int, worker: QThread):
        super().__init__()
        self.camera_id = camera_id
        self.worker = worker

    def run(self):
        print(f"[ThreadCleanupWorker] Stopping camera worker {self.camera_id}...")
        self.worker.stop()
        print(f"[ThreadCleanupWorker] Waiting for camera worker {self.camera_id} to exit...")
        self.worker.wait()
        print(f"[ThreadCleanupWorker] Camera worker {self.camera_id} stopped successfully.")
        self.cleanup_finished.emit(self.camera_id)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vision.IO Desktop - Security Operations Center")
        self.resize(1024, 768)
        
        # Initialize thread containers
        self.camera_workers = {}
        self.yolo_worker = None
        self.vlm_worker = None
        self.vector_worker = None
        self.scan_worker = None

        # Load style QSS
        self.load_stylesheet()

        # Build UI layout
        self.init_ui()
        
        # Initialize System Tray
        self.setup_system_tray()

        # Start AI backend engine threads
        self.start_ai_backend()

        # Load camera streams
        self.initialize_camera_streams()

    def load_stylesheet(self):
        qss_path = os.path.join(os.path.dirname(__file__), "style.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r") as f:
                self.setStyleSheet(f.read())
        else:
            print("[MainWindow] Warning: style.qss not found.")

    def init_ui(self):
        # Master central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Top Bar Widget
        from ui.top_bar import TopBar
        self.top_bar = TopBar(self)
        self.top_bar.settings_clicked.connect(self._open_settings_dialog)
        main_layout.addWidget(self.top_bar)
        
        # 2. Main Content Horizontal Layout
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Left side: Tabs
        self.tabs = QTabWidget()
        content_layout.addWidget(self.tabs, 1)
        
        # Right side: EventFeed sidebar widget
        from ui.event_feed import EventFeed
        self.event_feed = EventFeed()
        self.event_feed.setMinimumWidth(320)
        self.event_feed.setMaximumWidth(380)
        self.event_feed.setObjectName("cardFrame")
        content_layout.addWidget(self.event_feed)
        
        main_layout.addLayout(content_layout)

        from ui.live_monitoring import LiveMonitoringTab
        from ui.rule_builder import RuleBuilderTab
        from ui.semantic_search import SemanticSearchTab
        from ui.incident_log import IncidentLogTab
        from ui.tabs.settings_tab import SettingsTab

        self.tab_live = LiveMonitoringTab()
        self.tab_rules = RuleBuilderTab()
        self.tab_search = SemanticSearchTab()
        self.tab_incidents = IncidentLogTab()
        self.tab_settings = SettingsTab()

        self.tabs.addTab(self.tab_live, "📺 Live Feeds Grid")
        self.tabs.addTab(self.tab_rules, "🛡️ Rule Builder")
        self.tabs.addTab(self.tab_search, "🔍 Semantic Search")
        self.tabs.addTab(self.tab_incidents, "📊 Incidents & Metrics")
        self.tabs.addTab(self.tab_settings, "⚙️ Settings")

        # Connect UI Action Signals
        self.tab_live.scan_network_clicked.connect(self._on_scan_network)
        self.tab_live.pause_ai_clicked.connect(self._on_pause_ai)
        self.tab_live.take_snapshot_clicked.connect(self._on_take_manual_snapshot)
        self.tab_live.add_camera_clicked.connect(self._on_add_camera)
        self.tab_live.delete_camera_clicked.connect(self._on_delete_camera)
        
        self.tab_rules.rules_updated.connect(self._on_rules_updated)
        self.tab_search.search_triggered.connect(self._on_search_query)

    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self.tray_icon.setToolTip("Vision.IO Edge Surveillance")
        self.tray_icon.show()

    def start_ai_backend(self):
        """Starts heavy YOLO inference, VLM reasoning, and Vector DB worker threads."""
        self.yolo_worker = YOLOInferenceWorker()
        self.vlm_worker = CloudVLMWorker()
        self.vector_worker = VectorIndexingWorker()
        self.alert_dispatcher = AlertDispatcher()
 
        # Connect YOLO
        self.yolo_worker.detection_results.connect(self._on_yolo_detection_ready)
        self.yolo_worker.detection_results.connect(
            lambda cid, name, dets, frame, lat: self.tab_incidents.append_yolo_latency(lat)
        )
        self.yolo_worker.detection_event.connect(self._on_yolo_detection_event)
 
        # Configure VLM
        self.vlm_worker.vlm_latency_updated.connect(self.tab_incidents.append_vlm_latency)
        self.vlm_worker.incident_triggered.connect(lambda inc: self.tab_incidents.refresh_log())
        self.vlm_worker.incident_triggered.connect(self._on_incident_trigger_vector_index)
        self.vlm_worker.incident_triggered.connect(self._on_incident_show_tray)
        self.vlm_worker.vlm_response_received.connect(self._on_vlm_response_received)
        self.vlm_worker.event_triggered.connect(self.tab_live.event_feed.add_event)
        self.vlm_worker.vlm_analysis_complete.connect(self._on_vlm_analysis_complete)
        self.vlm_worker.api_error_occurred.connect(self._on_api_error_occurred)
 
        # Connect Vector Search
        self.vector_worker.search_results.connect(self.tab_search.display_results)
 
        # Launch threads
        self.yolo_worker.start()
        self.vlm_worker.start()
        self.vector_worker.start()
        self.alert_dispatcher.start()

    def initialize_camera_streams(self):
        """Fetches active camera profiles and launches capture worker threads."""
        self.stop_camera_workers()

        cameras = sqlite_db.get_all_cameras()
        self.tab_live.update_camera_grid(cameras)
        self.tab_live.refresh_camera_list(cameras)
        
        self.tab_rules.refresh_data()

        for cam in cameras:
            self.add_camera_stream(cam)

        self.top_bar.set_streams_count(len(self.camera_workers), len(cameras))
        self.top_bar.set_engine_status("GEMINI FLASH")

    def add_camera_stream(self, cam):
        cam_id = cam["id"]
        if cam_id in self.camera_workers:
            return
            
        yolo_queue = self.yolo_worker.frame_queue if self.yolo_worker else None
        worker = CameraWorker(cam_id, cam["name"], cam["url"], cam["type"], yolo_queue)
        
        worker.frame_processed.connect(
            lambda img, cid=cam_id: self.tab_live.update_frame(cid, img)
        )
        worker.connection_status_changed.connect(
            lambda cid, state: self.tab_live.update_status(cid, state)
        )
        worker.vlm_trigger_required.connect(
            lambda frame, classes, cid=cam_id, name=cam["name"]: self._on_vlm_trigger_required(cid, name, frame, classes)
        )
        worker.yolo_latency_updated.connect(
            lambda cid, lat: self._on_yolo_latency_updated(cid, lat)
        )
        
        # Set initial pause state
        worker.set_ai_paused(self.tab_live.ai_paused)
            
        self.camera_workers[cam_id] = worker
        worker.start()
        
        cameras = sqlite_db.get_all_cameras()
        self.top_bar.set_streams_count(len(self.camera_workers), len(cameras))

    def remove_camera_stream(self, cam_id):
        if cam_id not in self.camera_workers:
            return
            
        worker = self.camera_workers.pop(cam_id)
        
        cameras = sqlite_db.get_all_cameras()
        self.top_bar.set_streams_count(len(self.camera_workers), len(cameras))
        
        # Disconnect signals to prevent updates during teardown
        try:
            worker.frame_processed.disconnect()
            worker.connection_status_changed.disconnect()
            worker.vlm_trigger_required.disconnect()
            worker.yolo_latency_updated.disconnect()
        except Exception:
            pass
            
        # Start cleanup in the background
        cleanup_worker = ThreadCleanupWorker(cam_id, worker)
        cleanup_worker.cleanup_finished.connect(self._on_cleanup_finished)
        
        if not hasattr(self, "_cleanup_workers"):
            self._cleanup_workers = []
        self._cleanup_workers.append(cleanup_worker)
        cleanup_worker.start()

    @Slot(int)
    def _on_cleanup_finished(self, cam_id):
        sender = self.sender()
        if sender and hasattr(self, "_cleanup_workers") and sender in self._cleanup_workers:
            self._cleanup_workers.remove(sender)
            sender.deleteLater()
        print(f"[MainWindow] Asynchronous cleanup complete for camera {cam_id}.")

    @Slot(str, str)
    def _on_add_camera(self, name: str, url: str):
        # Enforce MAX_CAMERA_LIMIT (default: 4 cameras)
        cameras = sqlite_db.get_all_cameras()
        if len(cameras) >= 4:
            QMessageBox.warning(self, "Camera Limit", "Maximum limit of 4 cameras has been reached.")
            return
            
        # Deduce camera type
        cam_type = "RTSP" if url.startswith("rtsp://") or url.startswith("rtmp://") or url.startswith("http://") or url.startswith("https://") else "USB"
        if url.isdigit():
            cam_type = "USB"
            
        # Insert to database
        cam_id = sqlite_db.add_camera(name, url, cam_type)
        
        # Reload and start the stream
        cameras = sqlite_db.get_all_cameras()
        new_cam = next((c for c in cameras if c["id"] == cam_id), None)
        if new_cam:
            self.add_camera_stream(new_cam)
            
        # Refresh grid and list
        self.tab_live.update_camera_grid(cameras)
        self.tab_live.refresh_camera_list(cameras)
        
        # Refresh rule builder drop-down list
        self.tab_rules.refresh_data()

    @Slot(int)
    def _on_delete_camera(self, camera_id: int):
        # Stop stream asynchronously
        self.remove_camera_stream(camera_id)
        
        # Delete from database
        sqlite_db.delete_camera(camera_id)
        
        # Refresh grid and list
        cameras = sqlite_db.get_all_cameras()
        self.tab_live.update_camera_grid(cameras)
        self.tab_live.refresh_camera_list(cameras)
        
        # Refresh rule builder drop-down list
        self.tab_rules.refresh_data()

    def stop_camera_workers(self):
        for worker in self.camera_workers.values():
            worker.stop()
        self.camera_workers.clear()

    # --- Worker Route Proxies & Signal Slots ---

    @Slot(int, str, np.ndarray, list)
    def _on_vlm_trigger_required(self, camera_id, camera_name, frame_bgr, classes):
        print(f"[MainWindow] VLM trigger required for {camera_name} (ID: {camera_id}) (classes: {classes})")
        if self.vlm_worker and classes:
            # Map classes to detection dictionaries format for VLM worker
            detections = [
                {
                    "class_id": 0,
                    "label": cls,
                    "confidence": 1.0,
                    "box": (0, 0, frame_bgr.shape[1], frame_bgr.shape[0])
                }
                for cls in classes
            ]
            three_frame_buffer = [frame_bgr.copy(), frame_bgr.copy(), frame_bgr.copy()]
            self.vlm_worker.enqueue_vlm_task(camera_id, camera_name, detections, frame_bgr, three_frame_buffer)

    @Slot(int, float)
    def _on_yolo_latency_updated(self, camera_id, latency_ms):
        self.tab_live.update_detections(camera_id, [], latency_ms)
        self.tab_incidents.append_yolo_latency(latency_ms)
        
        fps = 1000.0 / latency_ms if latency_ms > 0 else 0.0
        self.top_bar.set_edge_fps(fps)

    @Slot(int, str, list, object, float)
    def _on_yolo_detection_ready(self, camera_id, camera_name, detections, frame, latency_ms):
        self.tab_live.update_detections(camera_id, detections, latency_ms)

    @Slot(int, str, list, object, float)
    def vlm_worker_enqueue_proxy(self, camera_id, camera_name, detections, frame, latency_ms):
        if self.vlm_worker and detections:
            # Wire to trigger only when motion/bounding boxes meet confidence thresholds (>= 0.50)
            high_conf_dets = [d for d in detections if d.get("confidence", 0.0) >= 0.50]
            if high_conf_dets:
                self.vlm_worker.enqueue_vlm_task(camera_id, camera_name, high_conf_dets, frame, [])

    @Slot(int, str, list, object, list)
    def _on_yolo_detection_event(self, camera_id, camera_name, detections, frame, three_frame_buffer):
        if self.vlm_worker and detections:
            self.vlm_worker.enqueue_vlm_task(camera_id, camera_name, detections, frame, three_frame_buffer)

    @Slot(str, str, bool)
    def _on_vlm_response_received(self, camera_id_str, analysis_text, is_alert):
        camera_id = int(camera_id_str)
        # Update the Live Camera Grid OSD with alert text
        self.tab_live.update_vlm_text(camera_id, analysis_text, is_alert)
        # Append narrative logs to the Incident Tab QListWidget (refreshes logs)
        self.tab_incidents.refresh_log()

    @Slot(str, str, str, str, np.ndarray, list, str)
    def _on_vlm_analysis_complete(self, cam_name, timestamp, threat_level, summary, frame, detections, details):
        # Update UI event feed
        self.event_feed.add_event(cam_name, timestamp, threat_level, summary, frame, detections)

        # Handle async high threat alert dispatching
        if threat_level == "HIGH":
            vlm_dict = {
                "threat_level": threat_level,
                "summary": summary,
                "details": details
            }
            if hasattr(self, "alert_dispatcher") and self.alert_dispatcher:
                self.alert_dispatcher.dispatch_high_threat(cam_name, timestamp, frame, vlm_dict)

    @Slot()
    def _open_settings_dialog(self):
        from ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.exec()

    @Slot(str)
    def _on_api_error_occurred(self, error_msg):
        print(f"[MainWindow] Cloud VLM API Error occurred: {error_msg}")

    @Slot(dict)
    def _on_incident_trigger_vector_index(self, incident: dict):
        if self.vector_worker:
            self.vector_worker.enqueue_index_task(
                incident["id"],
                incident["snapshot_path"],
                incident["explanation"]
            )

    @Slot(dict)
    def _on_incident_show_tray(self, incident: dict):
        title = f"🚨 SECURITY ALERT - {incident['camera_name']}"
        body = f"Rule violation: {incident['explanation']}"
        self.tray_icon.showMessage(
            title, body, QSystemTrayIcon.Warning, 8000
        )

    # --- Action Slot Triggers ---

    @Slot()
    def _on_scan_network(self):
        self.progress_dialog = QProgressDialog("Scanning LAN & Video Ports for cameras...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowTitle("Discovery Scanning")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()

        self.scan_worker = CameraScanWorker()
        self.scan_worker.scan_finished.connect(self._on_scan_completed)
        self.scan_worker.start()

    @Slot(list)
    def _on_scan_completed(self, discovered_cameras: list):
        self.progress_dialog.close()
        
        if not discovered_cameras:
            QMessageBox.information(self, "Scan Complete", "No active ONVIF or USB video cameras found on local networks.")
            return

        new_count = 0
        existing_urls = [c["url"] for c in sqlite_db.get_all_cameras()]
        
        for cam in discovered_cameras:
            if cam["url"] not in existing_urls:
                sqlite_db.add_camera(cam["name"], cam["url"], cam["type"])
                new_count += 1
                
        QMessageBox.information(
            self, "Scan Complete", 
            f"Network Discovery complete.\nDiscovered: {len(discovered_cameras)} device(s).\nAdded to SOC database: {new_count} new camera(s)."
        )
        
        if new_count > 0:
            self.initialize_camera_streams()

    @Slot(bool)
    def _on_pause_ai(self, paused: bool):
        print(f"[MainWindow] AI Pipeline execution paused state: {paused}")
        for worker in self.camera_workers.values():
            try:
                worker.set_ai_paused(paused)
            except Exception as e:
                print(f"[MainWindow] Error setting AI paused on camera worker: {e}")

    @Slot(int)
    def _on_take_manual_snapshot(self, camera_id: int):
        worker = self.camera_workers.get(camera_id)
        if not worker or worker.current_frame is None or worker.current_frame.isNull():
            QMessageBox.warning(self, "Snapshot Failed", "Cannot snapshot: Selected camera feed is currently offline.")
            return
            
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Snapshot", f"snapshot_cam{camera_id}.jpg", "Images (*.jpg)"
        )
        if save_path:
            success = worker.current_frame.save(save_path, "JPG", 95)
            if success:
                QMessageBox.information(self, "Success", f"Snapshot saved successfully to:\n{save_path}")
            else:
                QMessageBox.critical(self, "Error", "Failed to save file. Check directory permissions.")

    @Slot()
    def _on_rules_updated(self):
        print("[MainWindow] Dynamic VLM rules registry updated.")

    @Slot(str)
    def _on_search_query(self, query: str):
        if self.vector_worker:
            self.vector_worker.trigger_search(query)

    # --- Shutdown & Lifecycle ---

    def closeEvent(self, event):
        print("[MainWindow] Shutting down Operations Center pipeline...")
        
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.terminate()
            self.scan_worker.wait()
            
        self.stop_camera_workers()
        
        if self.yolo_worker:
            self.yolo_worker.stop()
            
        if self.vlm_worker:
            self.vlm_worker.stop()
            
        if self.vector_worker:
            self.vector_worker.stop()

        if hasattr(self, "alert_dispatcher") and self.alert_dispatcher:
            self.alert_dispatcher.stop()
 
        self.tray_icon.hide()
        event.accept()
