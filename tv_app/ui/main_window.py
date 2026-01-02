from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QSplitter, QFrame, QComboBox, QSlider, QStyle, QFileDialog, QScrollArea, QLabel, QProgressBar
)
from PyQt6.QtCore import Qt, QSize, QTimer, QUrl, QThread, pyqtSignal, QRect
from PyQt6.QtGui import QIcon, QPainter, QColor, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import json
import requests
import sys

# API URLs (kept for backwards compatibility with old worker code)
LOGOS_URL = "https://iptv-org.github.io/api/logos.json"
COUNTRIES_URL = "https://iptv-org.github.io/api/countries.json"
STREAMS_URL = "https://iptv-org.github.io/api/streams.json"

from playlist import M3UParser, Channel
from player import VideoPlayer
from . import styles
from database import Database
from db_worker import DatabaseUpdateWorker

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


class StreamsWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, urls):
        super().__init__()
        self.urls = urls

    def run(self):
        try:
            channels = []
            response = requests.get(self.urls["streams"], timeout=25)
            response.raise_for_status()
            data = response.json()

            limit = 1200  # cap to keep UI responsive
            for idx, item in enumerate(data):
                if idx >= limit:
                    break

                name = item.get("title") or item.get("channel") or "Unknown"
                url = item.get("url")
                if not url:
                    continue

                tvg_id = item.get("channel")
                group = item.get("feed")
                logo = item.get("logo")

                channels.append(Channel(
                    name=name,
                    url=url,
                    logo=logo,
                    group=group,
                    tvg_id=tvg_id
                ))

            self.finished.emit(channels)
        except Exception as e:
            self.error.emit(str(e))




