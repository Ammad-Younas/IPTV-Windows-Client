from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QSplitter, QFrame, QComboBox, QSlider, QStyle, QFileDialog, QScrollArea
)
from PyQt6.QtCore import Qt, QSize, QTimer, QUrl, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPainter, QColor, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import json
import requests
import sys

from playlist import M3UParser, Channel
from player import VideoPlayer
from . import styles
from yt_handler import YouTubeHandler

class PlaylistWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            channels = YouTubeHandler.parse_playlist(self.url)
            self.finished.emit(channels)
        except Exception as e:
            self.error.emit(str(e))

class M3UPlaylistWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            channels = M3UParser.parse_from_url(self.url)
            self.finished.emit(channels)
        except Exception as e:
            self.error.emit(str(e))

class StreamResolverWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            stream_url = YouTubeHandler.get_stream_url(self.url)
            if stream_url:
                self.finished.emit(stream_url)
            else:
                self.error.emit("Could not resolve stream URL")
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IPTV Pro Player - Made by Ammad Younas")
        self.resize(1200, 800)
        
        self.channels = []
        self.current_playlist_url = "https://iptv-org.github.io/iptv/index.m3u"
        self.is_loading_media = False
        
        # Playback Timer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_video_position)
        
        # Initialize UI
        self.setup_ui()
        self.apply_styles()
        
        # Data
        self.logo_map = {}
        self.country_map = {}
        self.load_reference_data()
        
        # Network Manager for Logos
        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.on_image_loaded)
        self.pending_icon_requests = {} # reply -> button

        # Worker for async loading
        self.m3u_worker = None
        
        # Load Default playlist asynchronously
        QTimer.singleShot(100, self.load_channels)

    def load_reference_data(self):
        # Load Countries
        try:
            with open('tv_app/data/countries.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    self.country_map[item['code'].upper()] = item
        except Exception as e:
            print(f"Error loading countries: {e}")

        # Load Logos
        try:
            with open('tv_app/data/logos.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    # Map by channel name (normalized if possible)
                    # The JSON has 'channel' key which usually matches tvg-id or name
                    if 'channel' in item and 'url' in item:
                        self.logo_map[item['channel'].lower()] = item['url']
        except Exception as e:
            print(f"Error loading logos: {e}")

    def load_from_url_input(self):
        url_text = self.url_input.text().strip()
        if not url_text:
            return

        # Check for YouTube
        if YouTubeHandler.is_youtube_url(url_text):
            # Check if playlist
            if "list=" in url_text:
                self.search_input.setText("Loading YouTube Playlist...")
                self.status_loading(True)
                
                self.playlist_worker = PlaylistWorker(url_text)
                self.playlist_worker.finished.connect(self.on_playlist_loaded)
                self.playlist_worker.error.connect(self.on_playlist_error)
                self.playlist_worker.start()
            else:
                self.channels = [Channel(name="YouTube Video", url=url_text, group="YouTube")]
                self.refresh_ui_with_channels()
                self.play_channel(self.channels[0])
            return

        if url_text.endswith(".m3u") or url_text.endswith(".m3u8"):
            # Load from URL
            parser = M3UParser()
            try:
                # We need to fetch it first.
                response = requests.get(url_text, timeout=30)
                if response.status_code == 200:
                    self.channels = parser.parse(response.text)
                    self.refresh_ui_with_channels()
            except Exception as e:
                print(f"Error loading URL: {e}")
        else:
             pass

    def setup_ui(self):
        # Main Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === TOP BAR ===
        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(60)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 5, 20, 5)
        top_layout.setSpacing(15)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Channels")
        self.search_input.setFixedWidth(300)
        self.search_input.textChanged.connect(self.filter_channels)
        top_layout.addWidget(self.search_input)

        # URL Input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://...")
        self.url_input.setFixedWidth(400)
        self.url_input.setText(self.current_playlist_url)
        top_layout.addWidget(self.url_input)

        # Load Button
        load_btn = QPushButton("Load URL")
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.clicked.connect(self.load_from_url_input)
        load_btn.setStyleSheet("background-color: #2a2a2a; padding: 6px 12px; font-weight: bold;")
        top_layout.addWidget(load_btn)

        # Category Filter
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories")
        self.category_combo.setFixedWidth(160)
        self.category_combo.currentTextChanged.connect(self.filter_channels)
        top_layout.addWidget(self.category_combo)

        # Country Filter
        self.country_combo = QComboBox()
        self.country_combo.addItem("All Countries")
        self.country_combo.setFixedWidth(160)
        self.country_combo.currentTextChanged.connect(self.filter_channels)
        top_layout.addWidget(self.country_combo)

        top_layout.addStretch()

        # Folder Button
        folder_btn = QPushButton(" Browse Folder")
        folder_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_DirOpenIcon))
        folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        folder_btn.clicked.connect(self.browse_folder)
        folder_btn.setStyleSheet("font-weight: bold; padding: 6px 12px;")
        top_layout.addWidget(folder_btn)

        # Sidebar Toggle Button - Changed to Right Arrow
        self.toggle_btn = QPushButton()
        self.toggle_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_ArrowRight))
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        self.toggle_btn.setFixedSize(35, 35)
        top_layout.addWidget(self.toggle_btn)

        main_layout.addWidget(top_bar)

        # === CONTENT BODY (Horizontal Splitter: Player Left | Sidebar Right) ===
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setHandleWidth(2)
        self.content_splitter.setStyleSheet("QSplitter::handle { background-color: #222; }")
        
        # --- LEFT: PLAYER AREA (with vertical splitter inside) ---
        # Create a vertical splitter for the player area
        self.player_splitter = QSplitter(Qt.Orientation.Vertical)
        self.player_splitter.setHandleWidth(2)
        self.player_splitter.setStyleSheet("QSplitter::handle { background-color: #222; }")
        
        player_frame = QFrame()
        player_frame.setObjectName("playerContainer")
        player_frame.setStyleSheet("background-color: black;")
        player_layout = QVBoxLayout(player_frame)
        player_layout.setContentsMargins(0, 0, 0, 0)
        player_layout.setSpacing(0)

        # Video Player
        self.video_player = VideoPlayer()
        player_layout.addWidget(self.video_player, 1)

        self.player_splitter.addWidget(player_frame)
        
        # Controls Container (in the vertical splitter)
        controls_container = QFrame()
        controls_container.setObjectName("controlsFrame")
        controls_container.setStyleSheet("background-color: #0d0d0d;")
        controls_container.setMinimumHeight(70)
        
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setContentsMargins(15, 5, 15, 5)
        controls_layout.setSpacing(10)
        
        # Seek Bar
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.seek_slider.setFixedHeight(15) 
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 2px; background: #333; }
            QSlider::handle:horizontal { width: 10px; height: 10px; margin: -4px 0; border-radius: 5px; background: white; }
        """)
        self.seek_slider.sliderPressed.connect(self.seek_started)
        self.seek_slider.sliderReleased.connect(self.seek_finished)
        controls_layout.addWidget(self.seek_slider)

        # Buttons Row
        btns_row = QHBoxLayout()
        btns_row.setContentsMargins(0, 0, 0, 0)
        btns_row.setSpacing(15)
        
        self.play_btn = QPushButton()
        self.play_btn.setObjectName("playButton")
        self.play_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_btn.setFixedSize(30, 30)
        self.play_btn.setIconSize(QSize(16, 16))
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.clicked.connect(self.toggle_play)
        btns_row.addWidget(self.play_btn)

        
        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_btn.setFixedSize(30, 30)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self.stop_playback)
        btns_row.addWidget(self.stop_btn)

        self.vol_btn = QPushButton()
        self.vol_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_MediaVolume))
        self.vol_btn.setFixedSize(30, 30)
        self.vol_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vol_btn.clicked.connect(self.toggle_mute)
        btns_row.addWidget(self.vol_btn)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.volume_slider.valueChanged.connect(self.change_volume)
        btns_row.addWidget(self.volume_slider)

        btns_row.addStretch()

        self.fs_btn = QPushButton()
        self.fs_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_TitleBarMaxButton))
        self.fs_btn.setFixedSize(30, 30)
        self.fs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fs_btn.clicked.connect(self.toggle_fullscreen)
        btns_row.addWidget(self.fs_btn)

        controls_layout.addLayout(btns_row)
        self.player_splitter.addWidget(controls_container)
        
        # Set initial sizes for player splitter (player takes most space, controls fixed)
        self.player_splitter.setSizes([730, 70])
        
        self.content_splitter.addWidget(self.player_splitter)

        # --- RIGHT: SIDEBAR (Channel Shelf) ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("border: none; background-color: #121212; border-left: 1px solid #222;")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: #121212;")
        # Vertical Layout for Sidebar
        self.card_layout = QVBoxLayout(self.scroll_content)
        self.card_layout.setContentsMargins(10, 10, 10, 10)
        self.card_layout.setSpacing(10)
        self.card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.scroll_content)
        self.content_splitter.addWidget(self.scroll_area)
        
        # Initial Sizes (approx 75% | 25%)
        self.content_splitter.setSizes([900, 300])

        main_layout.addWidget(self.content_splitter)



    def apply_styles(self):
        self.setStyleSheet(styles.DARK_THEME)

    def load_channels(self):
        # Initial load - async
        self.load_from_url(self.current_playlist_url)

    def load_from_url(self, url):
        self.search_input.setPlaceholderText("Loading...")
        self.status_loading(True)
        
        # Load asynchronously using worker thread
        if self.m3u_worker and self.m3u_worker.isRunning():
            self.m3u_worker.quit()
            self.m3u_worker.wait()
        
        self.m3u_worker = M3UPlaylistWorker(url)
        self.m3u_worker.finished.connect(self.on_m3u_loaded)
        self.m3u_worker.error.connect(self.on_m3u_error)
        self.m3u_worker.start()
        
    def on_m3u_loaded(self, channels):
        self.status_loading(False)
        self.channels = channels
        self.refresh_ui_with_channels()
        self.search_input.setPlaceholderText("Search channels...")
        
    def on_m3u_error(self, error_msg):
        self.status_loading(False)
        self.search_input.setPlaceholderText(f"Error: {error_msg}")
        print(f"Error loading M3U: {error_msg}")
    
    def on_playlist_loaded(self, channels):
        self.status_loading(False)
        self.channels = channels
        self.refresh_ui_with_channels()
        self.search_input.clear()
        
    def on_playlist_error(self, error_msg):
        self.status_loading(False)
        print(f"Playlist Error: {error_msg}")
        self.search_input.setPlaceholderText("Error loading playlist")

    def browse_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Folder", "")
        if dir_path:
            self.status_loading(True)
            QApplication.processEvents()
            
            all_channels = M3UParser.parse_from_directory(dir_path)
            self.channels = all_channels
            self.refresh_ui_with_channels()

    def status_loading(self, loading):
        # We can disable search or show spinner later
        pass

    def refresh_ui_with_channels(self):
        # Extract Categories
        categories = set(ch.group for ch in self.channels if ch.group)
        self.category_combo.clear()
        self.category_combo.addItem("All Categories")
        self.category_combo.addItems(sorted(list(categories)))
        
        # Extract Countries
        countries = set()
        for ch in self.channels:
            if ch.country_code:
                countries.add(ch.country_code)
        
        # Sort countries by name if available
        country_items = []
        for code in countries:
            display_name = code
            if code.upper() in self.country_map:
                c_data = self.country_map[code.upper()]
                display_name = f"{c_data['name']}"
            country_items.append((display_name, code))
            
        country_items.sort(key=lambda x: x[0])
        
        self.country_combo.clear()
        self.country_combo.addItem("All Countries", "All")
        for disp, code in country_items:
            self.country_combo.addItem(disp, code)

        self.update_channel_list(self.channels)
        self.search_input.setPlaceholderText("Search")

    def filter_channels(self):
        search_text = self.search_input.text().lower()
        category = self.category_combo.currentText()
        country_code = self.country_combo.currentData()
        
        filtered = []
        for ch in self.channels:
            matches_search = search_text in ch.name.lower()
            matches_category = category == "All Categories" or ch.group == category
            
            matches_country = True
            if country_code and country_code != "All":
                matches_country = ch.country_code == country_code
            
            if matches_search and matches_category and matches_country:
                filtered.append(ch)
        
        self.update_channel_list(filtered)

    def load_icon_async(self, url, button):
        if not url:
            return
            
        # Check cache or simple request
        req = QNetworkRequest(QUrl(url))
        req.setAttribute(QNetworkRequest.Attribute.Http2AllowedAttribute, False)
        reply = self.nam.get(req)
        self.pending_icon_requests[reply] = button

    def on_image_loaded(self, reply):
        button = self.pending_icon_requests.pop(reply, None)
        if button and reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                try:
                    icon = QIcon(pixmap)
                    button.setIcon(icon)
                except RuntimeError:
                    pass
        reply.deleteLater()

    def seek_started(self):
        self.timer.stop()

    def seek_finished(self):
        pos = self.seek_slider.value() / 1000.0
        self.video_player.set_position(pos)
        self.timer.start()

    def update_video_position(self):
        if self.video_player.is_playing() and not self.seek_slider.isSliderDown():
            pos = self.video_player.get_position()
            self.seek_slider.setValue(int(pos * 1000))

    def update_channel_list(self, channels):
        # Clear pending requests map to avoid holding references to deleted buttons
        self.pending_icon_requests.clear()

        # Clear existing items
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Process in batches to keep UI responsive
        limit = 500
        batch_size = 50
        
        def add_batch(start_idx):
            end_idx = min(start_idx + batch_size, len(channels), limit)
            
            for i in range(start_idx, end_idx):
                ch = channels[i]
                
                # Create Card Button
                btn = QPushButton(f"  {ch.name}")
                btn.setObjectName("channelCard")
                btn.setFixedHeight(50) 
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                
                # Determine Logo URL
                logo_url = ch.logo
                if not logo_url:
                    if ch.tvg_id and ch.tvg_id.lower() in self.logo_map:
                        logo_url = self.logo_map[ch.tvg_id.lower()]
                    elif ch.name.lower() in self.logo_map:
                        logo_url = self.logo_map[ch.name.lower()]
                
                if logo_url:
                    btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_FileIcon))
                    self.load_icon_async(logo_url, btn)
                else:
                    btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_FileIcon))
                
                btn.setIconSize(QSize(32, 32))
                btn.clicked.connect(lambda checked, c=ch: self.play_channel(c))
                self.card_layout.addWidget(btn)
            
            # Schedule next batch
            if end_idx < len(channels) and end_idx < limit:
                QTimer.singleShot(10, lambda idx=end_idx: add_batch(idx))
        
        # Start processing batches
        if channels:
            add_batch(0)

    def play_channel(self, channel):
        if channel and not self.is_loading_media:
            self.is_loading_media = True
            print(f"Playing: {channel.name} -> {channel.url}")
            
            # Resolve stream URL
            stream_url = channel.url
            if YouTubeHandler.is_youtube_url(stream_url):
                self.play_btn.setDisabled(True)
                self.search_input.setPlaceholderText("Resolving YouTube URL...")
                
                self.current_resolving_worker = StreamResolverWorker(stream_url)
                self.current_resolving_worker.finished.connect(lambda url: self.on_stream_resolved(url))
                self.current_resolving_worker.error.connect(self.on_resolve_error)
                self.current_resolving_worker.start()
                return

            self.play_video(stream_url)

    def on_stream_resolved(self, stream_url):
        self.play_btn.setDisabled(False)
        self.search_input.setPlaceholderText("Search")
        print(f"Resolved YouTube Stream: {stream_url}")
        self.play_video(stream_url)

    def on_resolve_error(self, error):
        self.is_loading_media = False
        self.play_btn.setDisabled(False)
        self.search_input.setPlaceholderText("Error resolving URL")
        print(f"Resolve Error: {error}")

    def play_video(self, url):
        # Stop current playback
        self.video_player.stop()
        self.timer.stop()
        QApplication.processEvents()
        
        # Set new media and play
        self.video_player.set_media(url)
        
        # Small delay to let VLC process the media
        QTimer.singleShot(100, lambda: self._start_playback())
    
    def _start_playback(self):
        self.video_player.play()
        self.timer.start()
        self.play_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_MediaPause))
        self.is_loading_media = False

    def change_volume(self, value):
        self.video_player.set_volume(value)

    def get_icon(self, standard_pixmap):
        icon = self.style().standardIcon(standard_pixmap)
        pixmap = icon.pixmap(32, 32)
        if not pixmap.isNull():
            new_pixmap = pixmap.copy()
            new_pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(new_pixmap)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(new_pixmap.rect(), QColor("white"))
            painter.end()
            return QIcon(new_pixmap)
        return icon

    def toggle_play(self):
        if self.video_player.is_playing():
            self.video_player.pause()
            self.timer.stop()
            self.play_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_MediaPlay))
        else:
            self.video_player.play()
            self.timer.start()
            self.play_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_MediaPause))

    def stop_playback(self):
        self.video_player.stop()
        self.timer.stop()
        self.seek_slider.setValue(0)
        self.play_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_MediaPlay))

    def toggle_mute(self):
        if self.video_player.player.audio_get_mute():
            self.video_player.player.audio_set_mute(False)
            self.vol_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_MediaVolume))
        else:
            self.video_player.player.audio_set_mute(True)
            self.vol_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_MediaVolumeMuted))

    def toggle_sidebar(self):
        # Toggle sidebar visibility and update icon
        if self.scroll_area.isVisible():
            self.scroll_area.hide()
            self.toggle_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_ArrowLeft))
        else:
            self.scroll_area.show()
            self.toggle_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_ArrowRight))

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.scroll_area.show()
            self.toggle_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_ArrowRight))
        else:
            self.showFullScreen()
            self.scroll_area.hide()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())