import requests
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Channel:
    name: str
    url: str
    logo: Optional[str] = None
    group: Optional[str] = None
    country: Optional[str] = None

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
                
                meta_part, _, name = line.partition(',')
                current_channel['name'] = name.strip()
                
                if 'tvg-logo="' in meta_part:
                    logo_start = meta_part.find('tvg-logo="') + 10
                    logo_end = meta_part.find('"', logo_start)
                    current_channel['logo'] = meta_part[logo_start:logo_end]
                
                if 'group-title="' in meta_part:
                    group_start = meta_part.find('group-title="') + 13
                    group_end = meta_part.find('"', group_start)
                    current_channel['group'] = meta_part[group_start:group_end]
                
            elif not line.startswith("#"):
                if 'name' in current_channel:
                    channels.append(Channel(
                        name=current_channel['name'],
                        url=line,
                        logo=current_channel.get('logo'),
                        group=current_channel.get('group', 'Uncategorized')
                    ))
                    current_channel = {}
                    
        return channels

    @staticmethod
    def parse_from_url(url: str) -> List[Channel]:
        try:
            response = requests.get(url, timeout=10)
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

    @staticmethod
    def parse_from_directory(path: str) -> List[Channel]:
        import os
        channels = []
        valid_exts = ('.mp4', '.mkv', '.avi', '.ts', '.mov', '.webm')
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.lower().endswith(valid_exts):
                    full_path = os.path.join(root, file)
                    channels.append(Channel(
                        name=file,
                        url=f"file:///{full_path.replace(os.sep, '/')}",
                        group="Local Videos"
                    ))
        return channels
