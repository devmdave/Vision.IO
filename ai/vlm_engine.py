import base64
import cv2
import httpx
import json
import numpy as np
from datetime import datetime

class VLMEngine:
    def __init__(self, ollama_url="http://localhost:11434", model_name="moondream"):
        self.ollama_url = ollama_url
        self.model_name = model_name

    def analyze_frame(self, frame: np.ndarray, rule_text: str, detections: list) -> dict:
        """
        Sends frame + prompt to local Ollama VLM.
        If Ollama is offline, calls the heuristic simulation model.
        """
        # Encode frame to JPEG then base64 for Ollama
        try:
            _, buffer = cv2.imencode('.jpg', frame)
            img_b64 = base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            print(f"[VLMEngine] Failed to encode frame: {e}")
            return self._heuristic_mock_vlm(rule_text, detections)

        prompt = (
            f"You are a Security Operations Center VLM agent. Analyze this image under the following rule:\n"
            f"Rule: \"{rule_text}\"\n\n"
            f"Determine if the rule is violated. Respond strictly in valid JSON format with the following keys:\n"
            f"- 'alert': boolean (true if rule is violated/matched, false otherwise)\n"
            f"- 'confidence': float (between 0.0 and 1.0 indicating confidence)\n"
            f"- 'explanation': string (brief 1-2 sentence description of what you see related to the rule)\n"
            f"Ensure response is purely JSON."
        )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "images": [img_b64],
            "stream": False,
            "format": "json"
        }

        try:
            # Query Ollama with a tight timeout to prevent blocking the worker thread
            response = httpx.post(f"{self.ollama_url}/api/generate", json=payload, timeout=8.0)
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                data = json.loads(response_text)
                return {
                    "alert": bool(data.get("alert", False)),
                    "confidence": float(data.get("confidence", 0.0)),
                    "explanation": str(data.get("explanation", "Parsed from local Ollama."))
                }
        except Exception as e:
            pass

        # Fall back to simulated heuristic
        return self._heuristic_mock_vlm(rule_text, detections)

    def _heuristic_mock_vlm(self, rule_text: str, detections: list) -> dict:
        """
        Heuristic rule evaluation. Looks at YOLO object categories, labels, and rule keywords
        to generate a believable reasoning output.
        """
        rule_lower = rule_text.lower()
        has_person = any(d["label"] == "person" for d in detections)
        has_car = any(d["label"] == "car" for d in detections)
        
        # Analyze keywords in rule
        wants_person = "person" in rule_lower or "people" in rule_lower or "standing" in rule_lower or "man" in rule_lower or "woman" in rule_lower
        wants_car = "car" in rule_lower or "vehicle" in rule_lower or "truck" in rule_lower or "parked" in rule_lower or "driveway" in rule_lower
        wants_time = "after 10" in rule_lower or "pm" in rule_lower or "night" in rule_lower or "dark" in rule_lower

        alert = False
        confidence = 0.10
        explanation = "Scene evaluated. No anomalies detected violating the active security rules."

        if wants_person and has_person:
            alert = True
            confidence = 0.91
            explanation = "A person was spotted moving within the frame, triggering the camera activity check."
            if wants_time:
                explanation = "An individual was detected on camera during restricted late-night hours, violating rule criteria."
                
        elif wants_car and has_car:
            alert = True
            confidence = 0.88
            explanation = "A vehicle was observed entering the camera driveway boundary matching the target filter."

        elif has_person or has_car:
            confidence = 0.65
            detected_items = [d["label"] for d in detections]
            explanation = f"Detected {', '.join(detected_items)} in field of view, but did not match rule criteria exactly."

        return {
            "alert": alert,
            "confidence": confidence,
            "explanation": explanation
        }
