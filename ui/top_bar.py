from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QFont

class TopBar(QWidget):
    settings_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setObjectName("topBar")
        self.init_ui()

    def init_ui(self):
        # Top-level layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        # Left Section: Logo & Status
        left_layout = QHBoxLayout()
        left_layout.setSpacing(16)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_logo = QLabel("VISION.IO | VMS")
        self.lbl_logo.setObjectName("topBarLogo")
        self.lbl_logo.setFont(QFont("Inter", 12, QFont.Bold))
        self.lbl_logo.setStyleSheet("color: #e5e2e2; font-weight: bold;")
        left_layout.addWidget(self.lbl_logo)

        # Status badge layout
        status_layout = QHBoxLayout()
        status_layout.setSpacing(6)
        status_layout.setContentsMargins(0, 0, 0, 0)

        self.status_icon = QLabel()
        self.status_icon.setFixedSize(8, 8)
        self.status_icon.setStyleSheet("background-color: #2D6A4F; border: none;") # Forest Green
        
        self.status_text = QLabel("STATUS: ACTIVE")
        self.status_text.setFont(QFont("JetBrains Mono", 9))
        self.status_text.setStyleSheet("color: #c6c6cb; font-weight: bold;")
        
        status_layout.addWidget(self.status_icon)
        status_layout.addWidget(self.status_text)
        
        left_layout.addLayout(status_layout)
        layout.addLayout(left_layout)

        # Stretch to push telemetry to center/right
        layout.addStretch(1)

        # Telemetry Labels (Active Feeds, VLM engine, Edge status)
        self.lbl_streams = QLabel("STREAMS: 0/4")
        self.lbl_streams.setFont(QFont("JetBrains Mono", 9))
        self.lbl_streams.setStyleSheet("color: #c6c6cb;")

        self.lbl_engine = QLabel("ENGINE: GEMINI FLASH")
        self.lbl_engine.setFont(QFont("JetBrains Mono", 9))
        self.lbl_engine.setStyleSheet("color: #c6c6cb;")

        self.lbl_edge = QLabel("EDGE: YOLO11")
        self.lbl_edge.setFont(QFont("JetBrains Mono", 9))
        self.lbl_edge.setStyleSheet("color: #c6c6cb;")

        layout.addWidget(self.lbl_streams)
        layout.addWidget(self.lbl_engine)
        layout.addWidget(self.lbl_edge)

        # Stretch to right
        layout.addStretch(1)

        # Settings Trigger Button (⚙)
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setObjectName("settingsBtn")
        self.btn_settings.setFixedSize(28, 28)
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 16px;
                color: #c6c6cb;
            }
            QPushButton:hover {
                color: #e5e2e2;
                background-color: #2C313A;
            }
        """)
        self.btn_settings.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.btn_settings)

    def set_streams_count(self, active: int, total: int):
        self.lbl_streams.setText(f"STREAMS: {active}/{total}")

    def set_engine_status(self, engine_name: str):
        self.lbl_engine.setText(f"ENGINE: {engine_name.upper()}")

    def set_edge_fps(self, fps: float):
        if fps > 0:
            self.lbl_edge.setText(f"EDGE: YOLO11 ({fps:.1f} FPS)")
        else:
            self.lbl_edge.setText("EDGE: YOLO11")

    def set_status_active(self, active: bool):
        if active:
            self.status_icon.setStyleSheet("background-color: #2D6A4F; border: none;")
            self.status_text.setText("STATUS: ACTIVE")
        else:
            self.status_icon.setStyleSheet("background-color: #DC2626; border: none;")
            self.status_text.setText("STATUS: INACTIVE")
