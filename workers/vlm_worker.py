import os
import time
import queue
import cv2
import numpy as np
from datetime import datetime
from PySide6.QtCore import QThread, Signal, Slot
from ai.vlm_engine import VLMEngine
from db import sqlite_db
from utils.notifications import send_telegram_alert

class VLMReasoningWorker(QThread):
    # Signals
    incident_triggered = Signal(dict)
    vlm_latency_updated = Signal(float)
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.task_queue = queue.Queue(maxsize=10)
        self.running = True
        self.engine = VLMEngine()
        
        self.telegram_token = ""
        self.telegram_chat_id = ""

        # Ensure incidents directory exists
        self.incidents_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "incidents"
        )
        os.makedirs(self.incidents_dir, exist_ok=True)

    def run(self):
        print("[VLMReasoningWorker] Starting VLM reasoning thread...")
        while self.running:
            try:
                camera_id, camera_name, detections, frame = self.task_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                active_rules = sqlite_db.get_rules_by_camera(camera_id)
                active_rules = [r for r in active_rules if r["active"] == 1]
            except Exception as e:
                print(f"[VLMReasoningWorker] Error reading rules from SQLite: {e}")
                active_rules = []

            if not active_rules or not detections:
                self.task_queue.task_done()
                continue

            t_start = time.time()
            
            for rule in active_rules:
                rule_text = rule["rule_text"]
                try:
                    result = self.engine.analyze_frame(frame, rule_text, detections)
                    
                    if result.get("alert", False):
                        # Save frame snapshot
                        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                        snapshot_name = f"snapshot_{timestamp_str}_cam{camera_id}_rule{rule['id']}.jpg"
                        snapshot_path = os.path.join(self.incidents_dir, snapshot_name)
                        
                        # Draw bounding boxes on the saved snapshot
                        saved_frame = frame.copy()
                        for det in detections:
                            box = det["box"]
                            cv2.rectangle(saved_frame, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), 2)
                            cv2.putText(saved_frame, f"{det['label']} {det['confidence']:.2f}", 
                                        (box[0], box[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

                        cv2.imwrite(snapshot_path, saved_frame)
                        
                        # Log to database
                        incident_id = sqlite_db.log_incident(
                            camera_id=camera_id,
                            camera_name=camera_name,
                            snapshot_path=snapshot_path,
                            explanation=result.get("explanation", ""),
                            alert=1
                        )
                        
                        # Pack incident data
                        incident_data = {
                            "id": incident_id,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "camera_id": camera_id,
                            "camera_name": camera_name,
                            "snapshot_path": snapshot_path,
                            "explanation": result.get("explanation", ""),
                            "rule_text": rule_text,
                            "confidence": result.get("confidence", 0.0),
                            "false_positive": 0
                        }
                        
                        # Dispatch telegram alert
                        telegram_msg = (
                            f"🚨 <b>Vision.IO Alert Triggered</b> 🚨\n\n"
                            f"<b>Camera:</b> {camera_name}\n"
                            f"<b>Rule:</b> {rule_text}\n"
                            f"<b>VLM Narrative:</b> {result.get('explanation')}\n"
                            f"<b>Confidence:</b> {result.get('confidence') * 100:.1f}%"
                        )
                        
                        send_telegram_alert(self.telegram_token, self.telegram_chat_id, telegram_msg, snapshot_path)
                        
                        # Emit incident signal
                        self.incident_triggered.emit(incident_data)
                        
                except Exception as e:
                    print(f"[VLMReasoningWorker] Error evaluating rule {rule['id']}: {e}")
                    self.error_occurred.emit(str(e))

            latency_ms = (time.time() - t_start) * 1000.0
            self.vlm_latency_updated.emit(latency_ms)
            self.task_queue.task_done()

        print("[VLMReasoningWorker] Thread stopped.")

    @Slot(int, str, list, np.ndarray)
    def enqueue_vlm_task(self, camera_id: int, camera_name: str, detections: list, frame: np.ndarray):
        """Pushes a candidate frame + detections into the VLM analysis queue."""
        if not self.running:
            return
            
        try:
            self.task_queue.put_nowait((camera_id, camera_name, detections, frame))
        except queue.Full:
            pass

    def stop(self):
        self.running = False
        self.wait()
        
    def configure_telegram(self, token: str, chat_id: str):
        self.telegram_token = token
        self.telegram_chat_id = chat_id
