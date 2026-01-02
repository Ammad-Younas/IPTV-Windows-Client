import sys
import os
import json
import sqlite3
import requests
from dataclasses import dataclass
from typing import List, Dict, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QSplitter, QFrame, QComboBox, QSlider, QStyle, 
    QScrollArea, QLabel, QProgressBar
)
from PyQt6.QtCore import Qt, QSize, QTimer, QUrl, QThread, pyqtSignal, QRect
from PyQt6.QtGui import QIcon, QPainter, QColor, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

# Setup Environment / Logging
os.environ["QT_LOGGING_RULES"] = "qt.gui.imageio*=false"

try:
    import vlc
except ImportError:
    vlc = None
    print("python-vlc not found. Player will not work.")


# CONSTANTS
DB_PATH = "iptv_database.db"
LOGOS_URL = "https://iptv-org.github.io/api/logos.json"
COUNTRIES_URL = "https://iptv-org.github.io/api/countries.json"
STREAMS_URL = "https://iptv-org.github.io/api/streams.json"


# STYLES
DARK_THEME = """
/* GLOBAL APPLICATION STYLES */
QMainWindow {
    background-color: #000000;
}

QWidget {
    font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
    font-size: 14px;
    color: #e0e0e0;
    selection-background-color: #333333;
    selection-color: #ffffff;
}

/* === CHANNEL CARDS (SIDEBAR ITEMS) === */
QPushButton#channelCard {
    background-color: #1e1e1e;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 5px 10px;
    text-align: left;
    color: #e0e0e0;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#channelCard:hover {
    background-color: #2a2a2a;
    border: 1px solid #ffffff;
    color: #ffffff;
}

QPushButton#channelCard:pressed {
    background-color: #333333;
}

/* === SIDEBAR & TOP BAR === */
QFrame {
    background-color: #121212;
    border: none;
}

QFrame#topBar {
    background-color: #0f0f0f;
    border-bottom: 1px solid #1a1a1a;
}

/* === SPLITTER === */
QSplitter::handle {
    background-color: #2b2b2b;
    width: 1px;
}

/* === INPUTS & COMBOBOXES === */
QLineEdit {
    background-color: #1e1e1e;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 10px 12px;
    color: #ffffff;
    font-size: 13px;
}

QLineEdit:focus {
    border: 1px solid #666666;
    background-color: #252525;
}

QComboBox {
    background-color: #1e1e1e;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 8px 12px;
    color: #ffffff;
    font-size: 13px;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #1e1e1e;
    color: #ffffff;
    border: 1px solid #333333;
    selection-background-color: #333333;
}

/* === LIST WIDGET === */
QListWidget {
    background-color: #121212;
    border: none;
    outline: none;
    padding-top: 10px;
}

QListWidget::item {
    padding: 14px 16px;
    border-bottom: 1px solid #1a1a1a;
    color: #b0b0b0;
    font-weight: 500;
}

QListWidget::item:hover {
    background-color: #1a1a1a;
    color: #ffffff;
}

QListWidget::item:selected {
    background-color: #1f1f1f;
    color: #ffffff;
    border-left: 3px solid #ffffff;
    padding-left: 13px;
}

/* === SCROLLBARS (Minimalist) === */
QScrollBar:vertical {
    border: none;
    background: #121212;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #333333;
    min-height: 30px;
    border-radius: 4px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background: #555555;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* === PLAYER AREA === */
QFrame#playerContainer {
    background-color: #000000;
}

/* Controls Bar */
QFrame#controlsFrame {
    background-color: #0f0f0f;
    border-top: 1px solid #1a1a1a;
}

/* === BUTTONS === */
QPushButton {
    background-color: transparent;
    border: none;
    border-radius: 6px;
    color: #ffffff;
    padding: 6px;
}

QPushButton:hover {
    background-color: #252525;
}

QPushButton:pressed {
    background-color: #333333;
}

/* Source specific buttons (Load/Folder) to look a bit more tactile */
QWidget > QPushButton { 
    font-size: 13px;
    font-weight: 600;
}

/* === CONTROLS BUTTONS === */
QFrame#controlsFrame QPushButton {
    background-color: transparent;
    border: none;
    border-radius: 15px;
    color: #ffffff;
    padding: 0px;
}

QFrame#controlsFrame QPushButton:hover {
    background-color: transparent;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

QFrame#controlsFrame QPushButton:pressed {
    background-color: rgba(255, 255, 255, 0.2);
}

/* Play Button (Hero) - No hover effect */
QPushButton#playButton {
    background-color: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.3);
}

QPushButton#playButton:hover {
    background-color: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.3);
}

QPushButton#playButton:pressed {
    background-color: rgba(255, 255, 255, 0.3);
}

/* === SLIDERS (Seek Bar) === */
QSlider::groove:horizontal {
    border: none;
    height: 4px;
    background: #333333;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #ffffff;
    border-radius: 2px;
}

QSlider::add-page:horizontal {
    background: #333333;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: none;
    width: 14px;
    height: 14px;
    margin: -5px 0; /* Center handle */
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #e6e6e6;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}
"""

