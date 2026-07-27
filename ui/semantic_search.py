import os
from PySide6.QtCore import Qt, Signal, Slot, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QFrame, QSlider, QStyle,
    QGridLayout, QMessageBox, QSizePolicy
)
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

class SearchResultCard(QFrame):
    card_selected = Signal(dict)

    def __init__(self, incident_data: dict):
        super().__init__()
        self.incident = incident_data
        self.setObjectName("cardFrame")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(160, 110)
        self.lbl_thumb.setAlignment(Qt.AlignCenter)
        self.lbl_thumb.setStyleSheet("background-color: #131314; border-radius: 0px; border: 1px solid #3A3F4B;")
        
        snap_path = self.incident.get("snapshot_path", "")
        if snap_path and os.path.exists(snap_path):
            pix = QPixmap(snap_path)
            self.lbl_thumb.setPixmap(pix.scaled(self.lbl_thumb.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.lbl_thumb.setText("🎥 No Feed")
            
        lbl_cam = QLabel(self.incident.get("camera_name", "Unknown Cam"))
        lbl_cam.setStyleSheet("font-weight: bold; color: #c3c6d1; font-size: 11px;")
        
        lbl_time = QLabel(self.incident.get("timestamp", ""))
        lbl_time.setStyleSheet("color: #c6c6cb; font-size: 10px;")
        
        sim_val = self.incident.get("similarity", 0.0) * 100.0
        lbl_sim = QLabel(f"Similarity: {sim_val:.1f}%")
        if sim_val >= 80:
            lbl_sim.setStyleSheet("font-weight: bold; color: #2D6A4F; font-size: 11px;")
        elif sim_val >= 50:
            lbl_sim.setStyleSheet("font-weight: bold; color: #D97706; font-size: 11px;")
        else:
            lbl_sim.setStyleSheet("color: #c6c6cb; font-size: 11px;")
            
        lbl_desc = QLabel(self.incident.get("explanation", ""))
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #c6c6cb; font-size: 10px;")
        lbl_desc.setMaximumHeight(35)
        
        layout.addWidget(self.lbl_thumb, 0, Qt.AlignCenter)
        layout.addWidget(lbl_cam)
        layout.addWidget(lbl_time)
        layout.addWidget(lbl_sim)
        layout.addWidget(lbl_desc)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.card_selected.emit(self.incident)


class SemanticSearchTab(QWidget):
    search_triggered = Signal(str)

    def __init__(self):
        super().__init__()
        self.current_media_path = ""
        self.init_ui()
        self.setup_player()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)
        
        search_layout = QHBoxLayout()
        self.edit_query = QLineEdit()
        self.edit_query.setPlaceholderText("Search indexed footage (e.g. 'person carrying box near window')")
        self.edit_query.setMinimumHeight(35)
        self.edit_query.returnPressed.connect(self._on_search_clicked)
        
        self.btn_search = QPushButton("🔍 Search")
        self.btn_search.setMinimumHeight(35)
        self.btn_search.setObjectName("accentButton")
        self.btn_search.clicked.connect(self._on_search_clicked)
        
        search_layout.addWidget(self.edit_query, 1)
        search_layout.addWidget(self.btn_search, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #131314; border: 1px solid #3A3F4B; border-radius: 0px;")
        
        self.results_container = QWidget()
        self.results_layout = QGridLayout(self.results_container)
        self.results_layout.setSpacing(10)
        self.results_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll_area.setWidget(self.results_container)
        
        left_panel.addLayout(search_layout)
        left_panel.addWidget(self.scroll_area, 1)

        right_panel = QVBoxLayout()
        right_panel.setSpacing(10)
        
        player_frame = QFrame()
        player_frame.setObjectName("cardFrame")
        player_layout = QVBoxLayout(player_frame)
        
        lbl_player_title = QLabel("📺 Integrated Footage Player")
        lbl_player_title.setObjectName("hudHeader")
        
        self.video_stack = QFrame()
        self.video_stack.setMinimumSize(400, 300)
        self.video_stack.setStyleSheet("background-color: #131314; border-radius: 0px; border: 1px solid #3A3F4B;")
        stack_layout = QVBoxLayout(self.video_stack)
        stack_layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.lbl_snap_viewer = QLabel()
        self.lbl_snap_viewer.setAlignment(Qt.AlignCenter)
        self.lbl_snap_viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lbl_snap_viewer.hide()
        
        stack_layout.addWidget(self.video_widget)
        stack_layout.addWidget(self.lbl_snap_viewer)
        
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        
        self.btn_play = QPushButton()
        self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.btn_play.clicked.connect(self._toggle_playback)
        
        self.slider_timeline = QSlider(Qt.Horizontal)
        self.slider_timeline.setRange(0, 0)
        self.slider_timeline.sliderMoved.connect(self._set_player_position)
        
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet("font-family: 'JetBrains Mono'; font-size: 11px; color: #c6c6cb;")
        
        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.slider_timeline, 1)
        controls_layout.addWidget(self.lbl_time)
        
        self.lbl_now_playing_desc = QLabel("No clip loaded.")
        self.lbl_now_playing_desc.setWordWrap(True)
        self.lbl_now_playing_desc.setStyleSheet("color: #e5e2e2; padding: 5px; font-weight: bold;")
        
        player_layout.addWidget(lbl_player_title)
        player_layout.addWidget(self.video_stack, 1)
        player_layout.addLayout(controls_layout)
        player_layout.addWidget(self.lbl_now_playing_desc)
        
        right_panel.addWidget(player_frame)

        main_layout.addLayout(left_panel, 3)
        main_layout.addLayout(right_panel, 2)

    def setup_player(self):
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        
        self.media_player.positionChanged.connect(self._on_player_position_changed)
        self.media_player.durationChanged.connect(self._on_player_duration_changed)
        self.media_player.playbackStateChanged.connect(self._on_player_state_changed)

    def _on_search_clicked(self):
        query = self.edit_query.text().strip()
        if not query:
            return
        self.btn_search.setEnabled(False)
        self.btn_search.setText("Searching...")
        self.search_triggered.emit(query)

    @Slot(list)
    def display_results(self, incidents: list):
        self.btn_search.setEnabled(True)
        self.btn_search.setText("🔍 Search")
        
        for i in reversed(range(self.results_layout.count())):
            widget = self.results_layout.itemAt(i).widget()
            if widget is not None:
                self.results_layout.removeWidget(widget)
                widget.setParent(None)
                
        if not incidents:
            lbl_none = QLabel("No incident footage matched your semantic search terms.")
            lbl_none.setStyleSheet("color: #777; font-style: italic;")
            self.results_layout.addWidget(lbl_none, 0, 0)
            return

        cols = 3
        for idx, inc in enumerate(incidents):
            card = SearchResultCard(inc)
            card.card_selected.connect(self.load_media)
            
            row = idx // cols
            col = idx % cols
            self.results_layout.addWidget(card, row, col)

    @Slot(dict)
    def load_media(self, incident: dict):
        snap_path = incident.get("snapshot_path", "")
        explanation = incident.get("explanation", "")
        self.current_media_path = snap_path
        
        self.lbl_now_playing_desc.setText(f"NOW PLAYING: {incident.get('camera_name')} - {explanation}")
        
        if snap_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
            self.video_widget.hide()
            self.lbl_snap_viewer.show()
            
            pix = QPixmap(snap_path)
            scaled_pix = pix.scaled(self.lbl_snap_viewer.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_snap_viewer.setPixmap(scaled_pix)
            
            self.media_player.stop()
            self.slider_timeline.setRange(0, 100)
            self.slider_timeline.setValue(100)
            self.lbl_time.setText("00:00 / 00:00")
            self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        else:
            self.lbl_snap_viewer.hide()
            self.video_widget.show()
            
            self.media_player.setSource(QUrl.fromLocalFile(snap_path))
            self.media_player.play()

    def _toggle_playback(self):
        if self.current_media_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
            return

        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def _set_player_position(self, position: int):
        self.media_player.setPosition(position)

    def _on_player_position_changed(self, position: int):
        self.slider_timeline.setValue(position)
        self._update_time_label(position, self.media_player.duration())

    def _on_player_duration_changed(self, duration: int):
        self.slider_timeline.setRange(0, duration)

    def _on_player_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def _update_time_label(self, position: int, duration: int):
        pos_sec = position // 1000
        dur_sec = duration // 1000
        
        pos_min = pos_sec // 60
        pos_sec = pos_sec % 60
        dur_min = dur_sec // 60
        dur_sec = dur_sec % 60
        
        self.lbl_time.setText(f"{pos_min:02d}:{pos_sec:02d} / {dur_min:02d}:{dur_sec:02d}")
        
    def resizeEvent(self, event):
        if self.lbl_snap_viewer.isVisible() and self.current_media_path:
            pix = QPixmap(self.current_media_path)
            scaled_pix = pix.scaled(self.lbl_snap_viewer.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_snap_viewer.setPixmap(scaled_pix)
        super().resizeEvent(event)
