"""
FastAPI integration for receiving /add requests from extension or clipboard watcher.
Provides attach_downloader_instance helper for the GUI to register itself.
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import logging

from utils import is_valid_url, is_safe_url, log_error

logger = logging.getLogger(__name__)
app = FastAPI()

# Default CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

def attach_downloader_instance(downloader):
    app.state.app_instance = downloader

@app.post("/add")
async def add_video(request: Request):
    try:
        data = await request.json()
    except json.JSONDecodeError as exc:
        err = log_error(exc, "Invalid JSON in /add")
        raise HTTPException(status_code=400, detail={"error": "invalid_json", "message": str(err)})
    url = data.get("url", "").strip()
    if not url or not is_valid_url(url) or not is_safe_url(url):
        logger.warning("Rejected URL in /add: %s", url)
        raise HTTPException(status_code=400, detail={"error": "invalid_url", "message": "Invalid or unsafe URL"})

    app_instance = getattr(request.app.state, "app_instance", None)
    if not app_instance:
        logger.error("Downloader instance not attached")
        raise HTTPException(status_code=503, detail={"error": "no_gui", "message": "Downloader GUI is not running"})

    try:
        queued = app_instance.core.get_queued_urls()
        history_urls = {h["url"] for h in app_instance.history}
        if url in queued:
            return {"status": "already_in_queue", "url": url}
        if url in history_urls:
            return {"status": "already_downloaded", "url": url}

        # schedule in GUI thread safely
        app_instance.root.after(0, lambda: app_instance.add_to_queue(url=url, download_now=True))
        logger.info("Queued URL via API: %s", url)
        return {"status": "download_started", "url": url}
    except Exception as exc:
        err = log_error(exc, f"Failed to queue {url}")
        raise HTTPException(status_code=500, detail={"error": "server_error", "message": err})