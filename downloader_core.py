"""
Core module for handling downloads, from queueing to execution.

This module provides the main components for the download engine:
- DownloadItem: A dataclass to hold information about a specific download.
- YtDlpParser: A utility class to parse output from yt-dlp and aria2c.
- DownloadProcess: A wrapper for running and managing the yt-dlp subprocess.
- DownloaderCore: The main engine that manages a queue of downloads,
  concurrent workers, and communication with the rest of the application.
"""
import os
import re
import logging
import threading
import subprocess
import signal
from dataclasses import dataclass, field, asdict
from datetime import datetime
from queue import Queue, Empty
from typing import Optional, List, Dict, Callable

import database
from utils import YT_DLP_PATH, ARIA2C_PATH, notify

logger = logging.getLogger(__name__)


@dataclass
class DownloadItem:
    """
    Represents a single item to be downloaded.

    Attributes:
        url (str): The source URL of the video or media.
        quality (str): The desired quality (e.g., "720p", "1080p").
        audio_only (bool): If True, download only the audio.
        embed_thumbnail (bool): If True, embed thumbnail in audio file.
        format_id (Optional[str]): Specific yt-dlp format ID to use.
        title (str): The title of the media.
        from_playlist (bool): If True, indicates the item is part of a playlist.
        command (Optional[List[str]]): The exact command to execute.
        status (str): The current status of the download (e.g., "Queued").
        created_at (str): ISO format timestamp of when the item was created.
        filepath (Optional[str]): The final absolute path of the downloaded file.
        size (Optional[str]): The total size of the file as a string (e.g., "10.5MiB").
    """
    url: str
    quality: str = "720p"
    audio_only: bool = False
    embed_thumbnail: bool = False
    format_id: Optional[str] = None
    title: str = "Fetching title..."
    from_playlist: bool = False
    command: Optional[List[str]] = None
    status: str = "Queued"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    filepath: Optional[str] = None
    size: Optional[str] = None


