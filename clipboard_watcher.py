"""
Clipboard watcher that posts detected URLs to downloader API.
- Uses a seen file to avoid duplicates
- Respects env var DOWNLOADER_API
"""
import os
import time
import json
import pyperclip
import requests
from pathlib import Path
from datetime import datetime
import logging

from utils import is_valid_url, notify, log_error

logger = logging.getLogger(__name__)

SEEN_FILE = Path("seen_clipboard.json")
CHECK_INTERVAL = float(os.environ.get("CLIPBOARD_CHECK_INTERVAL", "2"))
DOWNLOADER_API = os.environ.get("DOWNLOADER_API", "http://127.0.0.1:5000/add")

def load_seen() -> dict:
    if not SEEN_FILE.exists():
        return {}
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        logger.exception("Failed to load seen file")
        return {}

def save_seen(seen: dict):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(seen, f, indent=2)
    except Exception:
        logger.exception("Failed to save seen file")

def send_to_downloader(url: str):
    try:
        resp = requests.post(DOWNLOADER_API, json={"url": url}, timeout=5)
        resp.raise_for_status()
        result = resp.json()
        if result.get("status") == "download_started":
            logger.info("Sent to downloader: %s", url)
            notify("Clipboard Download Queued", url)
        else:
            logger.info("Downloader response: %s", result)
    except Exception as e:
        logger.exception("Error sending to downloader")
        notify("Clipboard Error", "Could not contact downloader")

def main():
    seen = load_seen()
    last = ""
    logger.info("Clipboard watcher started")
    try:
        while True:
            try:
                txt = pyperclip.paste().strip()
            except Exception:
                txt = ""
            if txt and txt != last and is_valid_url(txt) and txt not in seen:
                seen[txt] = datetime.utcnow().isoformat()
                save_seen(seen)
                send_to_downloader(txt)
                last = txt
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        if __name__ == "__main__":
    main()