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