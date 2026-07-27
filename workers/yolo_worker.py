import time
import queue
import numpy as np
from PySide6.QtCore import QThread, Signal, Slot
from ai.yolo_engine import YOLOEngine

class YOLOInferenceWorker(QThread):
    # Signals
    # camera_id, camera_name, detections, frame, latency_ms
    detection_results = Signal(int, str, list, np.ndarray, float)
    # camera_id, camera_name, detections, frame_detection, three_frame_buffer
    detection_event = Signal(int, str, list, np.ndarray, list)
    error_occurred = Signal(str)

    TARGET_CLASSES = {"person", "car", "dog", "backpack", "suitcase", "handbag", "package"}

    def __init__(self):
        super().__init__()
        self.frame_queue = queue.Queue(maxsize=5)  # Drop frames if pipeline gets clogged
        self.running = True
        self.engine = None
        
        # State tracking per camera
        self.camera_histories = {}    # camera_id -> last_frame (np.ndarray)
        self.consecutive_counts = {}  # camera_id -> dict(class_label -> count)
        self.last_trigger_times = {}  # camera_id -> float (timestamp)
        self.pending_events = {}      # camera_id -> dict (event info waiting for frame_after)

    def run(self):
        print("[YOLOInferenceWorker] Starting detection thread...")
        try:
            self.engine = YOLOEngine()
        except Exception as e:
            self.error_occurred.emit(f"Failed to initialize YOLO engine: {e}")
            return

        while self.running:
            try:
                # Retrieve next frame block, timeout to allow check of self.running
                camera_id, camera_name, frame = self.frame_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            t_start = time.time()
            try:
                # 1. Complete any pending detection event for this camera (1s after)
                if camera_id in self.pending_events:
                    pending = self.pending_events.pop(camera_id)
                    frame_before = pending["frame_before"]
                    frame_detection = pending["frame_detection"]
                    frame_after = frame.copy()
                    
                    three_frame_buffer = [frame_before, frame_detection, frame_after]
                    # Emit Detection Event with 3-frame buffer
                    self.detection_event.emit(
                        camera_id, 
                        pending["camera_name"], 
                        pending["detections"], 
                        frame_detection, 
                        three_frame_buffer
                    )

                # 2. Run detection on current frame
                detections = self.engine.detect(frame)
                latency_ms = (time.time() - t_start) * 1000.0

                # 3. Track target classes and consecutive detections
                # Get all target classes detected in this frame with conf > 0.5
                detected_targets = set()
                for det in detections:
                    label = det.get("label", "").lower()
                    conf = det.get("confidence", 0.0)
                    if label in self.TARGET_CLASSES and conf > 0.5:
                        detected_targets.add(label)

                # Initialize state dicts for this camera if not exists
                if camera_id not in self.consecutive_counts:
                    self.consecutive_counts[camera_id] = {cls: 0 for cls in self.TARGET_CLASSES}

                # Update consecutive counts
                trigger_detected = False
                for cls in self.TARGET_CLASSES:
                    if cls in detected_targets:
                        self.consecutive_counts[camera_id][cls] += 1
                        # If detected for > 3 consecutive frames (reaches 4 frames)
                        if self.consecutive_counts[camera_id][cls] >= 4:
                            trigger_detected = True
                    else:
                        self.consecutive_counts[camera_id][cls] = 0

                # 4. Check Cooldown and trigger event if needed
                if trigger_detected:
                    now = time.time()
                    last_trigger = self.last_trigger_times.get(camera_id, 0.0)
                    if now - last_trigger >= 30.0:
                        # Cooldown passed, initiate detection event
                        self.last_trigger_times[camera_id] = now
                        
                        # Get frame before (1s before)
                        frame_before = self.camera_histories.get(camera_id)
                        if frame_before is None:
                            frame_before = frame.copy()
                        
                        # Store pending event to capture the "after" frame on the next cycle
                        self.pending_events[camera_id] = {
                            "camera_name": camera_name,
                            "detections": [d for d in detections if d.get("label", "").lower() in self.TARGET_CLASSES and d.get("confidence", 0.0) > 0.5],
                            "frame_before": frame_before.copy(),
                            "frame_detection": frame.copy()
                        }
                        
                        # Reset consecutive counts to avoid immediate double trigger
                        self.consecutive_counts[camera_id] = {cls: 0 for cls in self.TARGET_CLASSES}

                # Save current frame as history (1s before for the next frame)
                self.camera_histories[camera_id] = frame.copy()

                # Emit regular results back to UI for bounding box painting
                self.detection_results.emit(camera_id, camera_name, detections, frame, latency_ms)
            except Exception as e:
                print(f"[YOLOInferenceWorker] Error processing frame from cam {camera_id}: {e}")
                self.error_occurred.emit(str(e))
            finally:
                self.frame_queue.task_done()

        print("[YOLOInferenceWorker] Thread stopped.")

    @Slot(int, str, np.ndarray)
    def enqueue_frame(self, camera_id: int, camera_name: str, frame: np.ndarray):
        """Receives a frame from a CameraWorker and pushes it into the queue."""
        if not self.running:
            return
            
        try:
            # Non-blocking put; if queue is full, discard the frame to avoid lag
            self.frame_queue.put_nowait((camera_id, camera_name, frame))
        except queue.Full:
            # Queue is full, drop frame
            pass

    def stop(self):
        self.running = False
        self.wait()
