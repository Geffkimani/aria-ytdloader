"""
Refactored database module:
- Uses WAL mode to reduce locking contention
- Thread-safe via a module-level lock
- Better error handling
"""
import sqlite3
import json
from typing import List, Dict, Any
import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = str(Path("ariadownloader.db").absolute())
_db_lock = threading.RLock()

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL UNIQUE,
                    title TEXT,
                    size TEXT,
                    filepath TEXT,
                    date TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_json TEXT NOT NULL
                )
            """)
            # Migrate: ensure 'size' column exists for history table
            cursor.execute("PRAGMA table_info(history)")
            cols = [r[1] for r in cursor.fetchall()]
            if 'size' not in cols:
                cursor.execute("ALTER TABLE history ADD COLUMN size TEXT")
            if 'filepath' not in cols:
                cursor.execute("ALTER TABLE history ADD COLUMN filepath TEXT")
            conn.commit()
        finally:
            conn.close()
    logger.info("Database initialized at %s", DB_PATH)

def add_history_item(item: Dict[str, Any]):
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO history (url, title, size, filepath, date, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (item["url"], item.get("title"), item.get("size"), item.get("filepath"), item["date"], item["status"]))
            conn.commit()
        finally:
            conn.close()

def get_history() -> List[Dict[str, Any]]:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT url, title, size, filepath, date, status FROM history ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

def clear_history():
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM history")
            conn.commit()
        finally:
            conn.close()
    logger.info("History cleared")

def save_queue(queue_items: List[Dict[str, Any]]):
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM queue")
            if queue_items:
                cursor.executemany("INSERT INTO queue (item_json) VALUES (?)", [(json.dumps(i),) for i in queue_items])
            conn.commit()
        finally:
            conn.close()

def get_queue() -> List[Dict[str, Any]]:
    with _db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT item_json FROM queue ORDER BY id ASC")
            return [json.loads(row["item_json"]) for row in cursor.fetchall()]
        finally:
            conn.close()