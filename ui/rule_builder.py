import os
import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal, Slot, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QFileDialog, QMessageBox, QCheckBox
)
from PySide6.QtGui import QPixmap, QImage
from db import sqlite_db
from ai.vlm_engine import VLMEngine

class PlaygroundDropZone(QFrame):
    image_dropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("cardFrame")
        self.setMinimumHeight(150)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        self.lbl_icon = QLabel("📁")
        self.lbl_icon.setStyleSheet("font-size: 32px;")
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        
        self.lbl_text = QLabel("Drag & Drop Image Here\nor Click to Browse")
        self.lbl_text.setStyleSheet("color: #888888; font-weight: bold;")
        self.lbl_text.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.lbl_icon)
        layout.addWidget(self.lbl_text)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("border: 2px dashed #c3c6d1; background-color: #202020; border-radius: 0px;")

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event):
        self.setStyleSheet("")
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                self.image_dropped.emit(path)
                break

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            path, _ = QFileDialog.getOpenFileName(
                self, "Select Test Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
            )
            if path:
                self.image_dropped.emit(path)


class VLMPlaygroundWorker(QThread):
    analysis_completed = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, image_path: str, rule_text: str):
        super().__init__()
        self.image_path = image_path
        self.rule_text = rule_text
        self.engine = VLMEngine()

    def run(self):
        try:
            frame = cv2.imread(self.image_path)
            if frame is None:
                self.error_occurred.emit("Failed to read image file.")
                return
                
            detections = []
            rule_lower = self.rule_text.lower()
            if "person" in rule_lower or "man" in rule_lower or "woman" in rule_lower:
                detections.append({"label": "person", "box": (50, 50, 200, 300), "confidence": 0.90})
            if "car" in rule_lower or "vehicle" in rule_lower or "truck" in rule_lower:
                detections.append({"label": "car", "box": (100, 100, 400, 350), "confidence": 0.85})

            result = self.engine.analyze_frame(frame, self.rule_text, detections)
            self.analysis_completed.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))