# DATA STRUCTURES & PARSING
@dataclass
class Channel:
    name: str
    url: str
    logo: Optional[str] = None
    group: Optional[str] = None
    country: Optional[str] = None
    tvg_id: Optional[str] = None

class M3UParser:
    @staticmethod
    def parse(content: str) -> List[Channel]:
        channels = []
        lines = content.splitlines()
        
        current_channel = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("#EXTINF:"):
                # Basic parsing - improved regex could be used but sticking to string ops for now
                meta_part, _, name = line.partition(',')
                current_channel['name'] = name.strip()
                
                # Helper to extract attributes by key="value"
                def extract_attr(key, text):
                    pattern = f'{key}="'
                    if pattern in text:
                        start = text.find(pattern) + len(pattern)
                        end = text.find('"', start)
                        if end != -1:
                            return text[start:end]
                    return None

                current_channel['logo'] = extract_attr('tvg-logo', meta_part)
                current_channel['group'] = extract_attr('group-title', meta_part)
                current_channel['tvg_id'] = extract_attr('tvg-id', meta_part)
                # country_code removed per requirement
                
            elif not line.startswith("#"):
                if 'name' in current_channel:
                    channels.append(Channel(
                        name=current_channel['name'],
                        url=line,
                        logo=current_channel.get('logo'),
                        group=current_channel.get('group', 'Uncategorized'),
                        tvg_id=current_channel.get('tvg_id')
                    ))
                    current_channel = {}
                    
        return channels

    @staticmethod
    def parse_from_url(url: str) -> List[Channel]:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return M3UParser.parse(response.text)
        except Exception as e:
            print(f"Error loading playlist: {e}")
            return []

    @staticmethod
    def parse_from_file(path: str) -> List[Channel]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return M3UParser.parse(f.read())
        except Exception as e:
            print(f"Error reading playlist file: {e}")
            return []




# VIDEO PLAYER
class VideoPlayer(QFrame):
    errorOccurred = pyqtSignal(str)
    stateChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        try:
            # Setup VLC
            args = ['--no-video-title-show', '--quiet', '--mouse-hide-timeout=0']
            self.instance = vlc.Instance(*args) if vlc else None
            self.player = self.instance.media_player_new() if self.instance else None
        except Exception as e:
             print(f"VLC initialization error: {e}")
             self.instance = None
             self.player = None

        self.setStyleSheet("background-color: black;")

    def set_media(self, url):
        if not self.instance:
            return
        
        media = self.instance.media_new(url)
        self.player.set_media(media)
        
        if sys.platform.startswith('linux'):
            self.player.set_xwindow(self.winId())
        elif sys.platform == "win32":
             self.player.set_hwnd(self.winId())
        elif sys.platform == "darwin":
            self.player.set_nsobject(self.winId())

    def play(self):
        if self.player:
            if self.player.play() == -1:
                self.errorOccurred.emit("Failed to play media.")
            else:
                self.stateChanged.emit(True)

    def pause(self):
        if self.player:
            self.player.pause()
            
    def stop(self):
        if self.player:
            self.player.stop()
            self.stateChanged.emit(False)
            
    def set_volume(self, volume):
        if self.player:
            self.player.audio_set_volume(volume)

    def is_playing(self):
        if self.player:
            return self.player.is_playing()
        return False

    def get_position(self):
        if self.player:
            return self.player.get_position()
        return 0

    def set_position(self, position):
        if self.player:
            self.player.set_position(position)
            
    def get_time(self):
        if self.player:
            return self.player.get_time()
        return 0
        
    def get_length(self):
        if self.player:
            return self.player.get_length()
        return 0