class YtDlpParser:
    """
    A utility class for parsing output from yt-dlp and its external downloader, aria2c.

    This class uses regex to extract progress, metadata, and status updates from
    the stdout of the download process.
    """
    # Example: [download] 35.2% of 5.73MiB at 1.37MiB/s ETA 00:15
    YT_DLP_PROGRESS = re.compile(
        r'\s*\[download\]\s+'
        r'(?P<percent>[\d\.]+)\s*\%\s+of\s+'
        r'(?P<size>[\d\.]+\w+)\s+'
        r'at\s+(?P<speed>[\d\.]+\w*(?:/s)?)\s+'
        r'ETA\s+(?P<eta>[\w:]+)'
    )
    # Example: [#2e5c86 4.0MiB/5.7MiB(70%) CN:3 DL:1.6MiB/s ETA:5s]
    ARIA2C_PROGRESS = re.compile(
        r'\s*\[#\w+\s+'
        r'(?P<downloaded>[\d\.]+\w+)\/(?P<total>[\d\w\.]+)\((?P<percent>\d+)%\)\s+'
        r'CN:\d+\s+DL:(?P<speed>[\d\.]+\w+(?:/s)?)\s+'
        r'ETA:(?P<eta>[\w:]+)\]'
    )
    DESTINATION = re.compile(r"\[download\]\s+Destination:\s+(?P<path>.*)")
    MERGED = re.compile(r'\[Merger\]\s+Merging formats into "(?P<path>.*?)"')
    ALREADY_DOWNLOADED = re.compile(r"has already been downloaded", re.I)
    DELETE_ORIGINAL = re.compile(r"Deleting original file", re.I)

    @classmethod
    def parse_line(cls, line: str, item: DownloadItem, send_event: Callable):
        """
        Parses a single line of output and sends corresponding events.

        Args:
            line (str): The line of output from the subprocess.
            item (DownloadItem): The download item being processed.
            send_event (Callable): The function to call to send an event.
        """
        if not line.strip():
            return

        # Chain of responsibility for parsing the line
        parsers = [
            cls._parse_yt_dlp_progress,
            cls._parse_aria2c_progress,
            cls._handle_merge_complete,
            cls._handle_destination,
            cls._handle_already_downloaded,
            cls._handle_final_filepath,
            cls._handle_suppressed_lines,
        ]

        for parser_func in parsers:
            if parser_func(line, item, send_event):
                return

        # Fallback for any other lines
        send_event("status", text=line.strip())

    @classmethod
    def _parse_yt_dlp_progress(cls, line: str, item: DownloadItem, send_event: Callable) -> bool:
        """Parses native yt-dlp progress lines."""
        m = cls.YT_DLP_PROGRESS.search(line)
        if not m:
            return False
        try:
            data = m.groupdict()
            percent = float(data.get('percent'))
            item.size = data.get('size') or item.size
            send_event("progress", percent=percent, size=item.size, speed=data.get('speed'), eta=data.get('eta'), item=asdict(item))
            return True
        except (ValueError, TypeError):
            logger.debug("Could not parse yt-dlp progress from: %s", line)
            return False

    @classmethod
    def _parse_aria2c_progress(cls, line: str, item: DownloadItem, send_event: Callable) -> bool:
        """Parses aria2c progress lines."""
        m = cls.ARIA2C_PROGRESS.search(line)
        if not m:
            return False
        try:
            data = m.groupdict()
            percent = float(data.get('percent'))
            item.size = data.get('total') or item.size
            speed = data.get('speed')
            if speed and not speed.endswith('/s'):
                speed = f"{speed}/s"
            send_event("progress", percent=percent, size=item.size, downloaded=data.get('downloaded'), speed=speed, eta=data.get('eta'), item=asdict(item))
            return True
        except (ValueError, TypeError):
            logger.debug("Could not parse aria2c progress from: %s", line)
            return False

    @classmethod
    def _handle_merge_complete(cls, line: str, item: DownloadItem, send_event: Callable) -> bool:
        """Handles the 'merging formats' line."""
        m = cls.MERGED.search(line)
        if not m:
            return False
        path = m.group("path").strip()
        item.filepath = path
        send_event("status", text=f"✅ Merge complete: {os.path.basename(path)}")
        return True

    @classmethod
    def _handle_destination(cls, line: str, item: DownloadItem, send_event: Callable) -> bool:
        """Handles the 'Destination' line to capture the initial filepath."""
        m = cls.DESTINATION.search(line)
        if not m:
            return False
        item.filepath = m.group("path").strip()
        return True  # Suppress this line from the GUI

    @classmethod
    def _handle_already_downloaded(cls, line: str, item: DownloadItem, send_event: Callable) -> bool:
        """Handles the 'already been downloaded' line."""
        if not cls.ALREADY_DOWNLOADED.search(line):
            return False
        path_match = re.search(r'\[download\]\s+(.*?)\s+has already been downloaded', line)
        if path_match:
            item.filepath = path_match.group(1).strip()
        send_event("status", text="Already downloaded; skipping.")
        return True

    @classmethod
    def _handle_final_filepath(cls, line: str, item: DownloadItem, send_event: Callable) -> bool:
        """Handles the final filepath printed by '--print after_move:filepath'."""
        path_candidate = line.strip()
        try:
            if path_candidate and os.path.isabs(path_candidate) and os.path.exists(path_candidate):
                item.filepath = path_candidate
                return True  # Suppress this line from the GUI
        except Exception:
            return False
        return False

    @classmethod
    def _handle_suppressed_lines(cls, line: str, item: DownloadItem, send_event: Callable) -> bool:
        """Handles lines that should be suppressed from the GUI for a cleaner log."""
        if cls.DELETE_ORIGINAL.search(line):
            return True
        # Hide noisy raw lines unless in debug mode
        debug_mode = logger.isEnabledFor(logging.DEBUG)
        if not debug_mode and (line.strip().startswith('[#') or line.strip().startswith('[download]')):
            return True
        return False


