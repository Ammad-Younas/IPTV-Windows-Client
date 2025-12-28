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
    tvg_id: Optional[str] = None
    country_code: Optional[str] = None

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
                current_channel['country_code'] = extract_attr('tvg-country', meta_part)
                
                # Fallback: Extract country from tvg-id if not explicitly provided
                # Format often: "ChannelName.XX" or "ChannelName.XX@..."
                if not current_channel['country_code'] and current_channel['tvg_id']:
                    tid = current_channel['tvg_id']
                    # Check for pattern .XX (where XX is 2 chars)
                    # May handle .XX@...
                    parts = tid.split('.')
                    if len(parts) > 1:
                        potential_code = parts[-1]
                        if '@' in potential_code:
                            potential_code = potential_code.split('@')[0]
                        
                        if len(potential_code) == 2 and potential_code.isalpha():
                            current_channel['country_code'] = potential_code
                
            elif not line.startswith("#"):
                if 'name' in current_channel:
                    channels.append(Channel(
                        name=current_channel['name'],
                        url=line,
                        logo=current_channel.get('logo'),
                        group=current_channel.get('group', 'Uncategorized'),
                        tvg_id=current_channel.get('tvg_id'),
                        country_code=current_channel.get('country_code')
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
