import os
import time
import queue
import cv2
import numpy as np
from datetime import datetime
from PySide6.QtCore import QThread, Signal, Slot
from db import sqlite_db
from utils import config
from utils.notifications import send_telegram_alert
from services.vlm_service import VLMService

class CloudVLMWorker(QThread):
    # Signals
    vlm_response_received = Signal(str, str, bool)  # camera_id, analysis_text, is_alert
    api_error_occurred = Signal(str)
    incident_triggered = Signal(dict)
    event_triggered = Signal(dict)
    vlm_latency_updated = Signal(float)
    vlm_analysis_complete = Signal(str, str, str, str, np.ndarray, list, str)  # cam_name, timestamp, threat_level, summary, frame, detections, details

    def __init__(self):
        super().__init__()
        self.task_queue = queue.Queue(maxsize=10)
        self.running = True
        self.vlm_service = VLMService()
        
        # Ensure incidents directory exists
        self.incidents_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "incidents"
        )
        os.makedirs(self.incidents_dir, exist_ok=True)

    def run(self):
        print("[CloudVLMWorker] Starting Cloud VLM reasoning thread...")
        while self.running:
            try:
                # Non-blocking get with timeout
                camera_id, camera_name, detections, frame, three_frame_buffer = self.task_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            # 1. Check budget limit
            max_calls = config.get_max_daily_api_calls()
            current_calls = config.get_daily_usage()
            if current_calls >= max_calls:
                print(f"[CloudVLMWorker] Daily Budget Reached ({current_calls}/{max_calls}). Request dropped.")
                self.api_error_occurred.emit("Daily Budget Reached")
                self.task_queue.task_done()
                continue

            # 2. Retrieve active rules
            try:
                active_rules = sqlite_db.get_rules_by_camera(camera_id)
                active_rules = [r for r in active_rules if r["active"] == 1]
            except Exception as e:
                print(f"[CloudVLMWorker] Error reading rules from SQLite: {e}")
                active_rules = []

            t_start = time.time()

            # 3. Call VLM API Service
            try:
                res = self.vlm_service.analyze_frame(frame, active_rules)
                threat_level = res.get("threat_level", "LOW").strip().upper()
                summary = res.get("summary", "No assessment summary.")
                details = res.get("details", "No details returned.")
                analysis_text = f"[{threat_level}] {summary} - {details}"
                bool_is_alert = threat_level in ["MEDIUM", "HIGH"]
            except Exception as e:
                err_msg = f"VLM Analysis Failed: {e}"
                print(f"[CloudVLMWorker] {err_msg}")
                self.api_error_occurred.emit(err_msg)
                self.task_queue.task_done()
                continue

            # Increment daily usage
            config.increment_daily_usage()

            # 4. Save snapshots & 3-frame buffer
            try:
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                snapshot_name = f"cloud_snap_{timestamp_str}_cam{camera_id}.jpg"
                snapshot_path = os.path.join(self.incidents_dir, snapshot_name)

                # Draw bounding boxes on primary frame for saving
                saved_frame = frame.copy()
                for det in detections:
                    box = det["box"]
                    cv2.rectangle(saved_frame, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), 2)
                    cv2.putText(saved_frame, f"{det['label']} {det['confidence']:.2f}", 
                                (box[0], box[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                
                # Write primary snapshot
                cv2.imwrite(snapshot_path, saved_frame)

                # Write before / after snapshots if they exist
                before_path = snapshot_path.replace(".jpg", "_before.jpg")
                after_path = snapshot_path.replace(".jpg", "_after.jpg")
                if len(three_frame_buffer) > 0 and three_frame_buffer[0] is not None:
                    cv2.imwrite(before_path, three_frame_buffer[0])
                if len(three_frame_buffer) > 2 and three_frame_buffer[2] is not None:
                    cv2.imwrite(after_path, three_frame_buffer[2])

                # Log incident to SQLite DB
                alert_val = 1 if bool_is_alert else 0
                incident_id = sqlite_db.log_incident(
                    camera_id=camera_id,
                    camera_name=camera_name,
                    snapshot_path=snapshot_path,
                    explanation=analysis_text,
                    alert=alert_val
                )

                # Create package for trigger signals
                rule_text_str = ", ".join([r["rule_text"] for r in active_rules]) if active_rules else "YOLO Target Class Detection Event"
                incident_data = {
                    "id": incident_id,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "snapshot_path": snapshot_path,
                    "explanation": analysis_text,
                    "rule_text": rule_text_str,
                    "confidence": 1.0,
                    "false_positive": 0,
                    "threat_level": threat_level,
                    "summary": summary,
                    "details": details,
                    "detections": detections
                }

                # If alert, dispatch Telegram and trigger events
                if bool_is_alert:
                    # Dispatch telegram alert
                    tg_token = config.get_api_key("telegram_bot_token")
                    tg_chat = config.get_telegram_chat_id()
                    
                    telegram_msg = (
                        f"🚨 <b>Vision.IO Alert Triggered</b> 🚨\n\n"
                        f"<b>Camera:</b> {camera_name}\n"
                        f"<b>VLM Analysis:</b> {analysis_text}\n"
                        f"<b>Threat Level:</b> {threat_level}"
                    )
                    send_telegram_alert(tg_token, tg_chat, telegram_msg, snapshot_path)
                    
                    # Emit incident trigger
                    self.incident_triggered.emit(incident_data)

                # Emit event_triggered for ALL events (real-time Event Feed sidebar)
                self.event_triggered.emit(incident_data)
                
                # Emit detailed analysis complete signal directly for EventFeed integration
                self.vlm_analysis_complete.emit(
                    camera_name,
                    incident_data["timestamp"],
                    threat_level,
                    summary,
                    frame,
                    detections,
                    details
                )

            except Exception as e:
                print(f"[CloudVLMWorker] Error writing files / saving incident: {e}")

            # Emit VLM response signal
            self.vlm_response_received.emit(str(camera_id), analysis_text, bool_is_alert)

            # Emit latency update
            latency_ms = (time.time() - t_start) * 1000.0
            self.vlm_latency_updated.emit(latency_ms)

            self.task_queue.task_done()

        print("[CloudVLMWorker] Thread stopped.")

    @Slot(int, str, list, np.ndarray, list)
    def enqueue_vlm_task(self, camera_id: int, camera_name: str, detections: list, frame: np.ndarray, three_frame_buffer: list):
        """Pushes a candidate frame + detections + 3-frame buffer into the VLM analysis queue."""
        if not self.running:
            return
            
        try:
            self.task_queue.put_nowait((camera_id, camera_name, detections, frame, three_frame_buffer))
        except queue.Full:
            pass

    def stop(self):
        self.running = False
        self.wait()