class DownloadProcess:
    """
    Manages the execution of a single yt-dlp subprocess.

    This class is responsible for starting, monitoring, and stopping the download
    process, as well as capturing its output.
    """
    def __init__(self, cmd: List[str], item: DownloadItem, send_event: Callable, stop_event: threading.Event):
        self.cmd = cmd
        self.item = item
        self.send_event = send_event
        self.stop_event = stop_event
        self.proc: Optional[subprocess.Popen] = None
        self.output_lines: List[str] = []

    def run(self) -> List[str]:
        """
        Executes the download command and captures its output.

        Returns:
            List[str]: A list of all output lines from the process.
        """
        try:
            kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "text": True,
                "bufsize": 1,
                "universal_newlines": True
            }
            if os.name == 'posix':
                kwargs["start_new_session"] = True
            
            self.proc = subprocess.Popen(self.cmd, **kwargs)
            
            for line in iter(self.proc.stdout.readline, ''):
                if self.stop_event.is_set():
                    break
                if line.strip():
                    self.output_lines.append(line.strip())
                    YtDlpParser.parse_line(line, self.item, self.send_event)
            
            if self.proc:
                self.proc.wait()
                
        except Exception as e:
            logger.error(f"Error running download process: {e}")
            self.send_event("error", error=str(e), item=asdict(self.item))
        
        return self.output_lines

    def stop(self):
        """Stops the download process cleanly, terminating it if necessary."""
        if not self.proc or self.proc.poll() is not None:
            return
        try:
            if os.name == 'posix':
                pgid = os.getpgid(self.proc.pid)
                os.killpg(pgid, signal.SIGTERM)
                self.proc.wait(timeout=2)
            else:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    logger.warning("Process did not terminate gracefully, killing.")
                    self.proc.kill()
                    self.proc.wait()
        except Exception as e:
            logger.error(f"Error stopping process: {e}")
            if self.proc.poll() is None:
                self.proc.kill()
                self.proc.wait()
                        
    def pause(self):
        """Pauses the subprocess (POSIX only)."""
        if self.proc and self.proc.poll() is None and os.name == 'posix':
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGSTOP)
            except Exception as e:
                logger.error("Failed to pause process: %s", e)

    def resume(self):
        """Resumes the subprocess (POSIX only)."""
        if self.proc and self.proc.poll() is None and os.name == 'posix':
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGCONT)
            except Exception as e:
                logger.error("Failed to resume process: %s", e)


