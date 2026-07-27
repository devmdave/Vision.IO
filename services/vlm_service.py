import base64
import json
import re
import cv2
import httpx
import numpy as np
from utils import config

class VLMService:
    @staticmethod
    def encode_image_base64(frame: np.ndarray) -> str:
        """Helper to convert cv2 numpy frame (BGR) to JPEG base64 string."""
        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        return base64.b64encode(buffer.tobytes()).decode('utf-8')

    @staticmethod
    def extract_json(response_text: str) -> dict:
        """Extracts JSON from response text, handling markdown codeblocks if necessary."""
        text = response_text.strip()
        # Find anything between curly braces (inclusive)
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        try:
            return json.loads(text)
        except Exception:
            raise ValueError(f"Could not parse response as JSON: {text}")

    def analyze_frame(self, frame: np.ndarray, active_rules: list = None) -> dict:
        """
        Sends the primary frame to the configured VLM API (Gemini or OpenAI).
        Returns a dict:
        {
            "threat_level": "LOW" | "MEDIUM" | "HIGH",
            "summary": "short sentence",
            "details": "detailed description"
        }
        """
        provider = config.get_selected_provider()
        model = config.get_selected_model()
        custom_url = config.get_custom_base_url()

        # Retrieve Key
        if provider == "Google Gemini":
            api_key = config.get_api_key("gemini_api_key")
        elif provider == "OpenAI":
            api_key = config.get_api_key("openai_api_key")
        else:
            api_key = config.get_api_key("custom_api_key")

        # Encode frame
        img_b64 = self.encode_image_base64(frame)

        # Build prompt
        prompt = (
            "Analyze this security camera frame. Identify any potential threats, actions, or unusual behaviors. "
        )
        if active_rules:
            rules_str = "\n".join([f"- {r['rule_text']}" for r in active_rules])
            prompt += f"Verify if any of these active security rules are violated:\n{rules_str}\n\n"

        prompt += (
            "Respond strictly in JSON format with the following keys:\n"
            "{\n"
            "  \"threat_level\": \"LOW\"|\"MEDIUM\"|\"HIGH\",\n"
            "  \"summary\": \"short sentence\",\n"
            "  \"details\": \"detailed description\"\n"
            "}\n"
            "Ensure response is purely JSON without extra commentary."
        )

        success = False
        response_text = ""
        err_msg = ""

        try:
            with httpx.Client(timeout=15.0) as client:
                if provider == "Google Gemini":
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                    payload = {
                        "contents": [
                            {
                                "parts": [
                                    {"text": prompt},
                                    {
                                        "inlineData": {
                                            "mimeType": "image/jpeg",
                                            "data": img_b64
                                        }
                                    }
                                ]
                            }
                        ],
                        "generationConfig": {
                            "responseMimeType": "application/json"
                        }
                    }
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        res_json = resp.json()
                        response_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                        success = True
                    else:
                        err_msg = f"Gemini API Error {resp.status_code}: {resp.text}"
                else:
                    # OpenAI or Custom
                    if provider == "OpenAI":
                        url = "https://api.openai.com/v1/chat/completions"
                    else:
                        url = custom_url.rstrip('/')
                        if not url.endswith("/chat/completions"):
                            if url.endswith("/"):
                                url += "chat/completions"
                            else:
                                url += "/chat/completions"

                    headers = {
                        "Content-Type": "application/json"
                    }
                    if api_key:
                        headers["Authorization"] = f"Bearer {api_key}"

                    payload = {
                        "model": model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{img_b64}"
                                        }
                                    }
                                ]
                            }
                        ],
                        "response_format": {"type": "json_object"}
                    }

                    # Try with json_object format
                    try:
                        resp = client.post(url, headers=headers, json=payload)
                        if resp.status_code == 200:
                            response_text = resp.json()["choices"][0]["message"]["content"]
                            success = True
                        else:
                            # Fallback without json_object in case custom model doesn't support it
                            payload_fallback = payload.copy()
                            payload_fallback.pop("response_format", None)
                            resp_fb = client.post(url, headers=headers, json=payload_fallback)
                            if resp_fb.status_code == 200:
                                response_text = resp_fb.json()["choices"][0]["message"]["content"]
                                success = True
                            else:
                                err_msg = f"API Error {resp.status_code}: {resp.text}"
                    except Exception as inner_ex:
                        err_msg = f"API Call Failed: {inner_ex}"

        except Exception as e:
            err_msg = f"Network or Request Error: {e}"

        if not success:
            raise RuntimeError(err_msg)

        # Parse JSON
        return self.extract_json(response_text)
