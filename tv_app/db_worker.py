from PyQt6.QtCore import QThread, pyqtSignal
import requests
import os
import json
from database import Database

LOGOS_URL = "https://iptv-org.github.io/api/logos.json"
COUNTRIES_URL = "https://iptv-org.github.io/api/countries.json"
STREAMS_URL = "https://iptv-org.github.io/api/streams.json"

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
                # Only download if not exists (for local debugging) or always overwrite?
                # The user provides files in temp_data sometimes, so let's use them if they exist and are non-zero size
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    self.progress.emit(f"Using existing {key} file...")
                else:
                    self.progress.emit(f"Downloading {key}...")
                    try:
                        self.download_file(url, path)
                    except Exception as dl_err:
                        print(f"Failed to download {key}: {dl_err}")
                        # If channels.json fails (it's large), we proceed without it
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
                
                # Try finding via channel metadata
                if not country_code and tvg_id:
                    meta = channels_meta.get(tvg_id.lower())
                    if meta:
                        country_code = meta.get("country")
                
                # Try inferring from ID (e.g. US.HBO)
                if not country_code and tvg_id and "." in tvg_id:
                    parts = tvg_id.split(".")
                    # Heuristic: usually country is first or last part depending on convention, 
                    # but iptv-org often uses 'Country.Channel' or 'Channel.Country'
                    # iptv-org standard IDs often don't have country prefix directly unless custom.
                    # But often ID is 'us.hbo' -> 'us'
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
