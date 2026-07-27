import cv2
import numpy as np

class YoloDetector:
    def __init__(self, model_path="yolo11n.pt"):
        self.model_path = model_path
        self.model = None
        self.is_mock = False
        
        # Map class IDs to COCO labels for targeted monitoring
        self.target_classes = {
            0: "person",
            2: "car",
            3: "motorcycle",
            7: "truck",
            16: "dog"
        }
        
        try:
            from ultralytics import YOLO
            print(f"[YoloDetector] Loading native Ultralytics YOLO11 ({self.model_path})...")
            # This loads the model weights and downloads if necessary
            self.model = YOLO(self.model_path)
            self.is_mock = False
            print("[YoloDetector] Native YOLO11 loaded successfully.")
        except Exception as e:
            print(f"[YoloDetector] Native YOLO11 initialization failed or unavailable: {e}")
            print("[YoloDetector] Defaulting to simulation mode with color/contour detection.")
            self.is_mock = True

    def process_frame(self, frame_bgr: np.ndarray) -> tuple[np.ndarray, list[dict]]:
        """
        Processes a BGR frame through the detection model.
        Returns:
            - The annotated frame (np.ndarray BGR).
            - A list of target detections (conf >= 0.5).
        """
        detections = []
        if frame_bgr is None:
            return frame_bgr, detections

        h, w, _ = frame_bgr.shape

        if not self.is_mock and self.model is not None:
            try:
                # Run native YOLO11 inference
                # classes filter passes only targeted indices to optimize performance
                results = self.model(frame_bgr, classes=list(self.target_classes.keys()), verbose=False)
                if results and len(results) > 0:
                    result = results[0]
                    boxes = result.boxes
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        
                        # Apply confidence threshold >= 0.5
                        if conf >= 0.5:
                            xyxy = box.xyxy[0].tolist()
                            label = self.target_classes.get(cls_id, "unknown")
                            detections.append({
                                "class_id": cls_id,
                                "label": label,
                                "confidence": conf,
                                "box": (int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3]))
                            })
            except Exception as e:
                print(f"[YoloDetector] Native YOLO inference error: {e}. Falling back to simulation.")
                # If native fails mid-operation, proceed to mock logic

        # Fallback simulated detection if native YOLO is mock or failed
        if (self.is_mock or self.model is None) or len(detections) == 0:
            # We match simulated objects drawn by the CameraWorker simulator based on color tones.
            
            # 1. Simulated Person: uses color (100, 100, 200) - BGR.
            # B=100, G=100, R=200
            lower_person = np.array([95, 95, 195])
            upper_person = np.array([105, 105, 205])
            mask_person = cv2.inRange(frame_bgr, lower_person, upper_person)
            contours_person, _ = cv2.findContours(mask_person, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for c in contours_person:
                if cv2.contourArea(c) > 200:
                    x, y, cw, ch_rect = cv2.boundingRect(c)
                    y1 = max(0, y - 30)  # Expand slightly to cover the head circle
                    y2 = min(h, y + ch_rect)
                    x1 = max(0, x - 5)
                    x2 = min(w, x + cw + 5)
                    detections.append({
                        "class_id": 0,
                        "label": "person",
                        "confidence": 0.92,
                        "box": (x1, y1, x2, y2)
                    })

            # 2. Simulated Car: uses color (180, 100, 100) - BGR.
            # B=180, G=100, R=100
            lower_car = np.array([175, 95, 95])
            upper_car = np.array([185, 105, 105])
            mask_car = cv2.inRange(frame_bgr, lower_car, upper_car)
            contours_car, _ = cv2.findContours(mask_car, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for c in contours_car:
                if cv2.contourArea(c) > 500:
                    x, y, cw, ch_rect = cv2.boundingRect(c)
                    detections.append({
                        "class_id": 2,
                        "label": "car",
                        "confidence": 0.88,
                        "box": (x, y, x + cw, y + ch_rect)
                    })

            # 3. Simple motion/brightness heuristic for real camera feeds running under mock fallback
            if len(detections) == 0 and not self.is_mock:
                gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for c in contours:
                    if cv2.contourArea(c) > 1000:
                        x, y, cw, ch_rect = cv2.boundingRect(c)
                        detections.append({
                            "class_id": 0,
                            "label": "person",
                            "confidence": 0.75,
                            "box": (x, y, x + cw, y + ch_rect)
                        })

        # Draw visual annotations on a copy of the frame
        annotated_frame = self.draw_annotations(frame_bgr, detections)
        return annotated_frame, detections

    def draw_annotations(self, frame: np.ndarray, detections: list[dict]) -> np.ndarray:
        """Draws aesthetic bounding boxes and filled labels for detected targets."""
        annotated = frame.copy()
        
        # Color mapping in BGR for visual clarity
        colors = {
            0: (102, 255, 0),    # person - neon green
            2: (255, 150, 0),    # car - neon blue
            3: (0, 165, 255),    # motorcycle - orange
            7: (255, 0, 180),    # truck - magenta
            16: (0, 220, 255),   # dog - yellow/gold
        }

        for det in detections:
            cls_id = det.get("class_id", 0)
            box = det["box"]
            conf = det["confidence"]
            label = det["label"]
            
            color = colors.get(cls_id, (102, 255, 0))
            x1, y1, x2, y2 = box
            
            # 1. Draw bounding box with rounded corner hints or standard neat rectangle
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # 2. Draw label background badge & text
            label_text = f"{label.upper()} {int(conf * 100)}%"
            (tw, th), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
            
            # Calculate position to draw label (above bounding box or inside if there's no room)
            y_label = y1 - 4
            if y_label - th - 8 < 0:
                # Draw inside the top of bounding box
                cv2.rectangle(annotated, (x1, y1), (x1 + tw + 10, y1 + th + 8), color, -1)
                cv2.putText(annotated, label_text, (x1 + 5, y1 + th + 4), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)
            else:
                # Draw above bounding box
                cv2.rectangle(annotated, (x1, y1 - th - 8), (x1 + tw + 10, y1), color, -1)
                cv2.putText(annotated, label_text, (x1 + 5, y1 - 4), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)

        return annotated
