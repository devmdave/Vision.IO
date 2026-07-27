import os
import queue
import json
import cv2
import httpx
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from PySide6.QtCore import QThread, Slot, Signal
import numpy as np

from utils import config

class AlertDispatcher(QThread):
    finished_dispatch = Signal(bool, str)  # success, status message

    def __init__(self):
        super().__init__()
        self.task_queue = queue.Queue()
        self.running = True

    def run(self):
        print("[AlertDispatcher] Starting background alert worker thread...")
        while self.running:
            try:
                # Non-blocking pull with timeout
                task = self.task_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            camera_name, timestamp, frame_bgr, vlm_dict = task
            try:
                self._process_dispatch(camera_name, timestamp, frame_bgr, vlm_dict)
            except Exception as e:
                print(f"[AlertDispatcher] Error processing alert dispatch: {e}")
                self.finished_dispatch.emit(False, str(e))
            finally:
                self.task_queue.task_done()

        print("[AlertDispatcher] Background thread stopped.")

    def dispatch_high_threat(self, camera_name: str, timestamp: str, frame_bgr: np.ndarray, vlm_dict: dict):
        """Public method to enqueue a high-threat alert for background processing."""
        if not self.isRunning():
            self.start()
        
        # Make a copy of the frame to avoid mutation/threading issues
        frame_copy = frame_bgr.copy() if frame_bgr is not None else None
        self.task_queue.put((camera_name, timestamp, frame_copy, vlm_dict))

    def _process_dispatch(self, camera_name: str, timestamp: str, frame_bgr: np.ndarray, vlm_dict: dict):
        discord_enabled = config.get_discord_enabled()
        email_enabled = config.get_email_enabled()

        if not discord_enabled and not email_enabled:
            print("[AlertDispatcher] Threat dispatch skipped: Both Discord and Email channels are disabled.")
            return

        if frame_bgr is None:
            print("[AlertDispatcher] Alert dispatch error: Image frame is missing.")
            return

        # Encode frame_bgr to JPEG bytes in memory (no disk writes)
        success, buffer = cv2.imencode('.jpg', frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not success:
            print("[AlertDispatcher] Failed to encode threat frame to JPEG in memory.")
            return
        image_bytes = buffer.tobytes()

        # 1. Discord Webhook Integration
        if discord_enabled:
            self._dispatch_discord(camera_name, timestamp, image_bytes, vlm_dict)

        # 2. SMTP Email Integration
        if email_enabled:
            self._dispatch_email(camera_name, timestamp, image_bytes, vlm_dict)

    def _dispatch_discord(self, camera_name: str, timestamp: str, image_bytes: bytes, vlm_dict: dict):
        webhook_url = config.get_discord_webhook_url()
        if not webhook_url:
            print("[AlertDispatcher] Discord webhook URL is empty. Skipping.")
            return

        print(f"[AlertDispatcher] Dispatching Rich Embed alert to Discord webhook...")

        # Rich Embed structure with red border (#DC2626 -> decimal 14427686)
        embed = {
            "title": "🚨 HIGH RISK SECURITY THREAT DETECTED",
            "color": 14427686,
            "fields": [
                {"name": "Camera", "value": camera_name, "inline": True},
                {"name": "Time", "value": timestamp, "inline": True},
                {"name": "AI Summary", "value": vlm_dict.get("summary", "N/A"), "inline": False},
                {"name": "Details", "value": vlm_dict.get("details", "N/A"), "inline": False}
            ],
            "image": {
                "url": "attachment://snapshot.jpg"
            }
        }

        payload = {
            "embeds": [embed]
        }

        files = {
            "file": ("snapshot.jpg", image_bytes, "image/jpeg")
        }

        data = {
            "payload_json": json.dumps(payload)
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(webhook_url, data=data, files=files)
                if response.status_code in [200, 204]:
                    print("[AlertDispatcher] Discord webhook alert dispatched successfully.")
                    self.finished_dispatch.emit(True, "Discord alert sent successfully.")
                else:
                    err_msg = f"Discord Webhook error (status {response.status_code}): {response.text}"
                    print(f"[AlertDispatcher] {err_msg}")
                    self.finished_dispatch.emit(False, err_msg)
        except Exception as e:
            print(f"[AlertDispatcher] Discord connection failed: {e}")
            self.finished_dispatch.emit(False, f"Discord connection error: {e}")

    def _dispatch_email(self, camera_name: str, timestamp: str, image_bytes: bytes, vlm_dict: dict):
        smtp_server = config.get_smtp_server()
        smtp_port = config.get_smtp_port()
        sender_email = config.get_smtp_sender_email()
        recipient_email = config.get_smtp_recipient_email()
        smtp_password = config.get_api_key("smtp_password")

        if not smtp_server or not sender_email or not recipient_email:
            print("[AlertDispatcher] SMTP configuration fields are incomplete. Skipping email alert.")
            return

        print(f"[AlertDispatcher] Dispatching email alert to {recipient_email}...")

        # Create MIME multipart message
        msg = MIMEMultipart("related")
        msg["Subject"] = f"🚨 VLM HIGH THREAT DETECTED: {camera_name}"
        msg["From"] = sender_email
        msg["To"] = recipient_email

        # HTML body with embedded CID image
        summary = vlm_dict.get("summary", "N/A")
        details = vlm_dict.get("details", "N/A")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f3f4f6; color: #1f2937; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
                .header {{ background-color: #dc2626; color: #ffffff; padding: 20px; text-align: center; font-size: 20px; font-weight: bold; }}
                .content {{ padding: 24px; }}
                .field {{ margin-bottom: 16px; }}
                .label {{ font-weight: bold; color: #4b5563; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; }}
                .value {{ font-size: 16px; margin-top: 4px; color: #111827; }}
                .image-container {{ margin-top: 24px; text-align: center; border-radius: 4px; overflow: hidden; border: 1px solid #e5e7eb; }}
                .image-container img {{ max-width: 100%; height: auto; display: block; margin: 0 auto; }}
                .footer {{ background-color: #f9fafb; padding: 16px; text-align: center; font-size: 12px; color: #9ca3af; border-top: 1px solid #e5e7eb; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    🚨 HIGH RISK SECURITY THREAT DETECTED
                </div>
                <div class="content">
                    <div class="field">
                        <div class="label">Camera</div>
                        <div class="value">{camera_name}</div>
                    </div>
                    <div class="field">
                        <div class="label">Timestamp</div>
                        <div class="value">{timestamp}</div>
                    </div>
                    <div class="field">
                        <div class="label">AI Summary</div>
                        <div class="value">{summary}</div>
                    </div>
                    <div class="field">
                        <div class="label">Details</div>
                        <div class="value">{details}</div>
                    </div>
                    <div class="image-container">
                        <img src="cid:threat_image" alt="Threat Snapshot">
                    </div>
                </div>
                <div class="footer">
                    Vision.IO Automated Security Operations Center alert.
                </div>
            </div>
        </body>
        </html>
        """

        msg_alternative = MIMEMultipart("alternative")
        msg.attach(msg_alternative)

        html_part = MIMEText(html_content, "html")
        msg_alternative.attach(html_part)

        # Embedded image part
        img_part = MIMEImage(image_bytes, "jpeg")
        img_part.add_header("Content-ID", "<threat_image>")
        img_part.add_header("Content-Disposition", "inline", filename="snapshot.jpg")
        msg.attach(img_part)

        try:
            # Connect over SMTP
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=15.0)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=15.0)
                server.ehlo()
                server.starttls()
                server.ehlo()

            if smtp_password:
                server.login(sender_email, smtp_password)

            server.sendmail(sender_email, [recipient_email], msg.as_string())
            server.quit()
            print("[AlertDispatcher] SMTP email alert sent successfully.")
            self.finished_dispatch.emit(True, "SMTP Email sent successfully.")
        except Exception as e:
            print(f"[AlertDispatcher] SMTP email dispatch failed: {e}")
            self.finished_dispatch.emit(False, f"SMTP error: {e}")

    def stop(self):
        """Safely stops the worker thread."""
        self.running = False
        self.wait()