# DATABASE
class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Schema Migration: Check if 'channels' exists and has 'country_code'
        try:
            cursor.execute("PRAGMA table_info(channels)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'country_code' in columns:
                print("Migrating schema: Dropping old channels table...")
                cursor.execute("DROP TABLE channels")
        except Exception as e:
            print(f"Error checking schema: {e}")
        
        # Countries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS countries (
                code TEXT PRIMARY KEY,
                name TEXT,
                data TEXT
            )
        ''')
        
        # Logos table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logos (
                id TEXT PRIMARY KEY,
                channel_id TEXT,
                name TEXT,
                url TEXT
            )
        ''')
        
        # Channels/Streams table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                logo TEXT,
                group_name TEXT,
                tvg_id TEXT,
                country_name TEXT,
                UNIQUE(name, url)
            )
        ''')
        
        # Index for faster searches
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_channel_name ON channels(name)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_channel_group ON channels(group_name)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_channel_country ON channels(country_name)
        ''')
        
        conn.commit()
        conn.close()

    def clear_all(self):
        """Clear all data from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM countries')
        cursor.execute('DELETE FROM logos')
        cursor.execute('DELETE FROM channels')
        conn.commit()
        conn.close()

    def insert_countries(self, countries: List[Dict]):
        """Insert countries into database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for item in countries:
            code = item.get('code') or item.get('alpha2')
            if code:
                cursor.execute('''
                    INSERT OR REPLACE INTO countries (code, name, data)
                    VALUES (?, ?, ?)
                ''', (code.upper(), item.get('name') or "Unknown", json.dumps(item)))
        
        conn.commit()
        conn.close()

    def insert_logos(self, logos: List[Dict]):
        """Insert logos into database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for item in logos:
            chan_id = item.get('id') or item.get('channel')
            url = item.get('url')
            name = item.get('name')
            
            if url and chan_id:
                cursor.execute('''
                    INSERT OR REPLACE INTO logos (id, channel_id, name, url)
                    VALUES (?, ?, ?, ?)
                ''', (chan_id, chan_id, name, url))
        
        conn.commit()
        conn.close()

    def insert_channels(self, channels: List[Dict]):
        """Insert channels/streams into database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for item in channels:
            # Streams format: title (name), channel (tvg_id), feed (group), url, optional countries
            name = item.get('title') or item.get('name') or item.get('channel')
            url = item.get('url')

            if not url or not name:
                continue

            tvg_id = item.get('channel') or item.get('id')
            group = item.get('feed') or item.get('category') or item.get('group')

            # Countries may come as list; take first
            country_code = item.get('country')
            if not country_code:
                countries = item.get('countries')
                if isinstance(countries, list) and countries:
                    country_code = countries[0]

            # Logo may be enriched earlier; fallback to provided keys
            logo = item.get('logo') or item.get('favicon')

            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO channels 
                    (name, url, logo, group_name, tvg_id, country_name)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, url, logo or "", group or "Uncategorized", tvg_id, item.get('country_name') or ""))
            except Exception as e:
                print(f"Error inserting channel {name}: {e}")
        
        conn.commit()
        conn.close()

    def search_channels(self, query: str = "", group: str = "", country: str = ""):
        """Search channels from database and return as Channel objects"""
        # Local imports removed
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        sql = "SELECT * FROM channels WHERE 1=1"
        params = []
        
        if query:
            sql += " AND (name LIKE ? OR tvg_id LIKE ?)"
            pattern = f"%{query}%"
            params.extend([pattern, pattern])
        
        if group and group != "All Categories":
            sql += " AND group_name = ?"
            params.append(group)
        
        if country and country != "All":
            sql += " AND country_name = ?"
            params.append(country)
        
        sql += " LIMIT 1000"
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        channels = []
        for row in rows:
            channels.append(Channel(
                name=row['name'],
                url=row['url'],
                logo=row['logo'],
                group=row['group_name'],
                country=row['country_name'],
                tvg_id=row['tvg_id']
            ))
        
        return channels

    def get_all_groups(self) -> List[str]:
        """Get all unique group names"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT group_name FROM channels WHERE group_name IS NOT NULL ORDER BY group_name")
        groups = [row[0] for row in cursor.fetchall()]
        conn.close()
        return groups

    def get_all_countries(self) -> List[str]:
        """Get all unique country names"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT country_name 
            FROM channels 
            WHERE country_name IS NOT NULL AND country_name != ''
            ORDER BY country_name
        """)
        rows = cursor.fetchall()
        conn.close()
        return [row['country_name'] for row in rows]

    def get_channel_count(self) -> int:
        """Get total number of channels in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM channels")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_all_channels(self, limit: int = 1000) -> List:
        """Get all channels from database as Channel objects"""
        # Local import removed
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        channels = []
        for row in rows:
            channels.append(Channel(
                name=row['name'],
                url=row['url'],
                logo=row['logo'],
                group=row['group_name'],
                country=row['country_name'],
                tvg_id=row['tvg_id']
            ))
        return channels


