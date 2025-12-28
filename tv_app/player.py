import sys
import vlc
from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import pyqtSignal

class VideoPlayer(QFrame):
    errorOccurred = pyqtSignal(str)
    stateChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        try:
            self.instance = vlc.Instance('--no-video-title-show', '--quiet')
            self.player = self.instance.media_player_new()
        except NameError:
             print("VLC not found or python-vlc not installed properly.")
             self.instance = None
             self.player = None

        self.setStyleSheet("background-color: black;")

    def set_media(self, url):
        if not self.instance:
            return
        
        media = self.instance.media_new(url)
        self.player.set_media(media)
        
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
