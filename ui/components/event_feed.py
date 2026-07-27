import os
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QFrame
from PySide6.QtGui import QPixmap, QFont, QColor

class EventFeedItemWidget(QWidget):
    def __init__(self, event_data: dict):
        super().__init__()
        self.event_data = event_data
        self.init_ui()

    def init_ui(self):
        # Outer Horizontal Layout
        h_layout = QHBoxLayout(self)
        h_layout.setContentsMargins(8, 8, 8, 8)
        h_layout.setSpacing(12)

        # Thumbnail Label (90x60)
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(90, 60)
        self.lbl_thumb.setStyleSheet("background-color: #000000; border: 1px solid #3A3F4B;")
        self.lbl_thumb.setAlignment(Qt.AlignCenter)

        # Load and scale thumbnail
        snap_path = self.event_data.get("snapshot_path", "")
        if os.path.exists(snap_path):
            pix = QPixmap(snap_path)
            self.lbl_thumb.setPixmap(pix.scaled(90, 60, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        else:
            self.lbl_thumb.setText("NO IMG")
            self.lbl_thumb.setStyleSheet("color: #666666; background-color: #131314; border: 1px solid #3A3F4B;")

        h_layout.addWidget(self.lbl_thumb)

        # Text Details Layout (Vertical)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        text_layout.setContentsMargins(0, 0, 0, 0)

        # Header Row: Camera Name + Threat Badge
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        cam_info_layout = QVBoxLayout()
        cam_info_layout.setSpacing(1)

        lbl_cam = QLabel(self.event_data.get("camera_name", "Camera"))
        lbl_cam.setFont(QFont("Inter", 10, QFont.Bold))
        lbl_cam.setStyleSheet("color: #e5e2e2; border: none; background: transparent; padding: 0px;")
        
        lbl_time = QLabel(self.event_data.get("timestamp", ""))
        lbl_time.setFont(QFont("JetBrains Mono", 8))
        lbl_time.setStyleSheet("color: #c6c6cb; border: none; background: transparent; padding: 0px;")

        cam_info_layout.addWidget(lbl_cam)
        cam_info_layout.addWidget(lbl_time)
        header_layout.addLayout(cam_info_layout, 1)

        threat_level = self.event_data.get("threat_level", "LOW").upper()
        lbl_badge = QLabel(f" {threat_level} ")
        lbl_badge.setFont(QFont("Inter", 8, QFont.Bold))
        lbl_badge.setAlignment(Qt.AlignCenter)
        lbl_badge.setFixedHeight(18)
        
        # Color coding flat borders matching theme
        if threat_level == "HIGH":
            badge_style = "border: 1px solid #DC2626; color: #DC2626; font-weight: bold; background: transparent; padding: 1px 3px;"
        elif threat_level in ["MEDIUM", "MED"]:
            badge_style = "border: 1px solid #D97706; color: #D97706; font-weight: bold; background: transparent; padding: 1px 3px;"
        elif threat_level == "LOW":
            badge_style = "border: 1px solid #2D6A4F; color: #2D6A4F; font-weight: bold; background: transparent; padding: 1px 3px;"
        else: # INFO or others
            badge_style = "border: 1px solid #909095; color: #c6c6cb; font-weight: bold; background: transparent; padding: 1px 3px;"

        lbl_badge.setStyleSheet(badge_style)
        header_layout.addWidget(lbl_badge)

        text_layout.addLayout(header_layout)

        # AI Summary Text
        summary = self.event_data.get("summary", "")
        if not summary:
            # Fallback parsing summary from explanation
            explanation = self.event_data.get("explanation", "")
            if explanation.startswith("["):
                # explanation format: "[THREAT] Summary - Details"
                parts = explanation.split("] ", 1)
                if len(parts) > 1:
                    summary = parts[1].split(" - ", 1)[0]
                else:
                    summary = explanation
            else:
                summary = explanation or "No details."

        lbl_summary = QLabel(summary)
        lbl_summary.setWordWrap(True)
        lbl_summary.setFont(QFont("Inter", 9))
        lbl_summary.setStyleSheet("color: #c6c6cb; border: none; background: transparent; line-height: 14px;")
        text_layout.addWidget(lbl_summary)

        # Monospaced Target Detail Bullets
        detections = self.event_data.get("detections", [])
        if detections:
            bullet_text = ""
            for det in detections:
                label = det.get("label", "target").upper()
                conf = int(det.get("confidence", 1.0) * 100)
                bullet_text += f"• {label} ({conf}%)\n"
            
            bullet_text = bullet_text.strip()
            
            lbl_bullets = QLabel(bullet_text)
            lbl_bullets.setFont(QFont("JetBrains Mono", 8))
            lbl_bullets.setStyleSheet("color: #c3c6d1; border: none; background: transparent; padding-top: 2px;")
            text_layout.addWidget(lbl_bullets)

        h_layout.addLayout(text_layout, 1)


class EventFeedWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Title Header
        lbl_title = QLabel("DETECTION LOG")
        lbl_title.setObjectName("sectionHeader")
        lbl_title.setFont(QFont("Inter", 10, QFont.Bold))
        layout.addWidget(lbl_title)

        # Subtitle instructions
        lbl_sub = QLabel("DOUBLE-CLICK ANY CARD TO VIEW FULL LOGS")
        lbl_sub.setFont(QFont("Inter", 8, QFont.Bold))
        lbl_sub.setStyleSheet("color: #909095; margin-bottom: 2px;")
        layout.addWidget(lbl_sub)

        # QListWidget to hold alerts
        self.list_alerts = QListWidget()
        self.list_alerts.setObjectName("eventFeedList")
        self.list_alerts.setStyleSheet("""
            QListWidget {
                background-color: #1c1b1c;
                border: 1px solid #3A3F4B;
            }
            QListWidget::item {
                background-color: #201f20;
                border: 1px solid #3A3F4B;
                margin-bottom: 6px;
                padding: 0px;
            }
            QListWidget::item:hover {
                background-color: #2C313A;
                border-color: #c3c6d1;
            }
        """)
        self.list_alerts.doubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_alerts, 1)

    def add_event(self, event_data: dict):
        """Adds a new event item to the top of the feed list."""
        item = QListWidgetItem()
        item.setData(Qt.UserRole, event_data)

        # Create custom item widget
        item_widget = EventFeedItemWidget(event_data)
        item.setSizeHint(item_widget.sizeHint())

        # Insert at the top of the feed list (index 0)
        self.list_alerts.insertItem(0, item)
        self.list_alerts.setItemWidget(item, item_widget)

        # Keep list length capped to 50 for memory safety
        if self.list_alerts.count() > 50:
            removed_item = self.list_alerts.takeItem(self.list_alerts.count() - 1)
            del removed_item

    def _on_item_double_clicked(self, index):
        item = self.list_alerts.currentItem()
        if item is None:
            return
        event_data = item.data(Qt.UserRole)
        if event_data:
            from ui.incident_log import IncidentDetailsDialog
            dialog = IncidentDetailsDialog(event_data, self)
            dialog.exec()
