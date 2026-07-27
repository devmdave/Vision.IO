import time
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtWidgets import QFrame, QWidget, QGridLayout
from PySide6.QtGui import QPainter, QImage, QPen, QColor, QFont, QBrush

class VideoTileWidget(QFrame):
    clicked = Signal(int)

    def __init__(self, camera_id: int, camera_name: str, parent=None):
        super().__init__(parent)
        self.camera_id = camera_id
        self.camera_name = camera_name.upper()
        self.current_frame = None
        self.detections = []
        self.yolo_latency = 0.0
        self.fps = 0
        self.connected = False
        self.selected = False
        self.last_frame_time = time.time()
        self.vlm_alert_text = ""
        self.vlm_alert_is_violating = False
        self.vlm_alert_time = 0.0

        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("""
            QFrame {
                background-color: #131314;
                border: 1px solid #3A3F4B;
            }
        """)
        self.setCursor(Qt.PointingHandCursor)

    def set_frame(self, qimage: QImage):
        now = time.time()
        dt = now - self.last_frame_time
        self.last_frame_time = now
        self.fps = int(1.0 / dt) if dt > 0 else 0
        
        self.current_frame = qimage
        self.update()

    def set_detections(self, detections: list, latency_ms: float):
        self.detections = detections
        self.yolo_latency = latency_ms
        self.update()

    def set_connection_status(self, connected: bool):
        self.connected = connected
        if not connected:
            self.current_frame = None
            self.detections = []
            self.fps = 0
        self.update()

    def set_selected(self, selected: bool):
        self.selected = selected
        self.update()

    def set_vlm_response(self, text: str, is_alert: bool):
        self.vlm_alert_text = text
        self.vlm_alert_is_violating = is_alert
        self.vlm_alert_time = time.time()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.camera_id)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False) # For clean sharp borders
        
        rect = self.contentsRect()
        
        if self.current_frame is not None and not self.current_frame.isNull():
            # Draw frame
            painter.drawImage(rect, self.current_frame)

            # Draw 1px bounding boxes
            if self.detections:
                fw = self.current_frame.width()
                fh = self.current_frame.height()
                ww = rect.width()
                wh = rect.height()
                
                painter.setFont(QFont("JetBrains Mono", 8))
                
                for det in self.detections:
                    box = det["box"]
                    # Map coordinates
                    x1 = int(box[0] * ww / fw) + rect.left()
                    y1 = int(box[1] * wh / fh) + rect.top()
                    x2 = int(box[2] * ww / fw) + rect.left()
                    y2 = int(box[3] * wh / fh) + rect.top()
                    
                    # Choose colors (threat vs standard)
                    is_threat = self.vlm_alert_is_violating and (time.time() - self.vlm_alert_time < 10.0)
                    box_color = QColor("#DC2626") if is_threat else QColor("#c3c6d1")
                    text_color = QColor("#ffffff") if is_threat else QColor("#2c3039")

                    # Draw 1px box
                    pen_box = QPen(box_color, 1)
                    painter.setPen(pen_box)
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRect(x1, y1, x2 - x1, y2 - y1)

                    # Draw text label background
                    label_text = f"{det['label'].upper()} {int(det['confidence']*100)}%"
                    text_rect = painter.fontMetrics().boundingRect(label_text)
                    lbl_w = text_rect.width() + 6
                    lbl_h = text_rect.height() + 2

                    lbl_y = y1 - lbl_h
                    if lbl_y < rect.top():
                        lbl_y = y1
                    
                    painter.fillRect(x1, lbl_y, lbl_w, lbl_h, QBrush(box_color))
                    
                    # Draw text label
                    painter.setPen(text_color)
                    painter.drawText(x1 + 3, lbl_y + lbl_h - 3, label_text)

            # Top-left OSD overlay bar
            osd_h = 24
            osd_rect = QRect(rect.left() + 1, rect.top() + 1, 180, osd_h)
            painter.fillRect(osd_rect, QColor("#1E222A"))
            
            # Draw OSD Border (1px)
            painter.setPen(QColor("#3A3F4B"))
            painter.drawRect(osd_rect)

            # Text
            painter.setPen(QColor("#e5e2e2"))
            painter.setFont(QFont("JetBrains Mono", 8))
            telemetry_str = f"{self.camera_name} | {self.fps} FPS"
            painter.drawText(osd_rect.adjusted(8, 0, -32, 0), Qt.AlignVCenter | Qt.AlignLeft, telemetry_str)

            # Live text indicator
            painter.setPen(QColor("#2D6A4F"))
            painter.setFont(QFont("JetBrains Mono", 8, QFont.Bold))
            painter.drawText(osd_rect.adjusted(145, 0, -8, 0), Qt.AlignVCenter | Qt.AlignRight, "LIVE")

            # VLM Banner overlay (if active in last 10s)
            if self.vlm_alert_text and (time.time() - self.vlm_alert_time < 10.0):
                banner_h = 32
                banner_rect = QRect(rect.left() + 1, rect.bottom() - banner_h - 1, rect.width() - 2, banner_h)
                bg_color = QColor("#DC2626") if self.vlm_alert_is_violating else QColor("#2D6A4F")
                painter.fillRect(banner_rect, bg_color)
                
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont("Inter", 9, QFont.Bold))
                prefix = "🚨 VLM: " if self.vlm_alert_is_violating else "✅ VLM: "
                elided_text = painter.fontMetrics().elidedText(prefix + self.vlm_alert_text, Qt.ElideRight, banner_rect.width() - 16)
                painter.drawText(banner_rect.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, elided_text)

        else:
            # Offline State
            painter.fillRect(rect, QColor("#131314"))
            painter.setPen(QColor("#DC2626"))
            painter.setFont(QFont("Inter", 11, QFont.Bold))
            offline_str = f"🎥 [ {self.camera_name} ]\nCONNECTION OFFLINE"
            painter.drawText(rect, Qt.AlignCenter, offline_str)

        # Draw selected border
        if self.selected:
            painter.setPen(QPen(QColor("#c3c6d1"), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect.adjusted(1, 1, -1, -1))


class VideoGridWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.widgets = {}  # camera_id -> VideoTileWidget
        self.active_camera_id = None
        self.init_ui()

    def init_ui(self):
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(12) # Gutter spacing matching DESIGN.md

    def update_grid(self, cameras: list, select_callback):
        existing_ids = {cam["id"] for cam in cameras}
        for cam_id in list(self.widgets.keys()):
            if cam_id not in existing_ids:
                widget = self.widgets.pop(cam_id)
                self.grid_layout.removeWidget(widget)
                widget.setParent(None)
                widget.deleteLater()

        cols = 1 if len(cameras) <= 1 else 2
        for idx, cam in enumerate(cameras):
            cam_id = cam["id"]
            if cam_id not in self.widgets:
                widget = VideoTileWidget(cam_id, cam["name"])
                widget.clicked.connect(select_callback)
                self.widgets[cam_id] = widget
            else:
                widget = self.widgets[cam_id]

            row = idx // cols
            col = idx % cols
            self.grid_layout.removeWidget(widget)
            self.grid_layout.addWidget(widget, row, col)

        if cameras:
            if self.active_camera_id not in self.widgets:
                self.active_camera_id = cameras[0]["id"]
            
            for cid, widget in self.widgets.items():
                widget.set_selected(cid == self.active_camera_id)
        else:
            self.active_camera_id = None
