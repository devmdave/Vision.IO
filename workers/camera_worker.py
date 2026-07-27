import time
import queue
import threading
import numpy as np
import cv2
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
from services.yolo_detector import YoloDetector

class CameraWorker(QThread):
    # Signals
    frame_processed = Signal(QImage)  # Annotated frame for live rendering
    vlm_trigger_required = Signal(np.ndarray, list)     # frame_bgr, triggered_classes
    connection_status_changed = Signal(int, bool)       # camera_id, is_connected
    error_occurred = Signal(int, str)                   # camera_id, error_message
    yolo_latency_updated = Signal(int, float)           # camera_id, latency_ms

    def __init__(self, camera_id: int, camera_name: str, camera_url: str, camera_type: str, yolo_queue=None):
        super().__init__()
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.camera_url = camera_url
        self.camera_type = camera_type
        self.yolo_queue = yolo_queue  # Retained for legacy compatibility
        
        self.running = True
        self.paused = False
        self.ai_paused = False  # Track whether YOLO inference is paused
        
        # Thread-safe frame queue with maxsize=1 (drops old frames if inference lags)
        self.frame_queue = queue.Queue(maxsize=1)
        self.ingest_thread = None
        
        # Simulator state variables (used if live stream fails to open)
        self.sim_tick = 0
        self.sim_person_x = 50
        self.sim_person_y = 300
        self.sim_car_x = 800
        self.sim_car_y = 400
        self.sim_person_active = False
        self.sim_car_active = False

    def run(self):
        # Initialize YOLO11 detector inside the background thread
        print(f"[CameraWorker {self.camera_id}] Initializing YOLO11 detector in background QThread...")
        detector = YoloDetector()

        from services.event_tracker import EventTracker
        tracker = EventTracker(idle_threshold_frames=150)

        backoff = 1.0
        fps_target = 30.0
        frame_delay = 1.0 / fps_target

        print(f"[CameraWorker {self.camera_id}] Starting stream ingestion for: {self.camera_name} ({self.camera_url})")

        use_simulator = False
        cap = None

        # Check if URL is an integer (USB Camera index)
        try:
            device_index = int(self.camera_url)
            is_usb = True
        except ValueError:
            is_usb = False

        # Nested ingestion loop to run in a helper thread
        def ingest_loop():
            nonlocal cap, use_simulator, backoff
            while self.running:
                if self.paused:
                    time.sleep(0.1)
                    continue

                if not use_simulator:
                    # Attempt to open OpenCV capture if not already open
                    if cap is None or not cap.isOpened():
                        self.connection_status_changed.emit(self.camera_id, False)
                        if is_usb:
                            cap = cv2.VideoCapture(device_index)
                        else:
                            cap = cv2.VideoCapture(self.camera_url)
                        
                        if not cap.isOpened():
                            print(f"[CameraWorker {self.camera_id}] Failed to open stream. Retrying in {backoff:.1f}s...")
                            # If RTSP camera, fall back to simulator to prevent blank UI
                            if not is_usb:
                                print(f"[CameraWorker {self.camera_id}] Enabling stream simulator for RTSP.")
                                use_simulator = True
                            else:
                                time.sleep(backoff)
                                backoff = min(backoff * 2.0, 30.0)
                                continue
                        else:
                            # Reset backoff on successful connection
                            backoff = 1.0
                            self.connection_status_changed.emit(self.camera_id, True)

                # Read frame
                frame = None
                if use_simulator:
                    frame = self._generate_simulated_frame()
                    time.sleep(frame_delay)  # Limit frame rate
                else:
                    success, frame = cap.read()
                    if not success:
                        print(f"[CameraWorker {self.camera_id}] Read error. Triggering reconnect...")
                        if cap:
                            cap.release()
                        cap = None
                        if not is_usb:
                            use_simulator = True
                        else:
                            time.sleep(1.0)
                        continue

                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

                # Drop intermediate frames if queue backs up
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                
                try:
                    self.frame_queue.put_nowait((frame, timestamp))
                except queue.Full:
                    pass

        # Start ingestion helper thread
        self.ingest_thread = threading.Thread(target=ingest_loop, daemon=True)
        self.ingest_thread.start()

        # Processing loop in the main QThread (background thread)
        while self.running:
            try:
                frame, timestamp = self.frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                if self.ai_paused:
                    # Skip inference, convert raw BGR frame to RGB QImage and emit
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_frame.shape
                    bytes_per_line = ch * w
                    qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    self.frame_processed.emit(qimg.copy())
                    self.yolo_latency_updated.emit(self.camera_id, 0.0)
                    continue

                t_start = time.time()
                # Perform YOLO inference strictly in this background thread
                annotated_frame, detections = detector.process_frame(frame)
                latency_ms = (time.time() - t_start) * 1000.0
                
                # Emit latency for metric updates
                self.yolo_latency_updated.emit(self.camera_id, latency_ms)
                
                # Convert annotated BGR frame to RGB QImage for UI rendering
                rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # Emit fully annotated frame for UI rendering
                self.frame_processed.emit(qimg.copy())

                # Pass YOLO detection lists into EventTracker.update
                trigger, triggered_classes = tracker.update(detections)
                if trigger:
                    self.vlm_trigger_required.emit(frame.copy(), triggered_classes)
            except Exception as e:
                print(f"[CameraWorker {self.camera_id}] Processing error: {e}")
                self.error_occurred.emit(self.camera_id, str(e))

        # Cleanup
        self.running = False
        if self.ingest_thread:
            self.ingest_thread.join(timeout=1.0)
            
        if cap and cap.isOpened():
            cap.release()
        self.connection_status_changed.emit(self.camera_id, False)
        print(f"[CameraWorker {self.camera_id}] Thread stopped.")

    def stop(self):
        self.running = False
        self.wait()

    def set_paused(self, paused: bool):
        self.paused = paused

    def set_ai_paused(self, paused: bool):
        self.ai_paused = paused

    def _generate_simulated_frame(self) -> np.ndarray:
        """Generates a simulated camera feed frame."""
        # Create dark blue/grey background (640x480)
        h, w = 480, 640
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        
        # Color palette
        bg_grid_color = (25, 25, 25)
        text_color = (200, 200, 200)
        hud_accent = (0, 220, 0) if (self.camera_id % 2 == 0) else (220, 100, 0)
        
        # Draw grid pattern
        for y in range(0, h, 40):
            cv2.line(frame, (0, y), (w, y), bg_grid_color, 1)
        for x in range(0, w, 40):
            cv2.line(frame, (x, 0), (x, h), bg_grid_color, 1)
            
        # Draw crosshairs/HUD details
        cv2.circle(frame, (w // 2, h // 2), 60, (40, 40, 40), 1)
        cv2.line(frame, (w // 2 - 80, h // 2), (w // 2 + 80, h // 2), (40, 40, 40), 1)
        cv2.line(frame, (w // 2, h // 2 - 80), (w // 2, h // 2 + 80), (40, 40, 40), 1)
        
        # Simulate target motion
        self.sim_tick += 1
        
        # Periodically spawn a simulated person walking (every 400 ticks, lasting 150 ticks)
        if self.sim_tick % 400 == 0:
            self.sim_person_active = True
            self.sim_person_x = 50
            self.sim_person_y = 200 + np.random.randint(-50, 50)
            
        # Periodically spawn a simulated car passing (every 600 ticks, lasting 200 ticks)
        if self.sim_tick % 600 == 200:
            self.sim_car_active = True
            self.sim_car_x = 600
            self.sim_car_y = 300 + np.random.randint(-30, 30)

        # Draw simulated targets (which our YOLO simulation will look for)
        if self.sim_person_active:
            # Draw a simulated "person" (circle and rectangle)
            self.sim_person_x += 2
            if self.sim_person_x > w:
                self.sim_person_active = False
            else:
                # Body
                cv2.rectangle(frame, (self.sim_person_x - 15, self.sim_person_y - 10), (self.sim_person_x + 15, self.sim_person_y + 40), (100, 100, 200), -1)
                # Head
                cv2.circle(frame, (self.sim_person_x, self.sim_person_y - 20), 12, (200, 170, 150), -1)
                # Text indicator (simulated tags)
                cv2.putText(frame, "SIMULATED PERSON", (self.sim_person_x - 40, self.sim_person_y - 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 255), 1)

        if self.sim_car_active:
            # Draw a simulated "car" (large rectangle)
            self.sim_car_x -= 3
            if self.sim_car_x < -100:
                self.sim_car_active = False
            else:
                cv2.rectangle(frame, (self.sim_car_x - 50, self.sim_car_y - 20), (self.sim_car_x + 50, self.sim_car_y + 20), (180, 100, 100), -1)
                # Wheels
                cv2.circle(frame, (self.sim_car_x - 30, self.sim_car_y + 20), 10, (30, 30, 30), -1)
                cv2.circle(frame, (self.sim_car_x + 30, self.sim_car_y + 20), 10, (30, 30, 30), -1)
                cv2.putText(frame, "SIMULATED VEHICLE", (self.sim_car_x - 50, self.sim_car_y - 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 255), 1)

        # Draw HUD text
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"FEED: {self.camera_name}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, hud_accent, 1)
        cv2.putText(frame, "SIMULATED LIVE STREAM", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
        cv2.putText(frame, timestamp, (w - 180, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.4, text_color, 1)
        
        return frame