class DownloaderCore:
    """
    The main download engine.

    Manages a queue of downloads, a pool of worker threads to process them,
    and the lifecycle of download subprocesses.
    """
    def __init__(self, event_queue: Queue, download_dir: str = os.getcwd(),
                 concurrent_workers: int = 1, video_ext: str = "mp4", audio_ext: str = "mp3"):
        self.event_queue = event_queue
        self.download_dir = os.path.abspath(download_dir)
        self.video_ext = video_ext
        self.audio_ext = audio_ext
        self.concurrent_workers = max(1, concurrent_workers)

        self.download_queue: Queue[DownloadItem] = Queue()
        self._workers: List[threading.Thread] = []
        self._stop_event = threading.Event()
        self._active_processes: Dict[int, DownloadProcess] = {}
        self._proc_lock = threading.Lock()

    def enqueue(self, item: DownloadItem, start_workers: bool = True):
        """
        Adds a new download item to the queue.

        Args:
            item (DownloadItem): The item to add.
            start_workers (bool): If True, ensures worker threads are running.
        """
        self.download_queue.put(item)
        if start_workers:
            self._ensure_workers()

    def get_queued_urls(self) -> set:
        """Returns a set of URLs currently in the download queue."""
        return {i.url for i in list(self.download_queue.queue)}

    def stop_all(self):
        """Stops all workers and terminates active subprocesses."""
        self._stop_event.set()
        
        with self._proc_lock:
            for process in self._active_processes.values():
                process.stop()
            self._active_processes.clear()
        
        for worker in self._workers:
            if worker.is_alive():
                worker.join(timeout=1.0)
        
        while not self.download_queue.empty():
            try:
                self.download_queue.get_nowait()
                self.download_queue.task_done()
            except Empty:
                break
        
        logger.info("All downloads stopped and processes cleaned up")

    def pause_all(self):
        """Pauses all active download subprocesses (POSIX only)."""
        with self._proc_lock:
            for process in self._active_processes.values():
                process.pause()

    def resume_all(self):
        """Resumes all active download subprocesses (POSIX only)."""
        with self._proc_lock:
            for process in self._active_processes.values():
                process.resume()

    def _ensure_workers(self):
        """Ensures the number of active worker threads matches the configured limit."""
        self._workers = [t for t in self._workers if t.is_alive()]
        while len(self._workers) < self.concurrent_workers and not self._stop_event.is_set():
            t = threading.Thread(target=self._worker_loop, daemon=True)
            self._workers.append(t)
            t.start()

    def _worker_loop(self):
        """The main loop for a worker thread, processing items from the queue."""
        logger.debug("Worker %s started", threading.get_ident())
        while not self._stop_event.is_set():
            try:
                item = self.download_queue.get(timeout=0.5)
                if self._stop_event.is_set():
                    break
                self._process_item(item)
                self.download_queue.task_done()
            except Empty:
                continue
        logger.debug("Worker %s finished", threading.get_ident())

    def _process_item(self, item: DownloadItem):
        """Handles the processing of a single download item."""
        item.status = "Downloading"
        self._send_event("status", text=f"Starting: {item.title or item.url}")
        notify("Download Started", item.title or item.url)
        
        if not item.command:
            item.command = self._build_command(item)
        
        if not item.command or not os.path.exists(item.command[0]):
            error_msg = f"yt-dlp not found at: {item.command[0] if item.command else 'N/A'}"
            logger.error(error_msg)
            self._send_event("error", error=error_msg, item=asdict(item))
            return

        process = DownloadProcess(item.command, item, self._send_event, self._stop_event)
        with self._proc_lock:
            self._active_processes[threading.get_ident()] = process

        output_lines = process.run()

        with self._proc_lock:
            self._active_processes.pop(threading.get_ident(), None)

        self._handle_exit(process, output_lines, item)

    def _build_command(self, item: DownloadItem) -> List[str]:
        """
        Constructs the yt-dlp command for a given download item.

        Args:
            item (DownloadItem): The item to build the command for.

        Returns:
            List[str]: The fully constructed command as a list of strings.
        """
        out_template = os.path.join(self.download_dir, os.environ.get('FILENAME_TEMPLATE', "%(title)s [%(id)s].%(ext)s"))
        cmd = [YT_DLP_PATH, "--progress", "--newline", "--no-mtime",
               "--retries", "5", "--fragment-retries", "5", "--retry-sleep", "8",
               item.url]

        if item.format_id:
            cmd.extend(["-f", item.format_id])
        elif item.audio_only:
            cmd.extend(["-f", "bestaudio/best", "-x", "--audio-format", self.audio_ext])
            if item.embed_thumbnail:
                cmd.append("--embed-thumbnail")
        else:
            q = item.quality.replace("p", "")
            q = q if q.isdigit() else "720"
            cmd.extend([
                "-f", f"bestvideo[height<={q}]+bestaudio/best[height<={q}]/best",
                "--merge-output-format", self.video_ext
            ])

        if not item.from_playlist:
            cmd.append("--no-playlist")
        else:
            # Ensure we only download the single video url while keeping playlist context
            cmd.extend(["--yes-playlist", "--playlist-items", "1"])

        cmd.extend([
            "--external-downloader", ARIA2C_PATH,
            "--external-downloader-args", "aria2c:-x 16 -s 16 -k 1M --max-tries=5 --retry-wait=2",
            "--print", "after_move:filepath",
            "-o", out_template,
        ])
        return cmd

    def _handle_exit(self, process: DownloadProcess, output_lines: List[str], item: DownloadItem):
        """
        Handles the completion of a download process, determining success or failure.

        Args:
            process (DownloadProcess): The process that has finished.
            output_lines (List[str]): The captured output from the process.
            item (DownloadItem): The associated download item.
        """
        if self._stop_event.is_set():
            item.status = "Cancelled"
            self._send_event("cancelled", item=asdict(item))
            return

        success = item.filepath and os.path.exists(item.filepath)
        
        if success:
            item.status = "Completed"
            self._send_event("done", success=True, item=asdict(item))
            notify("Download Complete", os.path.basename(item.filepath))
        else:
            err_msg = self._extract_error(output_lines) or "Download failed"
            item.status = "Error"
            self._send_event("done", success=False, error_message=err_msg, item=asdict(item))
            notify("Download Failed", f"{item.title}: {err_msg}")

        history_entry = {
            "url": item.url,
            "title": os.path.basename(item.filepath).rsplit('.', 1)[0] if success else item.title,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": item.status,
            "size": item.size or "",
            "filepath": item.filepath or "",
        }
        database.add_history_item(history_entry)
        self._send_event("video_done", history_entry=history_entry)

    def _send_event(self, event_type: str, **kwargs):
        """Puts a new event onto the application's main event queue."""
        self.event_queue.put({"type": event_type, **kwargs})

    @staticmethod
    def _extract_error(output_lines: List[str]) -> Optional[str]:
        """
        Extracts the primary error message from yt-dlp's output.

        Args:
            output_lines (List[str]): The captured output.

        Returns:
            Optional[str]: The extracted error message, or None if not found.
        """
        for line in reversed(output_lines):
            if line.lower().startswith("error:"):
                return line.split(":", 1)[1].strip()
        return None