from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtGui import QFont

class CameraManager(QWidget):
    add_camera_clicked = Signal(str, str)     # name, url
    delete_camera_clicked = Signal(int)       # camera_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setObjectName("cameraManager")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        lbl_title = QLabel("CAMERA FEEDS")
        lbl_title.setFont(QFont("Inter", 10, QFont.Bold))
        lbl_title.setObjectName("sectionHeader")
        layout.addWidget(lbl_title)

        # Warning Badge (Max Camera Limit)
        self.lbl_warning_badge = QLabel("⚠️ MAX CAMERA LIMIT REACHED (4 MAX)")
        self.lbl_warning_badge.setStyleSheet("""
            background-color: #DC2626;
            color: #ffffff;
            font-weight: bold;
            padding: 8px;
            text-align: center;
        """)
        self.lbl_warning_badge.setAlignment(Qt.AlignCenter)
        self.lbl_warning_badge.setVisible(False)
        layout.addWidget(self.lbl_warning_badge)

        # Input Form
        form_layout = QVBoxLayout()
        form_layout.setSpacing(8)

        lbl_name = QLabel("CAMERA NAME")
        lbl_name.setFont(QFont("Inter", 10, QFont.Bold))
        lbl_name.setObjectName("inputLabel")
        
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("e.g. Lobby Entrance")

        lbl_url = QLabel("RTSP URL")
        lbl_url.setFont(QFont("Inter", 10, QFont.Bold))
        lbl_url.setObjectName("inputLabel")

        self.input_url = QLineEdit()
        self.input_url.setPlaceholderText("rtsp://192.168.1.100:554/live")

        self.btn_add_cam = QPushButton("ADD FEED")
        self.btn_add_cam.setObjectName("primaryButton")
        self.btn_add_cam.setFixedHeight(32)
        self.btn_add_cam.setCursor(Qt.PointingHandCursor)
        self.btn_add_cam.clicked.connect(self._on_add_clicked)

        form_layout.addWidget(lbl_name)
        form_layout.addWidget(self.input_name)
        form_layout.addWidget(lbl_url)
        form_layout.addWidget(self.input_url)
        form_layout.addWidget(self.btn_add_cam)

        layout.addLayout(form_layout)

        # Active Streams section header
        lbl_active_title = QLabel("ACTIVE STREAMS")
        lbl_active_title.setFont(QFont("Inter", 10, QFont.Bold))
        lbl_active_title.setObjectName("sectionHeader")
        layout.addWidget(lbl_active_title)

        # Table Widget for cameras
        self.table_cameras = QTableWidget(0, 3)
        self.table_cameras.setObjectName("cameraTable")
        self.table_cameras.setHorizontalHeaderLabels(["NAME", "SOURCE", ""])
        self.table_cameras.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_cameras.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_cameras.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table_cameras.setColumnWidth(2, 30)
        self.table_cameras.verticalHeader().setVisible(False)
        self.table_cameras.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_cameras.setSelectionMode(QTableWidget.SingleSelection)
        self.table_cameras.setShowGrid(False)
        
        # Apply stylesheet directly to headers to match table
        self.table_cameras.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #1c1b1c;
                color: #c6c6cb;
                font-family: 'Inter';
                font-size: 10px;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid #3A3F4B;
                padding: 4px;
            }
        """)

        layout.addWidget(self.table_cameras, 1)

    def _on_add_clicked(self):
        name = self.input_name.text().strip()
        url = self.input_url.text().strip()
        if not name or not url:
            QMessageBox.warning(self, "Validation Error", "Please fill in both Camera Name and RTSP URL.")
            return
        self.add_camera_clicked.emit(name, url)
        self.input_name.clear()
        self.input_url.clear()

    def refresh_camera_list(self, cameras: list):
        limit_reached = len(cameras) >= 4
        self.lbl_warning_badge.setVisible(limit_reached)
        self.input_name.setEnabled(not limit_reached)
        self.input_url.setEnabled(not limit_reached)
        self.btn_add_cam.setEnabled(not limit_reached)

        self.table_cameras.setRowCount(0)
        for idx, cam in enumerate(cameras):
            self.table_cameras.insertRow(idx)
            
            # Name
            item_name = QTableWidgetItem(cam["name"])
            item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
            item_name.setFont(QFont("Inter", 10, QFont.Bold))
            item_name.setForeground(Qt.white)
            self.table_cameras.setItem(idx, 0, item_name)

            # Source (IP or elided URL)
            url = cam["url"]
            source_text = url
            if "://" in url:
                parts = url.split("://")[1].split("/")[0]
                source_text = parts
            
            item_src = QTableWidgetItem(source_text)
            item_src.setFlags(item_src.flags() & ~Qt.ItemIsEditable)
            item_src.setFont(QFont("JetBrains Mono", 9))
            item_src.setForeground(Qt.lightGray)
            self.table_cameras.setItem(idx, 1, item_src)

            # Delete Button
            btn_delete = QPushButton("✕")
            btn_delete.setCursor(Qt.PointingHandCursor)
            btn_delete.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #DC2626;
                    border: none;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 0px;
                }
                QPushButton:hover {
                    color: #ff4d4d;
                }
            """)
            btn_delete.clicked.connect(lambda checked=False, cid=cam["id"]: self.delete_camera_clicked.emit(cid))
            self.table_cameras.setCellWidget(idx, 2, btn_delete)
