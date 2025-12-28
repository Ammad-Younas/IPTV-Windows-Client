import yt_dlp
from typing import List, Optional, Dict
from playlist import Channel

class YouTubeHandler:
    @staticmethod
    def is_youtube_url(url: str) -> bool:
        return "youtube.com" in url or "youtu.be" in url

    @staticmethod
    def get_stream_url(url: str) -> Optional[str]:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get('url')
        except Exception as e:
            print(f"Error fetching YouTube stream: {e}")
            return None

    @staticmethod
    def parse_playlist(url: str) -> List[Channel]:
        channels = []
        ydl_opts = {
            'extract_flat': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info and 'entries' in info:
                    for entry in info['entries']:
                        if entry:
                            # Construct video URL
                            vid_url = entry.get('url')
                            if not vid_url:
                                vid_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                            
                            channels.append(Channel(
                                name=entry.get('title', 'Unknown Video'),
                                url=vid_url,
                                logo=entry.get('thumbnail'),
                                group='YouTube'
                            ))
        except Exception as e:
            print(f"Error parsing YouTube playlist: {e}")
        
        return channels
