# IPTV Player

A custom IPTV player application built using Python, PyQt6, and VLC.

## Features

- **Modern UI**: Clean and responsive interface built with PyQt6.
- **VLC Integration**: Reliable media playback using the VLC engine.
- **Playlist Support**: Load and manage M3U playlists.
- **Channel Parsing**: Efficiently parses channel information including logos and groups.

## Prerequisites

Before running the application, ensure you have the following installed:

1. **Python 3.x**: [Download Python](https://www.python.org/downloads/)
2. **VLC Media Player**: The `python-vlc` binding requires the actual VLC media player to be installed on your system. [Download VLC](https://www.videolan.org/vlc/)

## Installation

1.  Clone functionality or download the source code.
2.  Install the required Python dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

To run the application, execute the `main.py` script from the project root directory:

```bash
python tv_app/main.py
```

## Structure

- `tv_app/`: Main application source code.
  - `main.py`: Entry point of the application.
  - `player.py`: Handles video playback logic.
  - `playlist.py`: Manages playlist parsing and storage.
  - `ui/`: Contains UI components and styles.

## Acknowledgements

- Shoutout to [iptv-org](https://github.com/iptv-org/iptv) for the comprehensive collection of publicly available IPTV channels.