# WORKERS
class DatabaseUpdateWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, db=None):
        super().__init__()
        self.db = db if db else Database()

    def run(self):
        temp_dir = "temp_data"
        CHANNELS_API_URL = "https://iptv-org.github.io/api/channels.json"
        
        try:
            self.progress.emit("Starting update process...")
            
            # Create temp directory
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            self.db.clear_all()
            
            # --- 1. Download Files ---
            self.progress.emit("Downloading data files...")
            
            files = {
                "countries": (COUNTRIES_URL, os.path.join(temp_dir, "countries.json")),
                "logos": (LOGOS_URL, os.path.join(temp_dir, "logos.json")),
                "streams": (STREAMS_URL, os.path.join(temp_dir, "streams.json")),
                "channels": (CHANNELS_API_URL, os.path.join(temp_dir, "channels.json"))
            }
            
            for key, (url, path) in files.items():
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    self.progress.emit(f"Using existing {key} file...")
                else:
                    self.progress.emit(f"Downloading {key}...")
                    try:
                        self.download_file(url, path)
                    except Exception as dl_err:
                        print(f"Failed to download {key}: {dl_err}")
                        if key != "channels": 
                            raise dl_err

            # --- 2. Process Reference Data ---
            self.progress.emit("Processing reference data...")
            
            # Countries Map: code -> name
            countries_map = {}
            if os.path.exists(files["countries"][1]):
                with open(files["countries"][1], 'r', encoding='utf-8') as f:
                    countries_data = json.load(f)
                    self.db.insert_countries(countries_data)
                    for c in countries_data:
                        code = c.get("code") or c.get("alpha2")
                        name = c.get("name")
                        if code and name:
                            countries_map[code.upper()] = name

            # Logos Map: id/name -> url
            logo_map = {}
            if os.path.exists(files["logos"][1]):
                with open(files["logos"][1], 'r', encoding='utf-8') as f:
                    logos_data = json.load(f)
                    self.db.insert_logos(logos_data)
                    for item in logos_data:
                        chan_id = item.get("channel") or item.get("id")
                        name = item.get("name")
                        url = item.get("url")
                        if not url: continue
                        if chan_id: logo_map[chan_id.lower()] = url
                        if name: logo_map[name.lower()] = url

            # Channels Metadata Map: id -> {country, ...}
            channels_meta = {}
            if os.path.exists(files["channels"][1]):
                try:
                    with open(files["channels"][1], 'r', encoding='utf-8') as f:
                        channels_data = json.load(f)
                        for ch in channels_data:
                            cid = ch.get("id")
                            if cid:
                                channels_meta[cid.lower()] = ch
                except Exception as e:
                    print(f"Error loading channels.json: {e}")

            # --- 3. Process Streams ---
            self.progress.emit("Processing streams...")
            with open(files["streams"][1], 'r', encoding='utf-8') as f:
                streams = json.load(f)

            batch_size = 1000
            total = len(streams)
            batch = []
            
            for i, s in enumerate(streams):
                # 1. Strict Group Filter
                group = s.get("feed") or s.get("group")
                if not group:
                    continue # Skip if no group
                
                # Normalize keys
                tvg_id = s.get("channel") or s.get("id") or ""
                name = s.get("title") or s.get("name") or s.get("channel") or ""
                
                # 2. Enrich Logo
                logo = None
                if tvg_id and tvg_id.lower() in logo_map:
                    logo = logo_map[tvg_id.lower()]
                elif name and name.lower() in logo_map:
                    logo = logo_map[name.lower()]
                logo = logo or s.get("logo") or s.get("favicon") or ""

                # 3. Enrich Country
                country_code = s.get("country")
                
                if not country_code and tvg_id:
                    meta = channels_meta.get(tvg_id.lower())
                    if meta:
                        country_code = meta.get("country")
                
                if not country_code and tvg_id and "." in tvg_id:
                    parts = tvg_id.split(".")
                    potential = parts[0]
                    if len(potential) == 2 and potential.isalpha():
                        country_code = potential.upper()
                
                country_code = country_code or ""
                
                # Get Country Name
                country_name = ""
                if country_code:
                    country_name = countries_map.get(country_code.upper(), "")

                # 4. Prepare Record
                s["logo"] = logo
                s["group_name"] = group
                s["tvg_id"] = tvg_id
                s["country_name"] = country_name
                
                batch.append(s)
                
                if len(batch) >= batch_size:
                    self.db.insert_channels(batch)
                    batch = []
                    progress = int((i + 1) / total * 100)
                    self.progress.emit(f"Loading streams... {progress}%")
            
            # Insert remaining
            if batch:
                self.db.insert_channels(batch)
            
            self.progress.emit(f"Database updated successfully! ({total} source channels)")
            self.finished.emit()

        except Exception as e:
            self.error.emit(f"Update failed: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # --- 5. Clean up ---
            if os.path.exists(temp_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    print(f"Failed to clean up temp dir: {cleanup_error}")

    def download_file(self, url, path):
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)


# MAIN WINDOW & UI CLASSES
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
        self.streams_started = False
        
        # Playback Timer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_video_position)
        
        # Search Debounce Timer
        self.search_timer = QTimer(self)
        self.search_timer.setInterval(100) # 100ms delay
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
        self.streams_worker = None
        
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
        self.play_btn.setDisabled(True)
        self.category_combo.setDisabled(True)
        self.country_combo.setDisabled(True)
        self.search_input.setDisabled(True)

    def enable_all_buttons(self):
        """Enable all interactive buttons after database update"""
        self.play_btn.setDisabled(False)
        self.category_combo.setDisabled(False)
        self.country_combo.setDisabled(False)
        self.search_input.setDisabled(False)

    def start_database_update(self):
        """Start the database update worker"""
        if self.update_worker and self.update_worker.isRunning():
            return
        
        self.update_worker = DatabaseUpdateWorker(self.db)
        self.update_worker.progress.connect(self.on_database_progress)
        self.update_worker.finished.connect(self.on_database_update_finished)
        self.update_worker.error.connect(self.on_database_update_error)
        
        self.loading_overlay.show()
        self.loading_overlay.raise_()
        
        # Hide Sidebar during processing
        self.scroll_area.hide()
        self.toggle_btn.setIcon(self.get_icon(QStyle.StandardPixmap.SP_ArrowLeft))
        
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

        if self.streams_worker and self.streams_worker.isRunning():
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
        self.setStyleSheet(DARK_THEME)

    def load_channels(self):
        # Start streams only once, after reference data is (attempted) loaded
        if self.streams_started:
            return
        self.streams_started = True
        self.load_streams()

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


# MAIN ENTRY
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
