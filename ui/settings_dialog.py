import httpx
import keyring
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QFrame,
    QTabWidget, QWidget, QCheckBox
)
from PySide6.QtGui import QFont

from utils import config

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vision.IO Settings & Integrations")
        self.setFixedSize(450, 480)
        self.init_ui()

    def init_ui(self):
        # Apply premium dark mode styles
        self.setStyleSheet("""
            QDialog {
                background-color: #131314;
                border: 1px solid #3A3F4B;
            }
            QLabel {
                color: #e5e2e2;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #131314;
                border: 1px solid #45474b;
                border-radius: 0px;
                color: #e5e2e2;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #c3c6d1;
            }
            QCheckBox {
                color: #e5e2e2;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #45474b;
                background-color: #131314;
            }
            QCheckBox::indicator:checked {
                background-color: #3e4451;
                border-color: #c3c6d1;
            }
            QTabWidget::pane {
                border: 1px solid #3A3F4B;
                background-color: #131314;
            }
            QTabBar::tab {
                background-color: #1e1e20;
                color: #aaaaaa;
                padding: 8px 16px;
                border: 1px solid #3A3F4B;
                border-bottom: none;
                font-size: 12px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #131314;
                color: #ffffff;
                border-top: 2px solid #c3c6d1;
            }
            QPushButton {
                background-color: #2c313a;
                border: 1px solid #3A3F4B;
                border-radius: 0px;
                color: #e5e2e2;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3e4451;
                border-color: #c3c6d1;
            }
            QPushButton#saveButton {
                background-color: #3A3F4B;
                border: 1px solid #45474b;
                color: #ffffff;
            }
            QPushButton#saveButton:hover {
                background-color: #2c313a;
                border-color: #c3c6d1;
            }
            QPushButton#testButton {
                background-color: transparent;
                border: 1px solid #2D6A4F;
                color: #2D6A4F;
            }
            QPushButton#testButton:hover {
                background-color: #2D6A4F;
                color: #ffffff;
            }
        """)

        # Main Layout
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(20, 20, 20, 20)
        dialog_layout.setSpacing(15)

        # Tab Widget
        self.tab_widget = QTabWidget()

        # --- TAB 1: API Configuration ---
        self.tab_api = QWidget()
        api_layout = QVBoxLayout(self.tab_api)
        api_layout.setContentsMargins(15, 15, 15, 15)
        api_layout.setSpacing(15)

        lbl_title = QLabel("🔑 Gemini AI API Configuration")
        lbl_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        api_layout.addWidget(lbl_title)

        field_layout = QVBoxLayout()
        field_layout.setSpacing(6)
        
        lbl_key = QLabel("Gemini API Key:")
        lbl_key.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        
        self.txt_key = QLineEdit()
        self.txt_key.setEchoMode(QLineEdit.Password)
        self.txt_key.setPlaceholderText("Enter AIzaSy... API key")
        
        # Load key from secure OS keychain using keyring
        try:
            saved_key = keyring.get_password("VisionIO", "gemini_key")
            if saved_key:
                self.txt_key.setText(saved_key)
        except Exception as e:
            print(f"[SettingsDialog] Error loading saved credentials: {e}")

        # Show / Hide toggle button next to password edit
        key_input_layout = QHBoxLayout()
        key_input_layout.setSpacing(8)
        key_input_layout.addWidget(self.txt_key, 1)
        
        self.btn_toggle_visibility = QPushButton("👁️")
        self.btn_toggle_visibility.setFixedWidth(35)
        self.btn_toggle_visibility.clicked.connect(self._toggle_password_visibility)
        key_input_layout.addWidget(self.btn_toggle_visibility)
        
        field_layout.addWidget(lbl_key)
        field_layout.addLayout(key_input_layout)
        api_layout.addLayout(field_layout)

        # Test key button
        self.btn_test = QPushButton("⚡ Test Connection")
        self.btn_test.setObjectName("testButton")
        self.btn_test.clicked.connect(self._test_gemini_connection)
        api_layout.addWidget(self.btn_test)
        api_layout.addStretch(1)

        # --- TAB 2: Alert Notifications ---
        self.tab_alerts = QWidget()
        alerts_layout = QVBoxLayout(self.tab_alerts)
        alerts_layout.setContentsMargins(15, 15, 15, 15)
        alerts_layout.setSpacing(12)

        # Title
        lbl_alerts_title = QLabel("🔔 Threat Alerts & Dispatcher")
        lbl_alerts_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        alerts_layout.addWidget(lbl_alerts_title)

        # 1. Discord Webhook Section
        self.chk_discord_enabled = QCheckBox("Enable Discord Webhook alerts")
        self.chk_discord_enabled.setChecked(config.get_discord_enabled())
        alerts_layout.addWidget(self.chk_discord_enabled)

        lbl_discord_url = QLabel("Discord Webhook URL:")
        lbl_discord_url.setStyleSheet("color: #aaaaaa;")
        self.txt_discord_url = QLineEdit()
        self.txt_discord_url.setPlaceholderText("https://discord.com/api/webhooks/...")
        self.txt_discord_url.setText(config.get_discord_webhook_url())
        alerts_layout.addWidget(lbl_discord_url)
        alerts_layout.addWidget(self.txt_discord_url)

        # Divider line
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setStyleSheet("background-color: #3A3F4B; max-height: 1px;")
        alerts_layout.addWidget(divider)

        # 2. SMTP Email Section
        self.chk_email_enabled = QCheckBox("Enable SMTP Email alerts")
        self.chk_email_enabled.setChecked(config.get_email_enabled())
        alerts_layout.addWidget(self.chk_email_enabled)

        # SMTP Host & Port Container
        smtp_host_layout = QHBoxLayout()
        smtp_host_layout.setSpacing(8)

        vbox_host = QVBoxLayout()
        vbox_host.setSpacing(4)
        lbl_smtp_server = QLabel("SMTP Server:")
        lbl_smtp_server.setStyleSheet("color: #aaaaaa;")
        self.txt_smtp_server = QLineEdit()
        self.txt_smtp_server.setPlaceholderText("smtp.gmail.com")
        self.txt_smtp_server.setText(config.get_smtp_server())
        vbox_host.addWidget(lbl_smtp_server)
        vbox_host.addWidget(self.txt_smtp_server)
        smtp_host_layout.addLayout(vbox_host, 2)

        vbox_port = QVBoxLayout()
        vbox_port.setSpacing(4)
        lbl_smtp_port = QLabel("Port:")
        lbl_smtp_port.setStyleSheet("color: #aaaaaa;")
        self.txt_smtp_port = QLineEdit()
        self.txt_smtp_port.setPlaceholderText("587")
        self.txt_smtp_port.setText(str(config.get_smtp_port()))
        vbox_port.addWidget(lbl_smtp_port)
        vbox_port.addWidget(self.txt_smtp_port)
        smtp_host_layout.addLayout(vbox_port, 1)

        alerts_layout.addLayout(smtp_host_layout)

        # SMTP Email fields
        lbl_smtp_sender = QLabel("Sender Email:")
        lbl_smtp_sender.setStyleSheet("color: #aaaaaa;")
        self.txt_smtp_sender = QLineEdit()
        self.txt_smtp_sender.setPlaceholderText("alerts@domain.com")
        self.txt_smtp_sender.setText(config.get_smtp_sender_email())
        alerts_layout.addWidget(lbl_smtp_sender)
        alerts_layout.addWidget(self.txt_smtp_sender)

        lbl_smtp_password = QLabel("SMTP Password / App Key:")
        lbl_smtp_password.setStyleSheet("color: #aaaaaa;")
        self.txt_smtp_password = QLineEdit()
        self.txt_smtp_password.setEchoMode(QLineEdit.Password)
        self.txt_smtp_password.setPlaceholderText("Enter SMTP password")
        
        # Load SMTP password securely using keyring
        try:
            saved_pwd = keyring.get_password("VisionIO_Desktop", "smtp_password")
            if saved_pwd:
                self.txt_smtp_password.setText(saved_pwd)
        except Exception as e:
            print(f"[SettingsDialog] Error loading saved SMTP credentials: {e}")

        # Show / Hide toggle button next to password edit
        smtp_pwd_layout = QHBoxLayout()
        smtp_pwd_layout.setSpacing(8)
        smtp_pwd_layout.addWidget(self.txt_smtp_password, 1)
        
        self.btn_toggle_smtp_visibility = QPushButton("👁️")
        self.btn_toggle_smtp_visibility.setFixedWidth(35)
        self.btn_toggle_smtp_visibility.clicked.connect(self._toggle_smtp_password_visibility)
        smtp_pwd_layout.addWidget(self.btn_toggle_smtp_visibility)

        alerts_layout.addWidget(lbl_smtp_password)
        alerts_layout.addLayout(smtp_pwd_layout)

        lbl_smtp_recipient = QLabel("Recipient Email:")
        lbl_smtp_recipient.setStyleSheet("color: #aaaaaa;")
        self.txt_smtp_recipient = QLineEdit()
        self.txt_smtp_recipient.setPlaceholderText("recipient@domain.com")
        self.txt_smtp_recipient.setText(config.get_smtp_recipient_email())
        alerts_layout.addWidget(lbl_smtp_recipient)
        alerts_layout.addWidget(self.txt_smtp_recipient)

        # Add tabs
        self.tab_widget.addTab(self.tab_api, "🔑 API Key")
        self.tab_widget.addTab(self.tab_alerts, "🔔 Alert Notifications")
        dialog_layout.addWidget(self.tab_widget)

        # Action Buttons Layout (Global)
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        actions_layout.addStretch(1)

        # Cancel button
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        actions_layout.addWidget(self.btn_cancel)

        # Save button
        self.btn_save = QPushButton("Save")
        self.btn_save.setObjectName("saveButton")
        self.btn_save.clicked.connect(self._save_settings)
        actions_layout.addWidget(self.btn_save)

        dialog_layout.addLayout(actions_layout)

    @Slot()
    def _toggle_password_visibility(self):
        if self.txt_key.echoMode() == QLineEdit.Password:
            self.txt_key.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_visibility.setText("🔒")
        else:
            self.txt_key.setEchoMode(QLineEdit.Password)
            self.btn_toggle_visibility.setText("👁️")

    @Slot()
    def _toggle_smtp_password_visibility(self):
        if self.txt_smtp_password.echoMode() == QLineEdit.Password:
            self.txt_smtp_password.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_smtp_visibility.setText("🔒")
        else:
            self.txt_smtp_password.setEchoMode(QLineEdit.Password)
            self.btn_toggle_smtp_visibility.setText("👁️")

    @Slot()
    def _test_gemini_connection(self):
        api_key = self.txt_key.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Validation Failed", "Please enter an API Key to test.")
            return

        self.btn_test.setEnabled(False)
        self.btn_test.setText("Connecting...")
        self.repaint()

        # Connect to Google Gemini validation endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        success = False
        message = ""
        try:
            resp = httpx.get(url, timeout=6.0)
            if resp.status_code == 200:
                success = True
                message = "Connection successful! Gemini key is active and ready."
            else:
                message = f"API verification failed (Status Code {resp.status_code}):\n{resp.text}"
        except Exception as e:
            message = f"Network request error:\n{e}"

        self.btn_test.setEnabled(True)
        self.btn_test.setText("⚡ Test Connection")
        
        if success:
            QMessageBox.information(self, "API Check Successful", message)
        else:
            QMessageBox.critical(self, "API Check Failed", message)

    @Slot()
    def _save_settings(self):
        # Validation checks
        if self.chk_discord_enabled.isChecked():
            if not self.txt_discord_url.text().strip():
                QMessageBox.warning(self, "Validation Failed", "Discord Webhook URL is required when Discord alerts are enabled.")
                return

        if self.chk_email_enabled.isChecked():
            if not self.txt_smtp_server.text().strip() or not self.txt_smtp_sender.text().strip() or not self.txt_smtp_recipient.text().strip():
                QMessageBox.warning(self, "Validation Failed", "SMTP Server, Sender, and Recipient emails are required when Email alerts are enabled.")
                return

        # Save VLM API Key to keychain
        api_key = self.txt_key.text().strip()
        if api_key:
            try:
                keyring.set_password("VisionIO", "gemini_key", api_key)
            except Exception as e:
                print(f"[SettingsDialog] Failed to save Gemini API key: {e}")

        # Save Discord config
        config.set_discord_enabled(self.chk_discord_enabled.isChecked())
        config.set_discord_webhook_url(self.txt_discord_url.text().strip())

        # Save SMTP config
        config.set_email_enabled(self.chk_email_enabled.isChecked())
        config.set_smtp_server(self.txt_smtp_server.text().strip())
        try:
            port = int(self.txt_smtp_port.text().strip())
            config.set_smtp_port(port)
        except ValueError:
            config.set_smtp_port(587)

        config.set_smtp_sender_email(self.txt_smtp_sender.text().strip())
        config.set_smtp_recipient_email(self.txt_smtp_recipient.text().strip())

        # Save SMTP Password to keychain
        smtp_password = self.txt_smtp_password.text().strip()
        if smtp_password:
            try:
                keyring.set_password("VisionIO_Desktop", "smtp_password", smtp_password)
            except Exception as e:
                print(f"[SettingsDialog] Failed to save SMTP password: {e}")
        else:
            try:
                keyring.delete_password("VisionIO_Desktop", "smtp_password")
            except Exception:
                pass

        QMessageBox.information(self, "Success", "Configuration successfully saved and applied.")
        self.accept()