class RuleBuilderTab(QWidget):
    rules_updated = Signal()

    def __init__(self):
        super().__init__()
        self.selected_test_image = None
        self.playground_worker = None
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        
        creator_frame = QFrame()
        creator_frame.setObjectName("cardFrame")
        creator_layout = QVBoxLayout(creator_frame)
        
        lbl_title = QLabel("🤖 Add Zero-Shot VLM Security Rule")
        lbl_title.setObjectName("hudHeader")
        
        form_layout = QHBoxLayout()
        self.combo_cameras = QComboBox()
        self.edit_rule_text = QLineEdit()
        self.edit_rule_text.setPlaceholderText("Define rule (e.g. 'Alert if a truck parks in the driveway')")
        
        btn_save = QPushButton("Save Rule")
        btn_save.setObjectName("accentButton")
        btn_save.clicked.connect(self._on_save_rule)
        
        form_layout.addWidget(self.combo_cameras, 0)
        form_layout.addWidget(self.edit_rule_text, 1)
        form_layout.addWidget(btn_save, 0)
        
        creator_layout.addWidget(lbl_title)
        creator_layout.addLayout(form_layout)
        
        lbl_table_title = QLabel("🛡️ Active Rules Register")
        lbl_table_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #888;")
        
        self.table_rules = QTableWidget()
        self.table_rules.setColumnCount(5)
        self.table_rules.setHorizontalHeaderLabels(["ID", "Camera Name", "Natural Language Rule", "Active", "Actions"])
        self.table_rules.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_rules.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_rules.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_rules.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_rules.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_rules.setEditTriggers(QTableWidget.NoEditTriggers)

        left_col.addWidget(creator_frame, 0)
        left_col.addWidget(lbl_table_title, 0)
        left_col.addWidget(self.table_rules, 1)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        right_col.setContentsMargins(0, 0, 0, 0)
        
        playground_frame = QFrame()
        playground_frame.setObjectName("cardFrame")
        playground_frame.setMinimumWidth(340)
        playground_layout = QVBoxLayout(playground_frame)
        
        lbl_play_title = QLabel("🔬 VLM Playground (Sandbox Testing)")
        lbl_play_title.setObjectName("hudHeader")
        
        self.drop_zone = PlaygroundDropZone()
        self.drop_zone.image_dropped.connect(self._on_image_dropped)
        
        self.lbl_thumbnail = QLabel()
        self.lbl_thumbnail.setMinimumSize(300, 200)
        self.lbl_thumbnail.setAlignment(Qt.AlignCenter)
        self.lbl_thumbnail.setStyleSheet("background-color: #131314; border-radius: 0px; border: 1px solid #3A3F4B;")
        self.lbl_thumbnail.hide()
        
        self.edit_play_rule = QLineEdit()
        self.edit_play_rule.setPlaceholderText("Rule: 'Is there a person carrying a package?'")
        self.edit_play_rule.setEnabled(False)
        
        self.btn_run_play = QPushButton("Run Playground Analysis")
        self.btn_run_play.setEnabled(False)
        self.btn_run_play.setObjectName("primaryButton")
        self.btn_run_play.clicked.connect(self._on_run_playground)

        self.result_frame = QFrame()
        self.result_frame.setObjectName("cardFrame")
        self.result_frame.setStyleSheet("background-color: #201f20; border: 1px solid #3A3F4B; border-radius: 0px;")
        res_layout = QVBoxLayout(self.result_frame)
        
        self.lbl_res_alert = QLabel("ALERT STATE: WAITING")
        self.lbl_res_alert.setStyleSheet("font-weight: bold; font-size: 13px; color: #c6c6cb;")
        
        self.lbl_res_confidence = QLabel("Confidence: N/A")
        self.lbl_res_explanation = QLabel("Drop an image and rule to start testing local Vision-Language Model inferences.")
        self.lbl_res_explanation.setWordWrap(True)
        self.lbl_res_explanation.setStyleSheet("color: #c6c6cb;")
        
        res_layout.addWidget(self.lbl_res_alert)
        res_layout.addWidget(self.lbl_res_confidence)
        res_layout.addWidget(self.lbl_res_explanation)
        
        playground_layout.addWidget(lbl_play_title)
        playground_layout.addWidget(self.drop_zone)
        playground_layout.addWidget(self.lbl_thumbnail)
        playground_layout.addWidget(self.edit_play_rule)
        playground_layout.addWidget(self.btn_run_play)
        playground_layout.addWidget(self.result_frame, 1)
        
        right_col.addWidget(playground_frame)

        main_layout.addLayout(left_col, 2)
        main_layout.addLayout(right_col, 1)

    def refresh_data(self):
        self.combo_cameras.clear()
        try:
            cameras = sqlite_db.get_all_cameras()
            for cam in cameras:
                self.combo_cameras.addItem(cam["name"], cam["id"])
        except Exception as e:
            print(f"[RuleBuilderTab] Camera dropdown populate error: {e}")

        self.table_rules.setRowCount(0)
        try:
            rules = sqlite_db.get_all_rules()
            self.table_rules.setRowCount(len(rules))
            
            for row_idx, rule in enumerate(rules):
                self.table_rules.setItem(row_idx, 0, QTableWidgetItem(str(rule["id"])))
                self.table_rules.setItem(row_idx, 1, QTableWidgetItem(rule["camera_name"]))
                self.table_rules.setItem(row_idx, 2, QTableWidgetItem(rule["rule_text"]))
                
                chk_active = QCheckBox()
                chk_active.setChecked(rule["active"] == 1)
                chk_container = QWidget()
                chk_layout = QHBoxLayout(chk_container)
                chk_layout.addWidget(chk_active)
                chk_layout.setAlignment(Qt.AlignCenter)
                chk_layout.setContentsMargins(0,0,0,0)
                
                rule_id = rule["id"]
                chk_active.stateChanged.connect(
                    lambda state, r_id=rule_id: self._on_toggle_rule(r_id, state == Qt.Checked)
                )
                self.table_rules.setCellWidget(row_idx, 3, chk_container)
                
                btn_del = QPushButton("Delete")
                btn_del.setObjectName("dangerButton")
                btn_del.setCursor(Qt.PointingHandCursor)
                btn_del.clicked.connect(lambda _, r_id=rule_id: self._on_delete_rule(r_id))
                self.table_rules.setCellWidget(row_idx, 4, btn_del)
                
        except Exception as e:
            print(f"[RuleBuilderTab] Rules table populate error: {e}")

    def _on_save_rule(self):
        rule_text = self.edit_rule_text.text().strip()
        if not rule_text:
            QMessageBox.warning(self, "Invalid Rule", "Please write a natural language security rule before saving.")
            return

        camera_id = self.combo_cameras.currentData()
        if camera_id is None:
            QMessageBox.warning(self, "No Camera Available", "Please add a camera profile before creating rules.")
            return

        try:
            sqlite_db.add_rule(camera_id, rule_text)
            self.edit_rule_text.clear()
            self.refresh_data()
            self.rules_updated.emit()
            QMessageBox.information(self, "Rule Saved", "VLM security rule has been successfully saved and activated.")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save rule: {e}")

    def _on_toggle_rule(self, rule_id: int, active: bool):
        try:
            sqlite_db.toggle_rule(rule_id, active)
            self.rules_updated.emit()
        except Exception as e:
            print(f"[RuleBuilderTab] Toggle rule failure: {e}")

    def _on_delete_rule(self, rule_id: int):
        reply = QMessageBox.question(
            self, "Confirm Delete", "Are you sure you want to delete this zero-shot rule?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                sqlite_db.delete_rule(rule_id)
                self.refresh_data()
                self.rules_updated.emit()
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to delete rule: {e}")

    def _on_image_dropped(self, image_path: str):
        self.selected_test_image = image_path
        
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(self.lbl_thumbnail.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_thumbnail.setPixmap(scaled_pixmap)
        self.lbl_thumbnail.show()
        self.drop_zone.hide()
        
        self.edit_play_rule.setEnabled(True)
        self.btn_run_play.setEnabled(True)
        self.edit_play_rule.setFocus()
        
        self.lbl_res_alert.setText("ALERT STATE: READY")
        self.lbl_res_alert.setStyleSheet("font-weight: bold; color: #007aff;")
        self.lbl_res_explanation.setText("Enter a security rule below and click 'Run Playground Analysis'.")

    def _on_run_playground(self):
        rule_text = self.edit_play_rule.text().strip()
        if not rule_text:
            QMessageBox.warning(self, "Invalid Query", "Please enter a test prompt/rule for the visual playground.")
            return

        if not self.selected_test_image:
            return

        self.btn_run_play.setEnabled(False)
        self.btn_run_play.setText("Analyzing Frame...")
        
        self.playground_worker = VLMPlaygroundWorker(self.selected_test_image, rule_text)
        self.playground_worker.analysis_completed.connect(self._on_playground_success)
        self.playground_worker.error_occurred.connect(self._on_playground_error)
        self.playground_worker.start()

    @Slot(dict)
    def _on_playground_success(self, result: dict):
        self.btn_run_play.setEnabled(True)
        self.btn_run_play.setText("Run Playground Analysis")
        
        is_alert = result.get("alert", False)
        confidence = result.get("confidence", 0.0)
        explanation = result.get("explanation", "")
        
        if is_alert:
            self.lbl_res_alert.setText("🚨 ALERT TRIGGERED (VIOLATION)")
            self.lbl_res_alert.setStyleSheet("font-weight: bold; color: #ff3b30; font-size: 14px;")
        else:
            self.lbl_res_alert.setText("✅ SCENE SECURE (NO MATCH)")
            self.lbl_res_alert.setStyleSheet("font-weight: bold; color: #00ff66; font-size: 14px;")
            
        self.lbl_res_confidence.setText(f"Inference Confidence: {confidence * 100:.1f}%")
        self.lbl_res_explanation.setText(explanation)

    @Slot(str)
    def _on_playground_error(self, err_msg: str):
        self.btn_run_play.setEnabled(True)
        self.btn_run_play.setText("Run Playground Analysis")
        QMessageBox.critical(self, "Sandbox VLM Error", f"Playground analysis failed: {err_msg}")
