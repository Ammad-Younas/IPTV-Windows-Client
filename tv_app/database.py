import sqlite3
import json
import os
from typing import List, Dict, Tuple

DB_PATH = "iptv_database.db"

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
        from playlist import Channel
        
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
        from playlist import Channel
        
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