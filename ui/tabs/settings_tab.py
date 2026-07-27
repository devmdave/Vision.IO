import time
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFrame, QSpinBox, QProgressBar,
    QMessageBox, QScrollArea, QStyle
)
from PySide6.QtGui import QAction
from utils import config

class KeyValidatorWorker(QThread):
    result_signal = Signal(bool, str)

    def __init__(self, provider, api_key, model, custom_url):
        super().__init__()
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.custom_url = custom_url

    def run(self):
        import httpx
        try:
            if self.provider == "Google Gemini":
                if not self.api_key:
                    self.result_signal.emit(False, "API Key is empty")
                    return
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
                resp = httpx.get(url, timeout=10.0)
                if resp.status_code == 200:
                    self.result_signal.emit(True, "Connected")
                else:
                    self.result_signal.emit(False, f"Invalid Key (Status {resp.status_code})")
            elif self.provider == "OpenAI":
                if not self.api_key:
                    self.result_signal.emit(False, "API Key is empty")
                    return
                url = "https://api.openai.com/v1/models"
                headers = {"Authorization": f"Bearer {self.api_key}"}
                resp = httpx.get(url, headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    self.result_signal.emit(True, "Connected")
                else:
                    self.result_signal.emit(False, f"Invalid Key (Status {resp.status_code})")
            else:  # Custom OpenAI-Compatible
                url = self.custom_url.rstrip('/')
                if not url:
                    self.result_signal.emit(False, "Custom URL is empty")
                    return
                
                # Deduce models list endpoint
                if not url.endswith("/models") and not url.endswith("/chat/completions"):
                    test_url = f"{url}/models"
                else:
                    test_url = url
                
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                resp = httpx.get(test_url, headers=headers, timeout=10.0)
                if resp.status_code in [200, 201]:
                    self.result_signal.emit(True, "Connected")
                elif resp.status_code in [401, 403]:
                    self.result_signal.emit(False, "Invalid Key / Unauthorized")
                else:
                    self.result_signal.emit(True, f"Connected (Status {resp.status_code})")
        except Exception as e:
            self.result_signal.emit(False, f"Error: {str(e)}")


class TelegramTestWorker(QThread):
    result_signal = Signal(bool, str)

    def __init__(self, token, chat_id):
        super().__init__()
        self.token = token
        self.chat_id = chat_id

    def run(self):
        try:
            from utils.notifications import send_telegram_alert
            msg = "⚡️ <b>Vision.IO Test Notification</b>\n\nYour alert integration has been successfully configured!"
            success = send_telegram_alert(self.token, self.chat_id, msg)
            if success:
                self.result_signal.emit(True, "Test alert sent!")
            else:
                self.result_signal.emit(False, "Send failed. Check parameters.")
        except Exception as e:
            self.result_signal.emit(False, f"Error: {str(e)}")


class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        
        self.temp_keys = {
            "Google Gemini": config.get_api_key("gemini_api_key"),
            "OpenAI": config.get_api_key("openai_api_key"),
            "Custom OpenAI-Compatible": config.get_api_key("custom_api_key")
        }
        self.telegram_token = config.get_api_key("telegram_bot_token")
        self.previous_provider = config.get_selected_provider()
        
        self.validator_worker = None
        self.telegram_worker = None
        
        self.init_ui()
        self.load_values()
        
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.update_usage_bar)
        self.refresh_timer.start(2000)

    def init_ui(self):
        # Outer Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(15)
        
        # --- Card 1: VLM Cloud API Configuration ---
        card1 = QFrame()
        card1.setObjectName("cardFrame")
        card1_layout = QVBoxLayout(card1)
        card1_layout.setContentsMargins(15, 15, 15, 15)
        card1_layout.setSpacing(12)
        
        lbl1_title = QLabel("☁️ VLM Cloud API Configuration")
        lbl1_title.setObjectName("hudHeader")
        card1_layout.addWidget(lbl1_title)
        
        provider_layout = QHBoxLayout()
        lbl_provider = QLabel("Cloud Provider:")
        lbl_provider.setMinimumWidth(120)
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Google Gemini", "OpenAI", "Custom OpenAI-Compatible"])
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(lbl_provider)
        provider_layout.addWidget(self.provider_combo, 1)
        card1_layout.addLayout(provider_layout)
        
        key_layout = QHBoxLayout()
        lbl_key = QLabel("API Key:")
        lbl_key.setMinimumWidth(120)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter provider API Key...")
        
        # Eye action for key
        self.action_toggle_key = QAction(self.api_key_input)
        self.action_toggle_key.setIcon(self.style().standardIcon(QStyle.SP_FileDialogInfoView))
        self.action_toggle_key.setToolTip("Show/Hide Key")
        self.api_key_input.addAction(self.action_toggle_key, QLineEdit.TrailingPosition)
        self.action_toggle_key.triggered.connect(self._toggle_api_key_visibility)
        
        key_layout.addWidget(lbl_key)
        key_layout.addWidget(self.api_key_input, 1)
        card1_layout.addLayout(key_layout)
        
        model_layout = QHBoxLayout()
        lbl_model = QLabel("Target VLM Model:")
        lbl_model.setMinimumWidth(120)
        self.model_combo = QComboBox()
        model_layout.addWidget(lbl_model)
        model_layout.addWidget(self.model_combo, 1)
        card1_layout.addLayout(model_layout)
        
        self.url_layout = QHBoxLayout()
        self.lbl_custom_url = QLabel("Custom Base URL:")
        self.lbl_custom_url.setMinimumWidth(120)
        self.custom_url_input = QLineEdit()
        self.custom_url_input.setPlaceholderText("e.g. http://localhost:8000/v1")
        self.url_layout.addWidget(self.lbl_custom_url)
        self.url_layout.addWidget(self.custom_url_input, 1)
        card1_layout.addLayout(self.url_layout)
        
        test_key_layout = QHBoxLayout()
        self.btn_test_key = QPushButton("Validate & Test Key")
        self.btn_test_key.setObjectName("accentButton")
        self.btn_test_key.clicked.connect(self._on_test_key)
        
        self.lbl_test_status = QLabel("")
        self.lbl_test_status.setStyleSheet("font-weight: bold;")
        
        test_key_layout.addWidget(self.btn_test_key)
        test_key_layout.addWidget(self.lbl_test_status, 1)
        card1_layout.addLayout(test_key_layout)
        
        content_layout.addWidget(card1)
        
        # --- Card 2: Cost & Budget Control ---
        card2 = QFrame()
        card2.setObjectName("cardFrame")
        card2_layout = QVBoxLayout(card2)
        card2_layout.setContentsMargins(15, 15, 15, 15)
        card2_layout.setSpacing(12)
        
        lbl2_title = QLabel("💸 Cost & Budget Control")
        lbl2_title.setObjectName("hudHeader")
        card2_layout.addWidget(lbl2_title)
        
        limit_layout = QHBoxLayout()
        lbl_limit = QLabel("Daily Limit:")
        lbl_limit.setMinimumWidth(120)
        self.daily_limit_box = QSpinBox()
        self.daily_limit_box.setRange(50, 5000)
        self.daily_limit_box.setValue(500)
        limit_layout.addWidget(lbl_limit)
        limit_layout.addWidget(self.daily_limit_box, 1)
        card2_layout.addLayout(limit_layout)
        
        usage_layout = QVBoxLayout()
        lbl_usage = QLabel("Daily API Usage:")
        self.daily_usage_bar = QProgressBar()
        self.daily_usage_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3A3F4B;
                border-radius: 0px;
                text-align: center;
                background-color: #131314;
                color: #e5e2e2;
                font-weight: bold;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #2D6A4F;
            }
        """)
        usage_layout.addWidget(lbl_usage)
        usage_layout.addWidget(self.daily_usage_bar)
        card2_layout.addLayout(usage_layout)
        
        content_layout.addWidget(card2)
        
        # --- Card 3: Notifications & Alert Integrations ---
        card3 = QFrame()
        card3.setObjectName("cardFrame")
        card3_layout = QVBoxLayout(card3)
        card3_layout.setContentsMargins(15, 15, 15, 15)
        card3_layout.setSpacing(12)
        
        lbl3_title = QLabel("🔔 Notifications & Alert Integrations")
        lbl3_title.setObjectName("hudHeader")
        card3_layout.addWidget(lbl3_title)
        
        tg_token_layout = QHBoxLayout()
        lbl_tg_token = QLabel("Telegram Bot Token:")
        lbl_tg_token.setMinimumWidth(120)
        self.telegram_token_input = QLineEdit()
        self.telegram_token_input.setEchoMode(QLineEdit.Password)
        self.telegram_token_input.setPlaceholderText("Enter Telegram Bot Token...")
        
        # Eye action for Telegram
        self.action_toggle_tg = QAction(self.telegram_token_input)
        self.action_toggle_tg.setIcon(self.style().standardIcon(QStyle.SP_FileDialogInfoView))
        self.action_toggle_tg.setToolTip("Show/Hide Token")
        self.telegram_token_input.addAction(self.action_toggle_tg, QLineEdit.TrailingPosition)
        self.action_toggle_tg.triggered.connect(self._toggle_tg_token_visibility)
        
        tg_token_layout.addWidget(lbl_tg_token)
        tg_token_layout.addWidget(self.telegram_token_input, 1)
        card3_layout.addLayout(tg_token_layout)
        
        tg_chat_layout = QHBoxLayout()
        lbl_tg_chat = QLabel("Telegram Chat ID:")
        lbl_tg_chat.setMinimumWidth(120)
        self.telegram_chat_id_input = QLineEdit()
        self.telegram_chat_id_input.setPlaceholderText("Enter Telegram Chat/Channel ID...")
        tg_chat_layout.addWidget(lbl_tg_chat)
        tg_chat_layout.addWidget(self.telegram_chat_id_input, 1)
        card3_layout.addLayout(tg_chat_layout)
        
        test_tg_layout = QHBoxLayout()
        self.btn_test_tg = QPushButton("Send Test Notification")
        self.btn_test_tg.clicked.connect(self._on_test_telegram)
        
        self.lbl_tg_status = QLabel("")
        self.lbl_tg_status.setStyleSheet("font-weight: bold;")
        
        test_tg_layout.addWidget(self.btn_test_tg)
        test_tg_layout.addWidget(self.lbl_tg_status, 1)
        card3_layout.addLayout(test_tg_layout)
        
        content_layout.addWidget(card3)
        
        # --- Save Settings Button ---
        self.btn_save = QPushButton("💾 Save Configuration")
        self.btn_save.setObjectName("successButton")
        self.btn_save.setMinimumHeight(45)
        self.btn_save.clicked.connect(self._on_save_settings)
        content_layout.addWidget(self.btn_save)
        
        content_layout.addStretch()
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def load_values(self):
        provider = config.get_selected_provider()
        idx = self.provider_combo.findText(provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        else:
            self.provider_combo.setCurrentIndex(0)
            
        # Fire change event to configure correct model items and visible fields
        self._on_provider_changed(self.provider_combo.currentText())
        
        self.custom_url_input.setText(config.get_custom_base_url())
        self.daily_limit_box.setValue(config.get_max_daily_api_calls())
        self.telegram_token_input.setText(self.telegram_token)
        self.telegram_chat_id_input.setText(config.get_telegram_chat_id())
        
        self.update_usage_bar()

    def update_usage_bar(self):
        limit = self.daily_limit_box.value()
        usage = config.get_daily_usage()
        
        self.daily_usage_bar.setMaximum(limit)
        self.daily_usage_bar.setValue(min(usage, limit))
        self.daily_usage_bar.setFormat(f"{usage} / {limit} calls made today")

    @Slot(str)
    def _on_provider_changed(self, provider: str):
        # Save key for previous provider
        if self.previous_provider != provider:
            self.temp_keys[self.previous_provider] = self.api_key_input.text()
            
        self.api_key_input.setText(self.temp_keys.get(provider, ""))
        
        self.model_combo.clear()
        if provider == "Google Gemini":
            self.model_combo.setEditable(False)
            self.model_combo.addItems(["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.6-flash"])
            self.custom_url_input.hide()
            self.lbl_custom_url.hide()
        elif provider == "OpenAI":
            self.model_combo.setEditable(False)
            self.model_combo.addItems(["gpt-4o-mini", "gpt-4o"])
            self.custom_url_input.hide()
            self.lbl_custom_url.hide()
        else: # Custom
            self.model_combo.setEditable(True)
            self.custom_url_input.show()
            self.lbl_custom_url.show()
            
        # Re-select stored model if available
        stored_model = config.get_selected_model()
        if provider == "Custom OpenAI-Compatible":
            self.model_combo.setEditText(stored_model)
        else:
            idx = self.model_combo.findText(stored_model)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
            else:
                self.model_combo.setCurrentIndex(0)
                
        self.previous_provider = provider
        self.lbl_test_status.setText("")

    def _toggle_api_key_visibility(self):
        if self.api_key_input.echoMode() == QLineEdit.Password:
            self.api_key_input.setEchoMode(QLineEdit.Normal)
        else:
            self.api_key_input.setEchoMode(QLineEdit.Password)

    def _toggle_tg_token_visibility(self):
        if self.telegram_token_input.echoMode() == QLineEdit.Password:
            self.telegram_token_input.setEchoMode(QLineEdit.Normal)
        else:
            self.telegram_token_input.setEchoMode(QLineEdit.Password)

    @Slot()
    def _on_test_key(self):
        provider = self.provider_combo.currentText()
        key = self.api_key_input.text().strip()
        model = self.model_combo.currentText().strip()
        custom_url = self.custom_url_input.text().strip()
        
        self.btn_test_key.setEnabled(False)
        self.lbl_test_status.setText("Testing key...")
        self.lbl_test_status.setStyleSheet("color: #aaaaaa;")
        
        self.validator_worker = KeyValidatorWorker(provider, key, model, custom_url)
        self.validator_worker.result_signal.connect(self._on_test_key_finished)
        self.validator_worker.start()

    @Slot(bool, str)
    def _on_test_key_finished(self, success: bool, msg: str):
        self.btn_test_key.setEnabled(True)
        if success:
            self.lbl_test_status.setText(f"✓ {msg}")
            self.lbl_test_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.lbl_test_status.setText(f"✗ {msg}")
            self.lbl_test_status.setStyleSheet("color: #F44336; font-weight: bold;")

    @Slot()
    def _on_test_telegram(self):
        token = self.telegram_token_input.text().strip()
        chat_id = self.telegram_chat_id_input.text().strip()
        
        if not token or not chat_id:
            QMessageBox.warning(self, "Integration Parameter Missing", "Please enter both Bot Token and Chat ID.")
            return
            
        self.btn_test_tg.setEnabled(False)
        self.lbl_tg_status.setText("Sending test...")
        self.lbl_tg_status.setStyleSheet("color: #aaaaaa;")
        
        self.telegram_worker = TelegramTestWorker(token, chat_id)
        self.telegram_worker.result_signal.connect(self._on_test_tg_finished)
        self.telegram_worker.start()

    @Slot(bool, str)
    def _on_test_tg_finished(self, success: bool, msg: str):
        self.btn_test_tg.setEnabled(True)
        if success:
            self.lbl_tg_status.setText(f"✓ {msg}")
            self.lbl_tg_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.lbl_tg_status.setText(f"✗ {msg}")
            self.lbl_tg_status.setStyleSheet("color: #F44336; font-weight: bold;")

    @Slot()
    def _on_save_settings(self):
        # Capture current key in input
        provider = self.provider_combo.currentText()
        self.temp_keys[provider] = self.api_key_input.text().strip()
        
        # Save providers
        config.set_selected_provider(provider)
        config.set_selected_model(self.model_combo.currentText().strip())
        config.set_custom_base_url(self.custom_url_input.text().strip())
        config.set_max_daily_api_calls(self.daily_limit_box.value())
        config.set_telegram_chat_id(self.telegram_chat_id_input.text().strip())
        
        # Save keys to keyring
        config.set_api_key("gemini_api_key", self.temp_keys.get("Google Gemini", ""))
        config.set_api_key("openai_api_key", self.temp_keys.get("OpenAI", ""))
        config.set_api_key("custom_api_key", self.temp_keys.get("Custom OpenAI-Compatible", ""))
        
        # Save telegram token
        tg_token = self.telegram_token_input.text().strip()
        config.set_api_key("telegram_bot_token", tg_token)
        self.telegram_token = tg_token
        
        self.update_usage_bar()
        QMessageBox.information(self, "Success", "Configuration successfully saved and applied.")
