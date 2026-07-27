import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel
from PySide6.QtGui import QFont
from ui.event_card import EventCard

class EventFeed(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        # Configure layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # Sidebar header title
        lbl_title = QLabel("DETECTION LOG")
        lbl_title.setFont(QFont("Inter", 10, QFont.Bold))
        lbl_title.setObjectName("sectionHeader")
        lbl_title.setStyleSheet("color: #e5e2e2; margin-bottom: 2px;")
        layout.addWidget(lbl_title)
        
        # Scroll Area for event cards list
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        # Container widget for scroll area
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 4, 0)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)

    def add_event(self, cam_name: str, timestamp: str, threat_level: str, summary: str, frame_bgr: np.ndarray, detections: list = None):
        """Adds a stylized EventCard to the top of the event feed scroll list."""
        card = EventCard(cam_name, timestamp, threat_level, summary, frame_bgr, detections, self)
        
        # Insert card at index 0 (the top of the vertical layout)
        self.scroll_layout.insertWidget(0, card)
        
        # Capping feed at 50 cards to prevent memory leak
        if self.scroll_layout.count() > 50:
            last_item = self.scroll_layout.takeAt(self.scroll_layout.count() - 1)
            last_widget = last_item.widget()
            if last_widget:
                last_widget.deleteLater()
