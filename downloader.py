import os
import json
import re
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, END, NORMAL, DISABLED
from tkinterdnd2 import DND_FILES, TkinterDnD
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from datetime import datetime
from queue import Queue, Empty
import sys
import signal
import requests

HISTORY_FILE = "history.json"
CONFIG_FILE = "settings.json"


class PlaylistSelectionWindow(ttk.Toplevel):
    def __init__(self, master, app_instance, videos, original_url, download_now):
        super().__init__(master)
        self.title("Select Playlist Videos")
        self.geometry("800x600")
        self.app = app_instance
        self.videos = videos
        self.original_url = original_url
        self.download_now = download_now
        self.selected_videos = {}

        self.create_widgets()
        self.populate_videos()

    def create_widgets(self):
        # Select All/None buttons
        button_frame = ttk.Frame(self, padding=10)
        button_frame.pack(fill=tk.X)
        ttk.Button(button_frame, text="Select All", command=self.select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Select None", command=self.select_none).pack(side=tk.LEFT, padx=5)

        # Treeview for videos
        self.tree = ttk.Treeview(self, columns=('select', 'title', 'id'), show='headings')
        self.tree.heading('select', text='Select', anchor=tk.CENTER)
        self.tree.heading('title', text='Title')
        self.tree.heading('id', text='ID')

        self.tree.column('select', width=50, anchor=tk.CENTER)
        self.tree.column('title', width=500)
        self.tree.column('id', width=150)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.tree.bind("<Button-1>", self.on_tree_click)

        # Download/Cancel buttons
        action_frame = ttk.Frame(self, padding=10)
        action_frame.pack(fill=tk.X)
        ttk.Button(action_frame, text="Download Selected", command=self.download_selected).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def populate_videos(self):
        for video in self.videos:
            item_id = self.tree.insert('', tk.END, values=('☐', video['title'], video['id']))
            self.selected_videos[item_id] = {'selected': False, 'data': video}

    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "heading":
            return

        item_id = self.tree.identify_row(event.y)
        if not item_id: return

        column = self.tree.identify_column(event.x)
        if column == '#1':  # The 'select' column
            current_state = self.selected_videos[item_id]['selected']
            new_state = not current_state
            self.selected_videos[item_id]['selected'] = new_state
            self.tree.set(item_id, 'select', '☑' if new_state else '☐')

    def select_all(self):
        for item_id in self.tree.get_children():
            self.selected_videos[item_id]['selected'] = True
            self.tree.set(item_id, 'select', '☑')

    def select_none(self):
        for item_id in self.tree.get_children():
            self.selected_videos[item_id]['selected'] = False
            self.tree.set(item_id, 'select', '☐')

    def download_selected(self):
        selected_urls = []
        for item_id, data in self.selected_videos.items():
            if data['selected']:
                selected_urls.append(data['data']['url'])

        if not selected_urls:
            messagebox.showwarning("No Videos Selected", "Please select at least one video to download.")
            return

        self.destroy()
        self.app.process_playlist_selection(selected_urls, self.download_now)


class SettingsWindow(ttk.Toplevel):
    def __init__(self, master, app_instance):
        super().__init__(master)
        self.title("Settings")
        self.geometry("400x300")
        self.app = app_instance

        self.create_widgets()

    def create_widgets(self):
        # Theme Selector
        theme_frame = ttk.Frame(self, padding=10)
        theme_frame.pack(fill=tk.X, pady=5)
        ttk.Label(theme_frame, text="Theme:").pack(side=tk.LEFT, padx=(0, 5))
        self.theme_selector = ttk.Combobox(theme_frame, textvariable=self.app.theme_var, values=self.app.style.theme_names(),
                                           state="readonly", width=15)
        self.theme_selector.pack(side=tk.LEFT, padx=5)
        self.theme_selector.bind("<<ComboboxSelected>>", self.app.change_theme)

        # Save Location
        save_location_frame = ttk.Frame(self, padding=10)
        save_location_frame.pack(fill=tk.X, pady=5)
        ttk.Label(save_location_frame, text="Download Folder:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(save_location_frame, textvariable=self.app.download_dir, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(save_location_frame, text="Browse", command=self.app.select_folder).pack(side=tk.LEFT, padx=5)

        # Update yt-dlp
        update_frame = ttk.Frame(self, padding=10)
        update_frame.pack(fill=tk.X, pady=5)
        ttk.Button(update_frame, text="Update yt-dlp", command=self.app.update_yt_dlp).pack(side=tk.LEFT, padx=5)

        # Clear History
        clear_history_frame = ttk.Frame(self, padding=10)
        clear_history_frame.pack(fill=tk.X, pady=5)
        ttk.Button(clear_history_frame, text="Clear History", command=self.app.clear_history).pack(side=tk.LEFT, padx=5)


class DownloaderApp(ttk.Frame):
    def __init__(self, master, style):
        super().__init__(master, padding=15)
        self.pack(fill=BOTH, expand=YES)
        self.root = master
        self.style = style

        # App variables
        self.download_dir = ttk.StringVar(value=os.getcwd())
        self.url_var = ttk.StringVar()
        self.quality_var = ttk.StringVar(value='720p')
        self.audio_only_var = ttk.BooleanVar(value=False)
        self.embed_thumbnail_var = ttk.BooleanVar(value=False)
        self.theme_var = ttk.StringVar()
        self.history = []
        self.threads = []
        self.queue = Queue()
        self.current_process = None
        self.is_cancelled = False
        self.download_queue = []

        self.load_config()
        self.load_history()

        # UI Elements
        self.create_widgets()
        self.update_option_states()  # Set initial state

    def create_widgets(self):
        option_text = "Enter a video URL to begin"
        option_lf = ttk.Labelframe(self, text=option_text, padding=15)
        option_lf.pack(fill=X, expand=NO, anchor=N)

        self.create_url_row(option_lf)
        self.create_options_row(option_lf)

        progress_frame = ttk.Frame(self)
        progress_frame.pack(fill=X, pady=10)

        self.progress = ttk.Progressbar(progress_frame, mode='determinate', bootstyle=(STRIPED, SUCCESS))
        self.progress.pack(side=LEFT, fill=X, expand=YES)

        self.percentage_var = ttk.StringVar()
        self.percentage_label = ttk.Label(progress_frame, textvariable=self.percentage_var)
        self.percentage_label.pack(side=LEFT, padx=10)

        status_frame = ttk.Frame(self)
        status_frame.pack(fill=X, expand=NO)
        self.status_var = ttk.StringVar(value="Status: Idle")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=LEFT, fill=X, anchor=W)

        self.open_folder_button = ttk.Button(status_frame, text="Open Folder", command=self.open_download_folder,
                                             width=12)

        self.size_var = ttk.StringVar()
        ttk.Label(status_frame, textvariable=self.size_var).pack(side=RIGHT, padx=5)
        self.speed_var = ttk.StringVar()
        ttk.Label(status_frame, textvariable=self.speed_var).pack(side=RIGHT, padx=5)

        self.create_history_view()
        self.update_history_view()
        self.create_footer()

    def create_url_row(self, parent):
        url_row = ttk.Frame(parent)
        url_row.pack(fill=X, expand=YES, pady=5)
        ttk.Label(url_row, text="URL", width=8).pack(side=LEFT, padx=(0, 5))

        self.url_entry = ttk.Entry(url_row, textvariable=self.url_var)
        self.url_entry.pack(side=LEFT, fill=X, expand=YES, padx=5)
        self.url_entry.drop_target_register(DND_FILES)
        self.url_entry.dnd_bind("<<Drop>>", self.on_drop)

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Paste", command=self.paste_url)
        self.url_entry.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

        self.add_to_queue_button = ttk.Button(url_row, text="Add to Queue", command=self.add_to_queue, width=12, bootstyle=OUTLINE)
        self.add_to_queue_button.pack(side=LEFT, padx=5)

        self.download_now_button = ttk.Button(url_row, text="Download Now", command=self.download_now, width=12, bootstyle=PRIMARY)
        self.download_now_button.pack(side=LEFT, padx=5)

        self.start_queue_button = ttk.Button(url_row, text="Start Queue", command=self.start_queue, width=12, bootstyle=SUCCESS)
        self.start_queue_button.pack(side=LEFT, padx=5)

        self.cancel_button = ttk.Button(url_row, text="Cancel", command=self.cancel_download, width=10,
                                        bootstyle=DANGER)

    def create_options_row(self, parent):
        options_row = ttk.Frame(parent)
        options_row.pack(fill=X, expand=YES, pady=5)

        self.quality_combobox = ttk.Combobox(options_row, textvariable=self.quality_var, 
                                                 values=['1080p', '720p', '480p', '360p'], 
                                                 state="readonly", width=8)
        self.quality_combobox.pack(side=LEFT, padx=5)
        ttk.Label(options_row, text="Quality:").pack(side=LEFT, padx=(0, 5))

        self.audio_only_checkbox = ttk.Checkbutton(options_row, text="Audio Only (MP3)", variable=self.audio_only_var,
                                                   bootstyle="round-toggle", command=self.update_option_states)
        self.audio_only_checkbox.pack(side=LEFT, padx=15)

        self.embed_thumbnail_checkbox = ttk.Checkbutton(options_row, text="Embed Thumbnail",
                                                        variable=self.embed_thumbnail_var, bootstyle="round-toggle")
        self.embed_thumbnail_checkbox.pack(side=LEFT, padx=5)

        self.select_folder_button = ttk.Button(options_row, text="Save Location", command=self.select_folder, width=15,
                                               bootstyle=OUTLINE)
        self.select_folder_button.pack(side=LEFT, padx=5)

        self.settings_button = ttk.Button(options_row, text="Settings", command=self.open_settings, width=10,
                                          bootstyle=INFO)
        self.settings_button.pack(side=RIGHT, padx=5)

        self.close_button = ttk.Button(options_row, text="Close", command=self.root.quit, width=10,
                                       bootstyle="danger-outline")
        self.close_button.pack(side=RIGHT, padx=5)

    def create_history_view(self):
        self.history_view = ttk.Treeview(
            master=self, bootstyle=INFO, columns=['status', 'title', 'date', 'url'], show=HEADINGS
        )
        self.history_view.pack(fill=BOTH, expand=YES, pady=10)

        self.history_view.heading('status', text='Status', anchor=W)
        self.history_view.heading('title', text='Title', anchor=W)
        self.history_view.heading('date', text='Date', anchor=W)
        self.history_view.heading('url', text='URL', anchor=W)

        self.history_view.column('status', anchor=W, width=100)
        self.history_view.column('title', anchor=W, width=250)
        self.history_view.column('date', anchor=W, width=150)
        self.history_view.column('url', anchor=W, width=200)

        self.history_menu = tk.Menu(self.root, tearoff=0)
        self.history_menu.add_command(label="Copy URL", command=self.copy_history_url)
        self.history_menu.add_command(label="Re-download", command=self.redownload_history_item)
        self.history_view.bind("<Button-3>", self.show_history_menu)

    def create_footer(self):
        footer_frame = ttk.Frame(self)
        footer_frame.pack(fill=X, side=BOTTOM, padx=0, pady=(10, 0))

    def _set_ui_state(self, state):
        is_downloading = state == DISABLED

        self.url_entry.config(state=state)

        if is_downloading:
            self.add_to_queue_button.pack_forget()
            self.download_now_button.pack_forget()
            self.start_queue_button.pack_forget()
            self.cancel_button.pack(side=LEFT, padx=5)
        else:
            self.cancel_button.pack_forget()
            self.add_to_queue_button.pack(side=LEFT, padx=5)
            self.download_now_button.pack(side=LEFT, padx=5)
            self.start_queue_button.pack(side=LEFT, padx=5)

        self.update_option_states()

    def on_drop(self, event):
        self.url_var.set(event.data.strip("{}"))

    def paste_url(self):
        try:
            self.url_var.set(self.root.clipboard_get())
        except tk.TclError:
            pass

    def select_folder(self):
        path = filedialog.askdirectory(title="Select Download Folder")
        if path:
            self.download_dir.set(path)
            self.save_config()

    def update_option_states(self):
        is_downloading = self.add_to_queue_button.cget('state') == DISABLED
        audio_only = self.audio_only_var.get()

        self.quality_combobox.config(state=DISABLED if audio_only or is_downloading else 'readonly')
        self.embed_thumbnail_checkbox.config(state=NORMAL if audio_only and not is_downloading else DISABLED)

        if not audio_only:
            self.embed_thumbnail_var.set(False)

    def download_now(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a YouTube URL")
            return

        is_playlist = 'list=' in url
        if is_playlist:
            self._fetch_playlist_info(url, download_now=True)
            return

        item = {
            "url": url,
            "quality": self.quality_var.get(),
            "audio_only": self.audio_only_var.get(),
            "embed_thumbnail": self.embed_thumbnail_var.get(),
            "title": "Fetching title..."
        }

        self.is_cancelled = False
        self.open_folder_button.pack_forget()
        self._set_ui_state(DISABLED)
        self.status_var.set("Status: Starting download...")
        self.progress.config(value=0)
        self.percentage_var.set("0.0%")
        self.speed_var.set("")
        self.size_var.set("")

        thread = threading.Thread(target=self.run_download, args=(self.build_command(url, 'list=' in url, False, item), url), daemon=True)
        thread.start()
        self.after(100, self.process_queue)

    def add_to_queue(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a YouTube URL")
            return

        is_playlist = 'list=' in url
        if is_playlist:
            self._fetch_playlist_info(url, download_now=False)
            return

        self.download_queue.append({
            "url": url,
            "quality": self.quality_var.get(),
            "audio_only": self.audio_only_var.get(),
            "embed_thumbnail": self.embed_thumbnail_var.get(),
            "title": "Fetching title..."
        })
        self.update_history_view()
        self.url_var.set("")

    def _fetch_playlist_info(self, url, download_now):
        self.status_var.set("Status: Fetching playlist info...")
        self._set_ui_state(DISABLED)
        thread = threading.Thread(target=self._run_fetch_playlist_info, args=(url, download_now), daemon=True)
        thread.start()

    def _run_fetch_playlist_info(self, url, download_now):
        yt_dlp_path = f"./assets/yt-dlp{'.exe' if sys.platform == 'win32' else ''}"
        cmd = [yt_dlp_path, "--flat-playlist", "--dump-json", url]

        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                raise Exception(f"yt-dlp error: {stderr}")

            videos = []
            for line in stdout.splitlines():
                try:
                    video_data = json.loads(line)
                    videos.append({
                        "id": video_data.get('id'),
                        "title": video_data.get('title'),
                        "url": video_data.get('webpage_url', url) # Fallback to playlist URL if individual URL not found
                    })
                except json.JSONDecodeError:
                    continue

            self.queue.put({'type': 'playlist_info', 'videos': videos, 'url': url, 'download_now': download_now})

        except Exception as e:
            self.queue.put({'type': 'status', 'text': f"Error fetching playlist: {e}"})
            messagebox.showerror("Error", f"Failed to fetch playlist information: {e}")
            self._set_ui_state(NORMAL)

    def build_command(self, url, is_playlist, download_playlist, item):
        yt_dlp_path = f"./assets/yt-dlp{'.exe' if sys.platform == 'win32' else ''}"
        aria2c_path = f"./assets/aria2c{'.exe' if sys.platform == 'win32' else ''}"
        base_cmd = [yt_dlp_path, url]

        if download_playlist:
            output_template = os.path.join(self.download_dir.get(),
                                           "%(playlist_title)s/%(playlist_index)s - %(title)s [%(id)s].%(ext)s")
        else:
            output_template = os.path.join(self.download_dir.get(), "%(title)s [%(id)s].%(ext)s")

        if item['audio_only']:
            format_cmd = ["-f", "bestaudio/best", "-x", "--audio-format", "mp3"]
            if item['embed_thumbnail']:
                format_cmd.append("--embed-thumbnail")
        else:
            quality = self.quality_var.get().replace('p', '')
            format_cmd = ["-f", f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"]

        playlist_cmd = []
        if is_playlist:
            playlist_cmd = ["--yes-playlist"] if download_playlist else ["--no-playlist"]

        remaining_cmd = [
            "--external-downloader", aria2c_path,
            "--external-downloader-args", "-x 16 -k 1M",
            "-o", output_template,
            "--no-mtime", "--progress"
        ]
        return base_cmd + format_cmd + playlist_cmd + remaining_cmd

    def cancel_download(self):
        if self.current_process:
            self.is_cancelled = True
            try:
                if sys.platform != "win32":
                    os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
                else:
                    self.current_process.terminate()
            except (ProcessLookupError, PermissionError) as e:
                print(f"Could not cancel download: {e}")

    def process_queue(self):
        try:
            msg = self.queue.get_nowait()
            msg_type = msg.get('type')

            if msg_type == 'progress':
                self.progress.config(value=msg.get('percent', 0))
                self.percentage_var.set(f"{msg.get('percent', 0):.1f}%")
                self.size_var.set(f"Size: {msg.get('size', '')}")
                self.speed_var.set(f"Speed: {msg.get('speed', '')}")
            elif msg_type == 'status':
                self.status_var.set(f"Status: {msg.get('text', '')}")
            elif msg_type == 'video_done':
                if msg.get('history_entry'):
                    self.history.append(msg['history_entry'])
                    self.save_history()
                    self.update_history_view()
                self.progress.config(value=0)
                self.percentage_var.set("")
                self.size_var.set("")
                self.speed_var.set("")
            elif msg_type == 'cancelled':
                self.status_var.set("Status: Download cancelled")
                self.progress.config(value=0)
                self.percentage_var.set("")
                self.size_var.set("")
                self.speed_var.set("")
                self._set_ui_state(NORMAL)
                self.current_process = None
                return
            elif msg_type == 'done':
                if msg.get('success'):
                    self.progress.config(value=100)
                    self.percentage_var.set("100.0%")
                    self.status_var.set("Status: Download complete!")
                    self.open_folder_button.pack(side=RIGHT, padx=10)
                else:
                    if not self.is_cancelled:
                        error_message = msg.get('error_message', "An unknown error occurred.")
                        self.status_var.set(f"Status: Error - {error_message}")
                        messagebox.showerror("Download Failed", error_message)
                self._set_ui_state(NORMAL)
                self.current_process = None
                return
            elif msg_type == 'playlist_info':
                videos = msg.get('videos', [])
                original_url = msg.get('url')
                download_now = msg.get('download_now')
                if videos:
                    PlaylistSelectionWindow(self.root, self, videos, original_url, download_now)
                else:
                    messagebox.showinfo("No Videos Found", "No videos were found in the playlist.")
                self._set_ui_state(NORMAL)
        except Empty:
            pass
        self.after(100, self.process_queue)

    def run_download(self, cmd, url):
        kwargs = {
            'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE,
            'text': True, 'bufsize': 1, 'universal_newlines': True, 'encoding': 'utf-8'
        }
        if sys.platform != "win32":
            kwargs['start_new_session'] = True

        self.current_process = process = subprocess.Popen(cmd, **kwargs)

        stderr_output = []

        # Use threads to read stdout and stderr concurrently
        def read_stdout(pipe, queue):
            for line in iter(pipe.readline, ''):
                if self.is_cancelled: break
                queue.put({'type': 'status', 'text': line.strip()})
            pipe.close()

        def read_stderr(pipe, buffer):
            for line in iter(pipe.readline, ''):
                buffer.append(line)
            pipe.close()

        stdout_thread = threading.Thread(target=read_stdout, args=(process.stdout, self.queue), daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, args=(process.stderr, stderr_output), daemon=True)

        stdout_thread.start()
        stderr_thread.start()

        stdout_thread.join() # Wait for stdout to finish
        stderr_thread.join() # Wait for stderr to finish

        process.wait()
        self.current_process = None

        if self.is_cancelled:
            self.queue.put({'type': 'cancelled'})
            return

        if process.returncode != 0:
            error_message = "An unknown error occurred during download."
            full_stderr = "".join(stderr_output)

            if "ERROR: " in full_stderr:
                match = re.search(r"ERROR: (.+)", full_stderr)
                if match:
                    error_message = match.group(1).strip()
            elif "aria2c" in full_stderr and "error" in full_stderr.lower():
                error_message = "aria2c encountered an error. Check console for details."

            self.queue.put({'type': 'done', 'success': False, 'error_message': error_message})
        else:
            self.queue.put({'type': 'done', 'success': True})

    def open_download_folder(self):
        path = self.download_dir.get()
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except FileNotFoundError:
            messagebox.showerror("Error", f"Could not open folder. Path not found: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def show_history_menu(self, event):
        iid = self.history_view.identify_row(event.y)
        if iid:
            self.history_view.selection_set(iid)
            self.history_menu.tk_popup(event.x_root, event.y_root)

    def copy_history_url(self):
        selected_items = self.history_view.selection()
        if not selected_items: return
        item_values = self.history_view.item(selected_items[0], 'values')
        if item_values and len(item_values) >= 3:
            url = item_values[2]
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.status_var.set("Status: URL copied to clipboard!")
            self.after(3000, lambda: self.status_var.set("Status: Idle"))

    def redownload_history_item(self):
        selected_items = self.history_view.selection()
        if not selected_items: return
        item_values = self.history_view.item(selected_items[0], 'values')
        if item_values and len(item_values) >= 3:
            url = item_values[2]
            self.url_var.set(url)
            self.download()

    def update_yt_dlp(self):
        if messagebox.askyesno("Confirm", "This will download the latest version of yt-dlp. Continue?"):
            thread = threading.Thread(target=self._update_yt_dlp_thread, daemon=True)
            thread.start()

    def _update_yt_dlp_thread(self):
        self.queue.put({'type': 'status', 'text': 'Updating yt-dlp...'})
        try:
            # Determine the correct asset for the OS
            if sys.platform == "win32":
                asset_name = "yt-dlp.exe"
            else:
                asset_name = "yt-dlp"

            # Get the latest release information from GitHub API
            response = requests.get("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest")
            response.raise_for_status()
            release_data = response.json()

            # Find the download URL for the correct asset
            asset_url = None
            for asset in release_data['assets']:
                if asset['name'] == asset_name:
                    asset_url = asset['browser_download_url']
                    break

            if not asset_url:
                raise Exception(f"Could not find asset: {asset_name}")

            # Download the new executable
            response = requests.get(asset_url, stream=True)
            response.raise_for_status()

            # Write the new executable to the assets folder
            yt_dlp_path = os.path.join("assets", asset_name)
            with open(yt_dlp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.queue.put({'type': 'status', 'text': 'yt-dlp updated successfully!'})
            messagebox.showinfo("Success", "yt-dlp has been updated to the latest version.")

        except Exception as e:
            print(f"yt-dlp update failed: {e}")
            self.queue.put({'type': 'status', 'text': 'Error: yt-dlp update failed.'})
            messagebox.showerror("Error", f"Failed to update yt-dlp. Check the console for details.")

    def open_settings(self):
        SettingsWindow(self.root, self)

    def change_theme(self, event):
        self.style.theme_use(self.theme_var.get())
        self.save_config()

    def save_history(self):
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.history, f, indent=2)

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    self.history = json.load(f)
            except json.JSONDecodeError:
                self.history = []

    def save_config(self):
        config = {
            "download_dir": self.download_dir.get(),
            "theme": self.theme_var.get()
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    self.download_dir.set(config.get("download_dir", os.getcwd()))
                    self.theme_var.set(config.get("theme", "darkly"))
            except json.JSONDecodeError:
                self.theme_var.set("darkly")  # Default on corrupt file
        else:
            self.theme_var.set("darkly")

        self.style.theme_use(self.theme_var.get())

    def update_history_view(self):
        for item in self.history_view.get_children():
            self.history_view.delete(item)

        for item in self.download_queue:
            self.history_view.insert(
                parent='', index=END,
                values=("Queued", item.get('title', 'N/A'), "", item.get('url', 'N/A'))
            )

        for item in reversed(self.history):
            self.history_view.insert(
                parent='', index=END,
                values=("Completed", item.get('title', 'N/A'), item.get('date', 'N/A'), item.get('url', 'N/A'))
            )

    def add_to_queue(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a YouTube URL")
            return

        is_playlist = 'list=' in url
        if is_playlist:
            self._fetch_playlist_info(url, download_now=False)
            return

        self.download_queue.append({
            "url": url,
            "quality": self.quality_var.get(),
            "audio_only": self.audio_only_var.get(),
            "embed_thumbnail": self.embed_thumbnail_var.get(),
            "title": "Fetching title..."
        })
        self.update_history_view()
        self.url_var.set("")

    def process_playlist_selection(self, selected_urls, download_now):
        if download_now:
            # If downloading now, process each selected URL individually
            for url in selected_urls:
                item = {
                    "url": url,
                    "quality": self.quality_var.get(),
                    "audio_only": self.audio_only_var.get(),
                    "embed_thumbnail": self.embed_thumbnail_var.get(),
                    "title": "Fetching title..."
                }
                self.is_cancelled = False
                self.open_folder_button.pack_forget()
                self._set_ui_state(DISABLED)
                self.status_var.set("Status: Starting download...")
                self.progress.config(value=0)
                self.percentage_var.set("0.0%")
                self.speed_var.set("")
                self.size_var.set("")

                thread = threading.Thread(target=self.run_download, args=(self.build_command(url, False, False, item), url), daemon=True)
                thread.start()
                self.after(100, self.process_queue)
        else:
            # If adding to queue, add each selected URL as a separate item
            for url in selected_urls:
                self.download_queue.append({
                    "url": url,
                    "quality": self.quality_var.get(),
                    "audio_only": self.audio_only_var.get(),
                    "embed_thumbnail": self.embed_thumbnail_var.get(),
                    "title": "Fetching title..."
                })
            self.update_history_view()
            self.url_var.set("")
            self._set_ui_state(NORMAL)

    def start_queue(self):
        if not self.download_queue:
            messagebox.showinfo("Queue Empty", "There are no videos in the queue.")
            return

        self.is_cancelled = False
        self.open_folder_button.pack_forget()
        self._set_ui_state(DISABLED)
        self.status_var.set("Status: Starting queue...")

        thread = threading.Thread(target=self.run_queue, daemon=True)
        thread.start()
        self.after(100, self.process_queue)

    def clear_history(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to delete all download history?"):
            self.history.clear()
            self.save_history()
            self.update_history_view()


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    root.title("Aria Youtube Downloader")
    root.geometry("900x700")
    style = ttk.Style()
    app = DownloaderApp(root, style)
    root.mainloop()