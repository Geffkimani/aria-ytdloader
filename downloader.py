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

HISTORY_FILE = "history.json"
CONFIG_FILE = "settings.json"

class DownloaderApp(ttk.Frame):
    def __init__(self, master, style):
        super().__init__(master, padding=15)
        self.pack(fill=BOTH, expand=YES)
        self.root = master
        self.style = style

        # App variables
        self.download_dir = ttk.StringVar(value=os.getcwd())
        self.url_var = ttk.StringVar()
        self.quality_var = ttk.BooleanVar(value=False)
        self.audio_only_var = ttk.BooleanVar(value=False)
        self.embed_thumbnail_var = ttk.BooleanVar(value=False)
        self.theme_var = ttk.StringVar()
        self.history = []
        self.threads = []
        self.queue = Queue()
        self.current_process = None
        self.is_cancelled = False

        self.load_config()
        self.load_history()

        # UI Elements
        self.create_widgets()
        self.update_option_states() # Set initial state

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

        self.open_folder_button = ttk.Button(status_frame, text="Open Folder", command=self.open_download_folder, width=12)

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

        self.download_button = ttk.Button(url_row, text="Download", command=self.download, width=10, bootstyle=OUTLINE)
        self.download_button.pack(side=LEFT, padx=5)
        
        self.cancel_button = ttk.Button(url_row, text="Cancel", command=self.cancel_download, width=10, bootstyle=DANGER)

    def create_options_row(self, parent):
        options_row = ttk.Frame(parent)
        options_row.pack(fill=X, expand=YES, pady=5)

        self.quality_checkbox = ttk.Checkbutton(options_row, text="1080p", variable=self.quality_var, bootstyle="round-toggle")
        self.quality_checkbox.pack(side=LEFT, padx=5)

        self.audio_only_checkbox = ttk.Checkbutton(options_row, text="Audio Only (MP3)", variable=self.audio_only_var, bootstyle="round-toggle", command=self.update_option_states)
        self.audio_only_checkbox.pack(side=LEFT, padx=15)

        self.embed_thumbnail_checkbox = ttk.Checkbutton(options_row, text="Embed Thumbnail", variable=self.embed_thumbnail_var, bootstyle="round-toggle")
        self.embed_thumbnail_checkbox.pack(side=LEFT, padx=5)

        self.select_folder_button = ttk.Button(options_row, text="Save Location", command=self.select_folder, width=15, bootstyle=OUTLINE)
        self.select_folder_button.pack(side=LEFT, padx=5)

        self.clear_history_button = ttk.Button(options_row, text="Clear History", command=self.clear_history, width=15, bootstyle=OUTLINE)
        self.clear_history_button.pack(side=RIGHT, padx=5)

        self.close_button = ttk.Button(options_row, text="Close", command=self.root.quit, width=10, bootstyle="danger-outline")
        self.close_button.pack(side=RIGHT, padx=5)

        self.theme_selector = ttk.Combobox(options_row, textvariable=self.theme_var, values=self.style.theme_names(), state="readonly", width=10)
        self.theme_selector.pack(side=RIGHT, padx=5)
        self.theme_selector.bind("<<ComboboxSelected>>", self.change_theme)
        ttk.Label(options_row, text="Theme:").pack(side=RIGHT, padx=(0, 5))

    def create_history_view(self):
        self.history_view = ttk.Treeview(
            master=self, bootstyle=INFO, columns=['title', 'date', 'url'], show=HEADINGS
        )
        self.history_view.pack(fill=BOTH, expand=YES, pady=10)

        self.history_view.heading('title', text='Title', anchor=W)
        self.history_view.heading('date', text='Date', anchor=W)
        self.history_view.heading('url', text='URL', anchor=W)

        self.history_view.column('title', anchor=W, width=300)
        self.history_view.column('date', anchor=W, width=150)
        self.history_view.column('url', anchor=W, width=250)

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
        self.select_folder_button.config(state=state)
        self.clear_history_button.config(state=state)
        self.audio_only_checkbox.config(state=state)
        self.theme_selector.config(state=state)
        
        if is_downloading:
            self.download_button.pack_forget()
            self.cancel_button.pack(side=LEFT, padx=5)
        else:
            self.cancel_button.pack_forget()
            self.download_button.pack(side=LEFT, padx=5)

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
        is_downloading = self.download_button.cget('state') == DISABLED
        audio_only = self.audio_only_var.get()

        self.quality_checkbox.config(state=DISABLED if audio_only or is_downloading else NORMAL)
        self.embed_thumbnail_checkbox.config(state=NORMAL if audio_only and not is_downloading else DISABLED)
        
        if not audio_only:
            self.embed_thumbnail_var.set(False)

    def download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a YouTube URL")
            return

        is_playlist = 'list=' in url
        download_playlist = False
        if is_playlist:
            download_playlist = messagebox.askyesno(
                "Playlist Detected",
                "This URL belongs to a playlist. Do you want to download the entire playlist?",
                icon='question'
            )

        self.is_cancelled = False
        self.open_folder_button.pack_forget()
        cmd = self.build_command(url, is_playlist, download_playlist)

        self._set_ui_state(DISABLED)
        self.status_var.set("Status: Starting download...")
        self.progress.config(value=0)
        self.percentage_var.set("0.0%")
        self.speed_var.set("")
        self.size_var.set("")

        thread = threading.Thread(target=self.run_download, args=(cmd, url), daemon=True)
        thread.start()
        self.after(100, self.process_queue)

    def build_command(self, url, is_playlist, download_playlist):
        base_cmd = ["./assets/yt-dlp", url]
        
        if download_playlist:
            output_template = os.path.join(self.download_dir.get(), "%(playlist_title)s/%(playlist_index)s - %(title)s [%(id)s].%(ext)s")
        else:
            output_template = os.path.join(self.download_dir.get(), "%(title)s [%(id)s].%(ext)s")

        if self.audio_only_var.get():
            format_cmd = ["-f", "bestaudio/best", "-x", "--audio-format", "mp3"]
            if self.embed_thumbnail_var.get():
                format_cmd.append("--embed-thumbnail")
        else:
            quality = "1080" if self.quality_var.get() else "720"
            format_cmd = ["-f", f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"]

        playlist_cmd = []
        if is_playlist:
            playlist_cmd = ["--yes-playlist"] if download_playlist else ["--no-playlist"]

        remaining_cmd = [
            "--external-downloader", "./assets/aria2c",
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
                        self.status_var.set("Status: Error - Download failed")
                        messagebox.showerror("Download Failed", "An error occurred. Check console for details.")
                self._set_ui_state(NORMAL)
                self.current_process = None
                return
        except Empty:
            pass
        self.after(100, self.process_queue)

    def run_download(self, cmd, url):
        kwargs = {
            'stdout': subprocess.PIPE, 'stderr': subprocess.STDOUT, 
            'text': True, 'bufsize': 1, 'universal_newlines': True, 'encoding': 'utf-8'
        }
        if sys.platform != "win32":
            kwargs['start_new_session'] = True
        
        self.current_process = process = subprocess.Popen(cmd, **kwargs)

        for line in iter(process.stdout.readline, ''):
            if self.is_cancelled: break
            print(line.strip())

            playlist_match = re.search(r"^\[download\] Downloading video (\d+) of (\d+)", line)
            if playlist_match:
                current, total = playlist_match.groups()
                self.queue.put({'type': 'status', 'text': f"Downloading video {current}/{total}..."})
                self.queue.put({'type': 'progress', 'percent': 0, 'size': '', 'speed': ''})

            destination_match = re.search(r"^\[download\] Destination: (.+)", line)
            if destination_match:
                title = destination_match.group(1).strip()
                self.queue.put({'type': 'status', 'text': f"Downloading {os.path.basename(title)}"})

            progress_match = re.search(r"^\[download\]\s+([\d\.]+)% of\s+~?(.+?)\s+at\s+(.+?)\s+ETA", line)
            if progress_match:
                percentage = float(progress_match.group(1))
                size = progress_match.group(2).strip()
                speed = progress_match.group(3).strip()
                self.queue.put({'type': 'progress', 'percent': percentage, 'size': size, 'speed': speed})

            final_file_match = re.search(r'(?:^\[Merger\] Merging formats into "(.+)"|^\[ExtractAudio\] Destination: (.+))', line)
            if final_file_match:
                filepath = final_file_match.group(1) or final_file_match.group(2)
                if filepath:
                    history_entry = {
                        "title": os.path.basename(filepath),
                        "date": datetime.now().strftime(r'%Y-%m-%d %H:%M:%S'),
                        "url": url
                    }
                    self.queue.put({'type': 'video_done', 'history_entry': history_entry})

        process.wait()
        self.current_process = None

        if self.is_cancelled:
            self.queue.put({'type': 'cancelled'})
            return

        self.queue.put({'type': 'done', 'success': process.returncode == 0})

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
                self.theme_var.set("darkly") # Default on corrupt file
        else:
            self.theme_var.set("darkly")
        
        self.style.theme_use(self.theme_var.get())

    def update_history_view(self):
        for item in self.history_view.get_children():
            self.history_view.delete(item)
        for item in reversed(self.history):
            self.history_view.insert(
                parent='', index=END,
                values=(item.get('title', 'N/A'), item.get('date', 'N/A'), item.get('url', 'N/A'))
            )

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