class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False) # Block input
        self.setStyleSheet("background-color: rgba(18, 18, 18, 240);")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        # Spinner/Progress Bar
        self.spinner = QProgressBar(self)
        self.spinner.setRange(0, 0) # Infinite/Marquee mode
        self.spinner.setFixedWidth(200)
        self.spinner.setFixedHeight(4)
        self.spinner.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #333;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 2px;
            }
        """)
        self.spinner.setTextVisible(False)
        layout.addWidget(self.spinner)
        
        # Loading Text
        self.label = QLabel("Loading...", self)
        self.label.setStyleSheet("color: white; font-size: 24px; font-weight: bold; background: transparent;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        # Info Text
        self.info_label = QLabel("Initializing...", self)
        self.info_label.setStyleSheet("color: #aaa; font-size: 14px; background: transparent;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)
        
    def set_message(self, msg):
        self.info_label.setText(msg)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IPTV Pro Player - Made by Ammad Younas")
        self.resize(1200, 800)
        
        self.channels = []
        self.channels = []
        self.is_loading_media = False
        
        # Playback Timer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_video_position)
        
        # Search Debounce Timer
        self.search_timer = QTimer(self)
        self.search_timer.setInterval(100) # 300ms delay
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.filter_channels)
        
        # Initialize UI
        self.setup_ui()
        self.apply_styles()
        
        # Database initialization
        self.db = Database()
        self.db.init_db()
        
        # Network Manager for Logos
        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self.on_image_loaded)
        self.pending_icon_requests = {} # reply -> button

        # Worker for async loading
        self.m3u_worker = None
        self.update_worker = None
        
        # Loading Overlay
        self.loading_overlay = LoadingOverlay(self)
        self.loading_overlay.resize(self.size())
        self.loading_overlay.hide()

        # Disable all buttons initially while database updates
        self.disable_all_buttons()
        
        # Kick off background database update shortly after UI shows
        QTimer.singleShot(50, self.start_database_update)

    def resizeEvent(self, event):
        if hasattr(self, 'loading_overlay'):
             self.loading_overlay.resize(self.size())
        super().resizeEvent(event)

    def disable_all_buttons(self):
        """Disable all interactive buttons during database update"""
    def disable_all_buttons(self):
        """Disable all interactive buttons during database update"""
        self.play_btn.setDisabled(True)
        self.category_combo.setDisabled(True)
        self.country_combo.setDisabled(True)
        self.search_input.setDisabled(True)
        self.search_input.setDisabled(True)

    def enable_all_buttons(self):
        """Enable all interactive buttons after database update"""
    def enable_all_buttons(self):
        """Enable all interactive buttons after database update"""
        self.play_btn.setDisabled(False)
        self.category_combo.setDisabled(False)
        self.country_combo.setDisabled(False)
        self.search_input.setDisabled(False)
        self.search_input.setDisabled(False)

    def start_database_update(self):
        """Start the database update worker"""
        if self.update_worker and self.update_worker.isRunning():
            return
        
        self.update_worker = DatabaseUpdateWorker(self.db)
        self.update_worker.progress.connect(self.on_database_progress)
        self.update_worker.finished.connect(self.on_database_update_finished)
        self.update_worker.error.connect(self.on_database_update_error)
        self.update_worker = DatabaseUpdateWorker(self.db)
        self.update_worker.progress.connect(self.on_database_progress)
        self.update_worker.finished.connect(self.on_database_update_finished)
        self.update_worker.error.connect(self.on_database_update_error)
        
        self.loading_overlay.show()
        self.loading_overlay.raise_()
        self.update_worker.start()

    def on_database_progress(self, message):
        self.loading_overlay.set_message(message)

    def on_database_update_finished(self):
        self.loading_overlay.hide()
        self.search_input.setPlaceholderText("Search channels...")
        self.enable_all_buttons()
        self.load_channels_from_db()
        self.populate_dropdowns_from_db()
        
        # Open Sidebar automatically
        self.scroll_area.show()
        self.toggle_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_ArrowRight))

    def on_database_update_error(self, error_msg):
        self.loading_overlay.hide()
        self.search_input.setPlaceholderText(f"Error: {error_msg}")
        self.enable_all_buttons()
        print(f"Database update error: {error_msg}")
        
        # Show sidebar anyway
        self.scroll_area.show()
        self.toggle_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_ArrowRight))

    def load_channels_from_db(self):
        try:
            self.channels = self.db.get_all_channels()
            self.refresh_ui_with_channels()
        except Exception as e:
            print(f"Error loading channels from database: {e}")

    def populate_dropdowns_from_db(self):
        try:
            categories = self.db.get_all_groups()
            self.category_combo.clear()
            self.category_combo.addItem("All Categories")
            self.category_combo.addItems(sorted(categories) if categories else [])
            
            countries = self.db.get_all_countries()
            self.country_combo.clear()
            self.country_combo.addItem("All Countries", "All")
            for name in countries:
                self.country_combo.addItem(name, name)
        except Exception as e:
            print(f"Error populating dropdowns: {e}")

    def load_streams(self):
        self.search_input.setPlaceholderText("Loading streams...")
        self.status_loading(True)

        if getattr(self, 'streams_worker', None) and self.streams_worker.isRunning():
            self.streams_worker.quit()
            self.streams_worker.wait()

        api_urls = {"streams": STREAMS_URL}
        self.streams_worker = StreamsWorker(api_urls)
        self.streams_worker.finished.connect(self.on_streams_loaded)
        self.streams_worker.error.connect(self.on_streams_error)
        self.streams_worker.start()



    def setup_ui(self):
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
        self.search_input.textChanged.connect(self.on_search_text_changed)
        top_layout.addWidget(self.search_input)

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
        
        # Hide sidebar by default
        self.scroll_area.hide()
        self.toggle_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_ArrowLeft))



    def apply_styles(self):
        self.setStyleSheet(styles.DARK_THEME)

    def load_channels(self):
        # Start streams only once, after reference data is (attempted) loaded
        if self.streams_started:
            return
        self.streams_started = True
        self.load_streams()

    def load_streams(self):
        self.search_input.setPlaceholderText("Loading streams...")
        self.status_loading(True)

        if getattr(self, 'streams_worker', None) and self.streams_worker.isRunning():
            self.streams_worker.quit()
            self.streams_worker.wait()

        api_urls = {"streams": STREAMS_URL}
        self.streams_worker = StreamsWorker(api_urls)
        self.streams_worker.finished.connect(self.on_streams_loaded)
        self.streams_worker.error.connect(self.on_streams_error)
        self.streams_worker.start()

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
        if hasattr(self, 'load_btn'):
            self.load_btn.setDisabled(False)
        
    def on_m3u_error(self, error_msg):
        self.status_loading(False)
        self.search_input.setPlaceholderText(f"Error: {error_msg}")
        print(f"Error loading M3U: {error_msg}")
        if hasattr(self, 'load_btn'):
            self.load_btn.setDisabled(False)

    def on_streams_loaded(self, channels):
        self.status_loading(False)
        self.channels = channels
        self.refresh_ui_with_channels()
        self.search_input.setPlaceholderText("Search channels...")

    def on_streams_error(self, error_msg):
        self.status_loading(False)
        self.search_input.setPlaceholderText(f"Error: {error_msg}")
        print(f"Error loading streams: {error_msg}")

    def on_playlist_loaded(self, channels):
        self.status_loading(False)
        self.channels = channels
        self.refresh_ui_with_channels()
        self.search_input.clear()
        if hasattr(self, 'load_btn'):
            self.load_btn.setDisabled(False)
        
    def on_playlist_error(self, error_msg):
        self.status_loading(False)
        print(f"Playlist Error: {error_msg}")
        self.search_input.setPlaceholderText("Error loading playlist")
        if hasattr(self, 'load_btn'):
            self.load_btn.setDisabled(False)

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
        """Refresh UI with current channels - populates categories from channels"""
        # Extract Categories from channels
        categories = set(ch.group for ch in self.channels if ch.group)
        self.category_combo.clear()
        self.category_combo.addItem("All Categories")
        self.category_combo.addItems(sorted(list(categories)))

        self.update_channel_list(self.channels)
        self.search_input.setPlaceholderText("Search")

    def on_search_text_changed(self):
        """Restart debounce timer on text change"""
        self.search_timer.start()

    def filter_channels(self):
        search_text = self.search_input.text().strip()
        category = self.category_combo.currentText()
        country = self.country_combo.currentData()
        
        # Query database with filters
        group_filter = None if category == "All Categories" else category
        country_filter = None if not country or country == "All" else country
        
        try:
            # Search database (search_channels handles partial text matching)
            self.channels = self.db.search_channels(search_text, group_filter, country_filter)
            self.update_channel_list(self.channels)
        except Exception as e:
            print(f"Error filtering channels: {e}")

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
                
                # Determine Logo URL from database
                logo_url = ch.logo
                
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
            
            # Play stream directly
            stream_url = channel.url
            self.play_video(stream_url)

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