import os
import sys
import json
import logging
import subprocess
import threading
import tkinter as tk
import requests
from queue import Queue, Empty
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from settings import AppSettings

from dataclasses import asdict

from utils import check_dependencies, is_valid_url, notify, log_error, normalize_size_str, normalize_rate_str
from downloader_core import DownloaderCore, DownloadItem
import database

from .frames.url_frame import URLFrame
from .frames.options_frame import OptionsFrame
from .frames.progress_frame import ProgressFrame
from .frames.history_frame import HistoryFrame
from .playlist_selection_window import PlaylistSelectionWindow
from .settings_window import SettingsWindow

logger = logging.getLogger(__name__)

class DownloaderApp(ttk.Frame):
    def __init__(self, master, style):
        super().__init__(master, padding=15)
        self.pack(fill=BOTH, expand=YES)
        self.root = master
        self.style = style

        self._initialize_variables()
        # Apply saved theme early so UI starts in correct mode
        try:
            self.style.theme_use(self.theme_var.get())
        except Exception:
            pass
        self._setup_directories_and_db()
        self._load_data()
        self._create_downloader_core()
        self._create_widgets()
        self.after(100, self.process_event_queue)

    def _initialize_variables(self):
        self.settings = AppSettings()
        self.download_dir = ttk.StringVar(value=self.settings.download_dir)
        self.url_var = ttk.StringVar()
        self.quality_var = ttk.StringVar(value='720p')
        self.audio_only_var = ttk.BooleanVar(value=False)
        self.embed_thumbnail_var = ttk.BooleanVar(value=False)
        self.theme_var = ttk.StringVar(value=self.settings.theme)
        self.video_format_var = ttk.StringVar(value=self.settings.video_format)
        self.audio_format_var = ttk.StringVar(value=self.settings.audio_format)
        self.concurrent_downloads_var = ttk.IntVar(value=self.settings.concurrent_downloads)
        self.extension_id_var = ttk.StringVar(value=self.settings.extension_id)
        self.verbose_logs_var = ttk.BooleanVar(value=False)
        self.playlist_total = 0
        self.playlist_done = 0
        
        self.event_queue = Queue()
        self.download_queue_items = [] # This will be our source of truth for the queue UI
        self.history = []
        self.is_shutting_down = False

    def _setup_directories_and_db(self):
        # Initialize database first
        database.init_db()
        # Then create download directory
        download_path = self.download_dir.get()
        if download_path and not os.path.exists(download_path):
            try:
                os.makedirs(download_path, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create download directory {download_path}: {e}")
                # Fallback to current directory
                self.download_dir.set(os.getcwd())

    def _load_data(self):
        try:
            self.history = database.get_history()
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            self.history = []
        
        try:
            self.download_queue_items = database.get_queue()
        except Exception as e:
            logger.error(f"Failed to load queue: {e}")
            self.download_queue_items = []

    def _create_downloader_core(self):
        self.core = DownloaderCore(
            event_queue=self.event_queue,
            download_dir=self.download_dir.get(),
            concurrent_workers=self.concurrent_downloads_var.get(),
            video_ext=self.video_format_var.get(),
            audio_ext=self.audio_format_var.get(),
        )

    def _create_widgets(self):
        option_lf = ttk.Labelframe(self, text="Enter a video URL to begin", padding=15)
        option_lf.pack(fill=X, expand=NO, anchor=N, pady=5)

        self.url_frame = URLFrame(option_lf, self)
        self.options_frame = OptionsFrame(option_lf, self)
        
        self.progress_frame = ProgressFrame(self)
        self.progress_frame.pack(fill=X, pady=5)
        self.progress_frame.bind_verbose_var(self.verbose_logs_var)

        self.history_frame = HistoryFrame(self, self)
        self.history_frame.pack(fill=BOTH, expand=YES, pady=5)

        self.update_history_view()
        self.update_option_states()

    def process_event_queue(self):
        try:
            while not self.event_queue.empty():
                msg = self.event_queue.get_nowait()
                msg_type = msg.get('type')
                handler = getattr(self, f"_handle_{msg_type}_event", None)
                if handler:
                    handler(msg)
                else:
                    logger.warning("No handler for event type: %s", msg_type)
        except Empty:
            pass
        finally:
            if not self.is_shutting_down:
                self.after(100, self.process_event_queue)

    # --- Event Handlers ---
    def _handle_progress_event(self, msg):
        percent = msg.get('percent', 0)
        self.progress_frame.progress['value'] = percent
        size = msg.get('size', 'N/A')
        downloaded = msg.get('downloaded')
        speed = msg.get('speed', 'N/A')
        eta = msg.get('eta', 'N/A')
        # Compose a clean IDM-style progress line
        size_norm = normalize_size_str(size) if size and size != 'N/A' else 'N/A'
        speed_norm = normalize_rate_str(speed) if speed and speed != 'N/A' else 'N/A'
        progress_text = f"⏳ {percent:.0f}% of {size_norm} at {speed_norm}, ETA: {eta}"
        self.progress_frame.update_progress_display(percent, progress_text)

    def _handle_status_event(self, msg):
        text = msg.get('text', '')
        if text:
            self.progress_frame.add_output_line(text)

    def _handle_video_done_event(self, msg):
        history_entry = msg.get('history_entry')
        if history_entry:
            self.history.insert(0, history_entry)
            self.download_queue_items = [item for item in self.download_queue_items if item['url'] != history_entry['url']]
            self.update_history_view()
            # Show a concise success banner and set progress to 100%
            if history_entry.get('status') in ("Completed", "Done"):
                self.progress_frame.progress['value'] = 100
                self.progress_frame.show_success(f"Completed: {history_entry.get('title', '')}")
            # Playlist aggregate
            if self.playlist_total:
                self.playlist_done = min(self.playlist_done + 1, self.playlist_total)
                self.progress_frame.set_playlist_summary(f"Completed {self.playlist_done}/{self.playlist_total}")
        if self.core.download_queue.empty():
            self._set_ui_state(NORMAL)
            self.root.after(1500, self.progress_frame.set_idle_state)

    def _handle_cancelled_event(self, msg):
        self._set_ui_state(NORMAL)
        self.progress_frame.add_output_line("Download cancelled by user.")
        self.root.after(1500, self.progress_frame.set_idle_state)

    def _handle_done_event(self, msg):
        if self.core.download_queue.empty():
            self._set_ui_state(NORMAL)
            # If this wasn't a success, the error is already shown. Reset to idle.
            if not msg.get('success'):
                self.root.after(1500, self.progress_frame.set_idle_state)

        if not msg.get('success'):
            error_message = msg.get('error_message', "An unknown error occurred.")
            item_to_retry = msg.get('item')
            notify("Download Failed", error_message)
            if item_to_retry and messagebox.askyesno("Download Failed", f"{error_message}\n\nWould you like to retry?"):
                self.core.enqueue(DownloadItem(**item_to_retry))
            else:
                for item in self.download_queue_items:
                    if item['url'] == item_to_retry['url']:
                        item['status'] = "Error"
                self.update_history_view()

    def _handle_error_event(self, msg):
        error = msg.get('error', 'Unknown error')
        item = msg.get('item', {})
        log_error(Exception(error), f"Error processing {item.get('url')}")
        messagebox.showerror("Processing Error", f"Failed to process {item.get('title', 'item')}. See logs for details.")

    # --- UI Actions ---
    def add_to_queue(self, url=None, download_now=False):
        url_to_add = url or self.url_var.get().strip()
        if not is_valid_url(url_to_add):
            messagebox.showwarning("Invalid URL", "Please enter a valid video URL")
            return

        if "list=" in url_to_add:
            self._fetch_playlist_info(url_to_add, download_now)
        else:
            self._add_single_item_to_queue(url_to_add, download_now)

    def _add_single_item_to_queue(self, url, download_now=False, from_playlist=False):
        if url in [item['url'] for item in self.download_queue_items]:
            logger.warning("Skipping duplicate URL: %s", url)
            return
            
        item = DownloadItem(
            url=url,
            quality=self.quality_var.get(),
            audio_only=self.audio_only_var.get(),
            embed_thumbnail=self.embed_thumbnail_var.get(),
            status="Downloading" if download_now else "Queued",
            from_playlist=from_playlist
        )
        self.download_queue_items.append(asdict(item))
        self.update_history_view()
        self.url_var.set("")
        if download_now:
            self.start_download(item)

    def download_now(self):
        self.add_to_queue(download_now=True)

    def start_queue(self):
        if not self.download_queue_items:
            messagebox.showinfo("Queue Empty", "There are no videos in the queue.")
            return
        
        for item_dict in self.download_queue_items:
            if item_dict.get('status') == "Queued":
                item_dict['status'] = "Downloading"
                self.start_download(DownloadItem(**item_dict))
        self.update_history_view()

    def start_download(self, item: DownloadItem):
        if not check_dependencies(): return
        self.progress_frame.clear_output()
        header = item.title if item.title and item.title != 'Fetching title...' else item.url
        self.progress_frame.add_output_line(f"▶ Downloading: {header}")
        self.core.enqueue(item)
        self._set_ui_state(DISABLED)

    def cancel_download(self):
        self.core.stop_all()

    def pause_all(self):
        self.core.pause_all()

    def resume_all(self):
        self.core.resume_all()

    def _set_ui_state(self, state):
        self.url_frame.set_state(state)
        self.options_frame.set_state(state)

    def update_option_states(self):
        self.options_frame.set_state(NORMAL)

    def update_history_view(self):
        self.history_frame.update_view(self.download_queue_items, self.history)

    def select_folder(self):
        path = filedialog.askdirectory(title="Select Download Folder")
        if path and os.access(path, os.W_OK):
            self.download_dir.set(path)
            self.core.download_dir = path
            self.save_config()
        elif path:
            messagebox.showerror("Error", f"Selected folder is not writable: {path}")

    def open_settings(self):
        SettingsWindow(self.root, self)

    def update_yt_dlp(self):
        if messagebox.askyesno("Confirm", "This will download the latest version of yt-dlp. Continue?"):
            threading.Thread(target=self._update_yt_dlp_thread, daemon=True).start()

    def _update_yt_dlp_thread(self):
        self.event_queue.put({'type': 'status', 'text': 'Updating yt-dlp...'
        })
        try:
            asset_name = "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp"
            response = requests.get("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest", timeout=15)
            response.raise_for_status()
            asset = next((a for a in response.json()['assets'] if a['name'] == asset_name), None)
            if not asset: raise Exception(f"Could not find asset: {asset_name}")

            dl_response = requests.get(asset['browser_download_url'], stream=True, timeout=60)
            dl_response.raise_for_status()
            with open(os.path.join("assets", asset_name), 'wb') as f:
                for chunk in dl_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            self.event_queue.put({'type': 'status', 'text': 'yt-dlp updated successfully!'})
        except Exception as e:
            log_error(e, "yt-dlp update")
            self.event_queue.put({'type': 'status', 'text': 'Error updating yt-dlp. See logs.'})

    def change_theme(self, event=None):
        self.style.theme_use(self.theme_var.get())
        self.save_config()

    def save_config(self):
        config_data = {
            "download_dir": self.download_dir.get(),
            "theme": self.theme_var.get(),
            "video_format": self.video_format_var.get(),
            "audio_format": self.audio_format_var.get(),
            "concurrent_downloads": self.concurrent_downloads_var.get(),
            "extension_id": self.extension_id_var.get(),
        }
        try:
            with open(".env", "w") as f:
                for key, value in config_data.items():
                    f.write(f'{key.upper()}="{value}"\n')
        except IOError as e:
            log_error(e, "Failed to save config")

    def load_config(self):
        self.settings = AppSettings()
        self.download_dir.set(self.settings.download_dir)
        self.theme_var.set(self.settings.theme)
        self.video_format_var.set(self.settings.video_format)
        self.audio_format_var.set(self.settings.audio_format)
        self.concurrent_downloads_var.set(self.settings.concurrent_downloads)
        self.extension_id_var.set(self.settings.extension_id)
        self.change_theme()

    def quit(self):
        self.is_shutting_down = True
        self.core.stop_all()
        database.save_queue([item for item in self.download_queue_items if item['status'] != 'Completed'])
        self.root.destroy()

    # --- History/Queue Actions ---
    def copy_history_url(self):
        selected_item = self.history_frame.get_selected_item()
        if selected_item:
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_item['url'])

    def redownload_history_item(self):
        selected_item = self.history_frame.get_selected_item()
        if selected_item:
            self.url_var.set(selected_item['url'])
            self.download_now()

    def remove_history_item(self):
        selected_item = self.history_frame.get_selected_item()
        if selected_item:
            url_to_remove = selected_item['url']
            self.download_queue_items = [item for item in self.download_queue_items if item['url'] != url_to_remove]
            self.history = [item for item in self.history if item['url'] != url_to_remove]
            # Here you might want to also remove from the DB if it's a persistent history item
            self.update_history_view()

    # --- History file actions ---
    def _get_selected_history_full(self):
        sel = self.history_frame.get_selected_item()
        if not sel:
            return None
        # Find full entry including filepath
        for h in self.history:
            if h.get('url') == sel.get('url'):
                return h
        # Fallback to selection values
        return sel

    def open_history_file(self):
        item = self._get_selected_history_full()
        path = item.get('filepath') if item else None
        if path and os.path.isfile(path):
            try:
                if sys.platform == 'win32':
                    os.startfile(path)  # type: ignore[attr-defined]
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', path])
                else:
                    subprocess.Popen(['xdg-open', path])
            except Exception:
                pass

    def reveal_history_file(self):
        item = self._get_selected_history_full()
        path = item.get('filepath') if item else None
        if path and os.path.exists(path):
            folder = os.path.dirname(path)
            try:
                if sys.platform == 'win32':
                    subprocess.Popen(['explorer', '/select,', path])
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', folder])
                else:
                    subprocess.Popen(['xdg-open', folder])
            except Exception:
                pass

    def copy_history_filename(self):
        item = self._get_selected_history_full()
        path = item.get('filepath') if item else None
        if path:
            self.root.clipboard_clear()
            self.root.clipboard_append(os.path.basename(path))

    def copy_history_filepath(self):
        item = self._get_selected_history_full()
        path = item.get('filepath') if item else None
        if path:
            self.root.clipboard_clear()
            self.root.clipboard_append(path)

    def clear_history(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all completed downloads from history?"):
            database.clear_history()
            self.history = []
            self.update_history_view()

    def paste_url(self):
        try:
            self.url_var.set(self.root.clipboard_get())
        except tk.TclError:
            pass

    def _fetch_playlist_info(self, url, download_now):
        self._set_ui_state(DISABLED)
        self.url_frame.download_now_button.config(text="Fetching...")

        def fetch_thread():
            try:
                cmd = [check_dependencies.__globals__['YT_DLP_PATH'], '--flat-playlist', '-J', url]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True, encoding='utf-8')
                data = json.loads(proc.stdout)
                entries = data.get('entries', [])
                videos = [{'title': e.get('title', f"Video {e.get('id', '')}"), 'id': e.get('id', ''), 'url': e.get('url', f"https://www.youtube.com/watch?v={e['id']}")} for e in entries]
                self.root.after(0, lambda: self._show_playlist_selection(videos, url, download_now))
            except (subprocess.CalledProcessError, json.JSONDecodeError, Exception) as exc:
                log_error(exc, "Failed to fetch playlist info")
                self.event_queue.put({'type': 'status', 'text': f"ERROR: Could not fetch playlist info. Details: {exc}"})
            finally:
                self.root.after(0, lambda: self._set_ui_state(NORMAL))
                self.root.after(0, lambda: self.url_frame.download_now_button.config(text="Download Now"))

        threading.Thread(target=fetch_thread, daemon=True).start()

    def _show_playlist_selection(self, videos, url, download_now):
        PlaylistSelectionWindow(self.root, self, videos, url, download_now)
        self.playlist_total = len(videos)
        self.playlist_done = 0
        if download_now:
            self.progress_frame.set_playlist_summary(f"Completed 0/{self.playlist_total}")

    def process_playlist_selection(self, selected_urls, download_now):
        for url in selected_urls:
            self._add_single_item_to_queue(url, download_now, from_playlist=True)
        if download_now:
            self.start_queue()
