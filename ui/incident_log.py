import os
import random
import subprocess
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QDialog, QMessageBox, QFrame,
    QSizePolicy, QSplitter
)
from PySide6.QtGui import QPixmap, QFont, QIcon, QColor, QPainter
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis

from db import sqlite_db
from utils.notifications import send_telegram_alert

class IncidentDetailsDialog(QDialog):
    incident_updated = Signal()

    def __init__(self, incident: dict, parent=None):
        super().__init__(parent)
        self.incident = incident
        self.setWindowTitle(f"🚨 Security Alert Details - ID: {incident['id']}")
        self.resize(680, 540)
        self.setStyleSheet("background-color: #121212; color: #e0e0e0;")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        hdr_frame = QFrame()
        hdr_frame.setStyleSheet("background-color: #201f20; border-radius: 0px; border: 1px solid #3A3F4B;")
        hdr_layout = QVBoxLayout(hdr_frame)
        
        lbl_cam = QLabel(f"Camera: <b>{self.incident['camera_name']}</b>")
        lbl_time = QLabel(f"Detected: {self.incident['timestamp']}")
        lbl_rule = QLabel(f"Active Rule: <i>\"{self.incident.get('rule_text', 'Custom Target Trigger')}\"</i>")
        
        lbl_cam.setStyleSheet("font-size: 14px;")
        lbl_time.setStyleSheet("color: #c6c6cb;")
        lbl_rule.setStyleSheet("color: #c3c6d1;")
        
        hdr_layout.addWidget(lbl_cam)
        hdr_layout.addWidget(lbl_time)
        hdr_layout.addWidget(lbl_rule)
        
        self.lbl_snap = QLabel()
        self.lbl_snap.setAlignment(Qt.AlignCenter)
        self.lbl_snap.setMinimumHeight(280)
        self.lbl_snap.setStyleSheet("background-color: #131314; border-radius: 0px; border: 1px solid #3A3F4B;")
        
        snap_path = self.incident["snapshot_path"]
        if os.path.exists(snap_path):
            pix = QPixmap(snap_path)
            self.lbl_snap.setPixmap(pix.scaled(640, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.lbl_snap.setText("Snapshot image not found on disk.")
            self.lbl_snap.setStyleSheet("color: #DC2626; font-weight: bold; background-color: #131314; border-radius: 0px; border: 1px solid #3A3F4B;")

        # Set up 3-frame switcher if they exist
        self.before_path = snap_path.replace(".jpg", "_before.jpg")
        self.after_path = snap_path.replace(".jpg", "_after.jpg")
        self.switcher_widget = None

        if os.path.exists(self.before_path) and os.path.exists(self.after_path):
            self.switcher_widget = QFrame()
            switcher_layout = QHBoxLayout(self.switcher_widget)
            switcher_layout.setContentsMargins(0, 0, 0, 0)
            switcher_layout.setSpacing(10)

            self.btn_before = QPushButton("⏪ 1s Before")
            self.btn_detect = QPushButton("🎯 Detection Frame")
            self.btn_after = QPushButton("⏩ 1s After")

            self.btn_detect.setStyleSheet("background-color: #3A3F4B; color: white; font-weight: bold; border-radius: 0px;")

            self.btn_before.clicked.connect(lambda: self._switch_frame(self.before_path, self.btn_before))
            self.btn_detect.clicked.connect(lambda: self._switch_frame(snap_path, self.btn_detect))
            self.btn_after.clicked.connect(lambda: self._switch_frame(self.after_path, self.btn_after))

            switcher_layout.addWidget(self.btn_before)
            switcher_layout.addWidget(self.btn_detect)
            switcher_layout.addWidget(self.btn_after)

        desc_label = QLabel("VLM Narrative Assessment:")
        desc_label.setStyleSheet("font-weight: bold; color: #e5e2e2;")
        
        self.lbl_explanation = QLabel(self.incident["explanation"])
        self.lbl_explanation.setWordWrap(True)
        self.lbl_explanation.setStyleSheet("background-color: #1c1b1c; padding: 10px; border-radius: 0px; border: 1px solid #3A3F4B; color: #e5e2e2;")

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_open_folder = QPushButton("📂 Open Folder")
        self.btn_open_folder.clicked.connect(self._on_open_folder)
        
        is_fp = self.incident.get("false_positive", 0) == 1
        fp_text = "✅ Mark True Alert" if is_fp else "❌ Mark False Positive"
        self.btn_toggle_fp = QPushButton(fp_text)
        if is_fp:
            self.btn_toggle_fp.setObjectName("successButton")
        else:
            self.btn_toggle_fp.setObjectName("dangerButton")
        self.btn_toggle_fp.clicked.connect(self._on_toggle_false_positive)
        
        self.btn_telegram = QPushButton("✈️ Forward to Telegram")
        self.btn_telegram.setObjectName("accentButton")
        self.btn_telegram.clicked.connect(self._on_forward_telegram)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_open_folder)
        btn_layout.addWidget(self.btn_toggle_fp)
        btn_layout.addWidget(self.btn_telegram)
        btn_layout.addWidget(self.btn_close)
        
        layout.addWidget(hdr_frame)
        layout.addWidget(self.lbl_snap, 1)
        if self.switcher_widget:
            layout.addWidget(self.switcher_widget)
        layout.addWidget(desc_label)
        layout.addWidget(self.lbl_explanation)
        layout.addLayout(btn_layout)

    def _switch_frame(self, path, active_button):
        for btn in [self.btn_before, self.btn_detect, self.btn_after]:
            btn.setStyleSheet("")
        active_button.setStyleSheet("background-color: #007aff; color: white; font-weight: bold;")
        
        if os.path.exists(path):
            pix = QPixmap(path)
            self.lbl_snap.setPixmap(pix.scaled(640, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.lbl_snap.setText("Image not found on disk.")

    def _on_open_folder(self):
        path = self.incident["snapshot_path"]
        if os.path.exists(path):
            folder = os.path.dirname(os.path.abspath(path))
            try:
                if os.name == 'nt':
                    os.startfile(folder)
                else:
                    subprocess.Popen(['xdg-open' if os.name == 'posix' else 'open', folder])
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to open directory: {e}")
        else:
            QMessageBox.warning(self, "Error", "Snapshot path does not exist on disk.")

    def _on_toggle_false_positive(self):
        is_fp = self.incident.get("false_positive", 0) == 1
        new_state = not is_fp
        try:
            sqlite_db.toggle_false_positive(self.incident["id"], new_state)
            self.incident["false_positive"] = 1 if new_state else 0
            
            fp_text = "✅ Mark True Alert" if new_state else "❌ Mark False Positive"
            self.btn_toggle_fp.setText(fp_text)
            if new_state:
                self.btn_toggle_fp.setObjectName("successButton")
            else:
                self.btn_toggle_fp.setObjectName("dangerButton")
            self.btn_toggle_fp.style().polish(self.btn_toggle_fp)
            
            self.incident_updated.emit()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to update incident: {e}")

    def _on_forward_telegram(self):
        token, ok1 = self._prompt_input("Telegram Bot Token", "Enter your bot token:")
        if not ok1 or not token: return
        chat_id, ok2 = self._prompt_input("Telegram Chat ID", "Enter your destination chat or channel ID:")
        if not ok2 or not chat_id: return

        msg = (
            f"⚡️ <b>Vision.IO Incident Manual Forward</b>\n\n"
            f"<b>Cam:</b> {self.incident['camera_name']}\n"
            f"<b>Time:</b> {self.incident['timestamp']}\n"
            f"<b>Details:</b> {self.incident['explanation']}"
        )
        success = send_telegram_alert(token, chat_id, msg, self.incident["snapshot_path"])
        if success:
            QMessageBox.information(self, "Success", "Incident report dispatched successfully to Telegram.")
        else:
            QMessageBox.warning(self, "Failed", "Failed to dispatch Telegram notification. Verify tokens and connection.")

    def _prompt_input(self, title, label):
        from PySide6.QtWidgets import QInputDialog
        return QInputDialog.getText(self, title, label)


class IncidentLogTab(QWidget):
    def __init__(self):
        super().__init__()
        self.yolo_latencies = []
        self.vlm_latencies = []
        self.max_points = 25
        self.init_ui()
        self.setup_charts()
        self.refresh_log()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        
        splitter = QSplitter(Qt.Horizontal)
        
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_list_title = QLabel("📁 Incident Log Feed (Double-Click to Review)")
        lbl_list_title.setObjectName("hudHeader")
        
        self.list_incidents = QListWidget()
        self.list_incidents.doubleClicked.connect(self._on_incident_double_clicked)
        
        btn_refresh = QPushButton("🔄 Refresh Log")
        btn_refresh.clicked.connect(self.refresh_log)
        
        list_layout.addWidget(lbl_list_title)
        list_layout.addWidget(self.list_incidents, 1)
        list_layout.addWidget(btn_refresh, 0)
        
        chart_container = QWidget()
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(10)
        
        lbl_chart_title = QLabel("📊 Live Performance Operations Center")
        lbl_chart_title.setObjectName("hudHeader")
        chart_layout.addWidget(lbl_chart_title)
        
        self.chart_latency_view = QChartView()
        self.chart_latency_view.setRenderHint(QPainter.Antialiasing)
        self.chart_latency_view.setMinimumHeight(180)
        chart_layout.addWidget(self.chart_latency_view, 1)
        
        self.chart_resources_view = QChartView()
        self.chart_resources_view.setRenderHint(QPainter.Antialiasing)
        self.chart_resources_view.setMinimumHeight(180)
        chart_layout.addWidget(self.chart_resources_view, 1)
        
        splitter.addWidget(list_container)
        splitter.addWidget(chart_container)
        splitter.setSizes([320, 560])
        
        main_layout.addWidget(splitter)

    def setup_charts(self):
        self.chart_latency = QChart()
        self.chart_latency.setTitle("AI Pipeline Latencies (ms)")
        self.chart_latency.setBackgroundBrush(QColor("#181818"))
        self.chart_latency.setTitleBrush(QColor("#e0e0e0"))
        
        self.series_yolo = QLineSeries()
        self.series_yolo.setName("YOLO Latency")
        self.series_yolo.setColor(QColor("#00ff66"))
        
        self.series_vlm = QLineSeries()
        self.series_vlm.setName("VLM Latency")
        self.series_vlm.setColor(QColor("#007aff"))
        
        self.chart_latency.addSeries(self.series_yolo)
        self.chart_latency.addSeries(self.series_vlm)
        
        self.axis_latency_x = QValueAxis()
        self.axis_latency_x.setRange(0, self.max_points)
        self.axis_latency_x.setLabelFormat("%d")
        self.axis_latency_x.setLabelsBrush(QColor("#888"))
        
        self.axis_latency_y = QValueAxis()
        self.axis_latency_y.setRange(0, 100)
        self.axis_latency_y.setLabelsBrush(QColor("#888"))
        
        self.chart_latency.addAxis(self.axis_latency_x, Qt.AlignBottom)
        self.chart_latency.addAxis(self.axis_latency_y, Qt.AlignLeft)
        
        self.series_yolo.attachAxis(self.axis_latency_x)
        self.series_yolo.attachAxis(self.axis_latency_y)
        self.series_vlm.attachAxis(self.axis_latency_x)
        self.series_vlm.attachAxis(self.axis_latency_y)
        
        self.chart_latency_view.setChart(self.chart_latency)

        self.chart_resources = QChart()
        self.chart_resources.setTitle("Host Resource Utilization (%)")
        self.chart_resources.setBackgroundBrush(QColor("#181818"))
        self.chart_resources.setTitleBrush(QColor("#e0e0e0"))
        
        self.series_cpu = QLineSeries()
        self.series_cpu.setName("CPU Load")
        self.series_cpu.setColor(QColor("#ff9f0a"))
        
        self.series_ram = QLineSeries()
        self.series_ram.setName("RAM Usage")
        self.series_ram.setColor(QColor("#ff3b30"))
        
        self.chart_resources.addSeries(self.series_cpu)
        self.chart_resources.addSeries(self.series_ram)
        
        self.axis_res_x = QValueAxis()
        self.axis_res_x.setRange(0, self.max_points)
        self.axis_res_x.setLabelFormat("%d")
        self.axis_res_x.setLabelsBrush(QColor("#888"))
        
        self.axis_res_y = QValueAxis()
        self.axis_res_y.setRange(0, 100)
        self.axis_res_y.setLabelsBrush(QColor("#888"))
        
        self.chart_resources.addAxis(self.axis_res_x, Qt.AlignBottom)
        self.chart_resources.addAxis(self.axis_res_y, Qt.AlignLeft)
        
        self.series_cpu.attachAxis(self.axis_res_x)
        self.series_cpu.attachAxis(self.axis_res_y)
        self.series_ram.attachAxis(self.axis_res_x)
        self.series_ram.attachAxis(self.axis_res_y)
        
        self.chart_resources_view.setChart(self.chart_resources)
        
        self.cpu_data = [20.0] * self.max_points
        self.ram_data = [35.0] * self.max_points
        self.yolo_data = [0.0] * self.max_points
        self.vlm_data = [0.0] * self.max_points
        
        for idx in range(self.max_points):
            self.series_cpu.append(idx, self.cpu_data[idx])
            self.series_ram.append(idx, self.ram_data[idx])
            self.series_yolo.append(idx, self.yolo_data[idx])
            self.series_vlm.append(idx, self.vlm_data[idx])

        self.timer_resources = QTimer(self)
        self.timer_resources.timeout.connect(self._update_resources)
        self.timer_resources.start(1000)

    def refresh_log(self):
        self.list_incidents.clear()
        try:
            incidents = sqlite_db.get_all_incidents()
            for inc in incidents:
                item = QListWidgetItem()
                item.setData(Qt.UserRole, inc)
                
                is_fp = inc.get("false_positive", 0) == 1
                fp_indicator = " [FALSE POSITIVE]" if is_fp else ""
                
                # Check alert status (alert could be 0 or 1, or key might be missing)
                is_alert = inc.get("alert", 1) == 1
                
                if is_alert:
                    heading = f"🚨 ALERT - {inc['camera_name']} ({inc['timestamp']}){fp_indicator}"
                    item_color = QColor("#ffffff")
                else:
                    heading = f"ℹ️ INFO - {inc['camera_name']} ({inc['timestamp']})"
                    item_color = QColor("#888888")
                
                explanation = inc["explanation"] or "No assessment details logged."
                item.setText(f"{heading}\n{explanation}")
                
                if is_fp:
                    item.setForeground(QColor("#777777"))
                else:
                    item.setForeground(item_color)
                    
                self.list_incidents.addItem(item)
        except Exception as e:
            print(f"[IncidentLogTab] Failed to read database logs: {e}")

    def _on_incident_double_clicked(self, index):
        item = self.list_incidents.currentItem()
        if item is None:
            return
            
        incident = item.data(Qt.UserRole)
        dialog = IncidentDetailsDialog(incident, self)
        dialog.incident_updated.connect(self.refresh_log)
        dialog.exec()

    @Slot(float)
    def append_yolo_latency(self, latency_ms: float):
        self.yolo_data.pop(0)
        self.yolo_data.append(latency_ms)
        self._refresh_latency_series()

    @Slot(float)
    def append_vlm_latency(self, latency_ms: float):
        self.vlm_data.pop(0)
        self.vlm_data.append(latency_ms)
        self._refresh_latency_series()

    def _refresh_latency_series(self):
        self.series_yolo.clear()
        self.series_vlm.clear()
        
        max_y = 100.0
        for i in range(self.max_points):
            self.series_yolo.append(i, self.yolo_data[i])
            self.series_vlm.append(i, self.vlm_data[i])
            max_y = max(max_y, self.yolo_data[i], self.vlm_data[i])
            
        self.axis_latency_y.setRange(0, max_y + 20)

    def _update_resources(self):
        cpu_val = 15.0
        ram_val = 30.0
        
        try:
            import psutil
            cpu_val = psutil.cpu_percent()
            ram_val = psutil.virtual_memory().percent
        except ImportError:
            cpu_val = max(5.0, min(95.0, self.cpu_data[-1] + random.uniform(-4.0, 4.0)))
            ram_val = max(20.0, min(90.0, self.ram_data[-1] + random.uniform(-0.5, 0.5)))
            
        self.cpu_data.pop(0)
        self.cpu_data.append(cpu_val)
        
        self.ram_data.pop(0)
        self.ram_data.append(ram_val)
        
        self.series_cpu.clear()
        self.series_ram.clear()
        
        for i in range(self.max_points):
            self.series_cpu.append(i, self.cpu_data[i])
            self.series_ram.append(i, self.ram_data[i])
