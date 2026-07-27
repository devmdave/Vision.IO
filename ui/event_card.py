import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtGui import QImage, QPixmap, QFont

class EventCard(QFrame):
    def __init__(self, cam_name: str, timestamp: str, threat_level: str, summary: str, frame_bgr: np.ndarray, detections: list = None, parent=None):
        super().__init__(parent)
        self.cam_name = cam_name
        self.timestamp = timestamp
        self.threat_level = threat_level.upper()
        self.summary = summary
        self.frame_bgr = frame_bgr
        self.detections = detections or []
        
        self.init_ui()

    def init_ui(self):
        # Card container styling
        self.setObjectName("eventCard")
        self.setFrameShape(QFrame.NoFrame)
        self.setLineWidth(1)
        self.setStyleSheet("""
            QFrame#eventCard {
                background-color: #201f20;
                border: 1px solid #3A3F4B;
            }
            QFrame#eventCard:hover {
                border-color: #c3c6d1;
                background-color: #2C313A;
            }
        """)
        
        # Horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # 1. Thumbnail (90x60px)
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(90, 60)
        self.lbl_thumb.setAlignment(Qt.AlignCenter)
        self.lbl_thumb.setStyleSheet("background-color: #000000; border: 1px solid #3A3F4B;")

        if self.frame_bgr is not None and isinstance(self.frame_bgr, np.ndarray):
            try:
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(self.frame_bgr, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
                self.lbl_thumb.setPixmap(pixmap.scaled(90, 60, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            except Exception as e:
                self.lbl_thumb.setText("⚠️ ERR")
                print(f"[EventCard] Thumbnail generation error: {e}")
        else:
            self.lbl_thumb.setText("NO IMG")
            self.lbl_thumb.setStyleSheet("color: #666666; background-color: #131314; border: 1px solid #3A3F4B;")

        layout.addWidget(self.lbl_thumb)

        # 2. Right Side Details Layout (Vertical)
        details_layout = QVBoxLayout()
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(4)

        # Header Row: Camera Info + Threat Badge
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        cam_info_layout = QVBoxLayout()
        cam_info_layout.setSpacing(1)
        
        self.lbl_cam = QLabel(self.cam_name)
        self.lbl_cam.setFont(QFont("Inter", 10, QFont.Bold))
        self.lbl_cam.setStyleSheet("color: #e5e2e2; border: none; background: transparent; padding: 0px;")
        
        self.lbl_time = QLabel(self.timestamp)
        self.lbl_time.setFont(QFont("JetBrains Mono", 8))
        self.lbl_time.setStyleSheet("color: #c6c6cb; border: none; background: transparent; padding: 0px;")
        
        cam_info_layout.addWidget(self.lbl_cam)
        cam_info_layout.addWidget(self.lbl_time)
        header_layout.addLayout(cam_info_layout, 1)

        # Flat Threat Level Badge
        self.lbl_badge = QLabel(f" {self.threat_level} ")
        self.lbl_badge.setFont(QFont("Inter", 8, QFont.Bold))
        self.lbl_badge.setAlignment(Qt.AlignCenter)
        self.lbl_badge.setFixedHeight(18)
        
        # Color coding matching Stitch spec
        if self.threat_level == "HIGH":
            badge_style = "border: 1px solid #DC2626; color: #DC2626; font-weight: bold; background: transparent; padding: 1px 3px;"
        elif self.threat_level in ["MEDIUM", "MED"]:
            badge_style = "border: 1px solid #D97706; color: #D97706; font-weight: bold; background: transparent; padding: 1px 3px;"
        elif self.threat_level == "LOW":
            badge_style = "border: 1px solid #2D6A4F; color: #2D6A4F; font-weight: bold; background: transparent; padding: 1px 3px;"
        else: # INFO or others
            badge_style = "border: 1px solid #909095; color: #c6c6cb; font-weight: bold; background: transparent; padding: 1px 3px;"
            
        self.lbl_badge.setStyleSheet(badge_style)
        header_layout.addWidget(self.lbl_badge)
        
        details_layout.addLayout(header_layout)

        # Concise Gemini AI Summary
        self.lbl_summary = QLabel(self.summary)
        self.lbl_summary.setWordWrap(True)
        self.lbl_summary.setFont(QFont("Inter", 9))
        self.lbl_summary.setStyleSheet("color: #c6c6cb; border: none; background: transparent; line-height: 14px;")
        self.lbl_summary.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        details_layout.addWidget(self.lbl_summary)

        # Monospaced Target Detail Bullets
        if self.detections:
            bullet_text = ""
            for det in self.detections:
                label = det.get("label", "target").upper()
                conf = int(det.get("confidence", 1.0) * 100)
                bullet_text += f"• {label} ({conf}%)\n"
            
            # Remove trailing newline
            bullet_text = bullet_text.strip()
            
            lbl_bullets = QLabel(bullet_text)
            lbl_bullets.setFont(QFont("JetBrains Mono", 8))
            lbl_bullets.setStyleSheet("color: #c3c6d1; border: none; background: transparent; padding-top: 2px;")
            details_layout.addWidget(lbl_bullets)

        layout.addLayout(details_layout, 1)
