import os
import json
import re
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, Text, BooleanVar, END, NORMAL, DISABLED
from tkinterdnd2 import DND_FILES, TkinterDnD
from ttkbootstrap import Style
from ttkbootstrap.widgets import Frame, Label, Entry, Button, Progressbar, Checkbutton, Scrollbar

HISTORY_FILE = "history.json"
CONFIG_FILE = "settings.json"

class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("yt-downloader")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        self.style = Style("darkly")

        self.download_dir = os.getcwd()
        self.history = []
        self.load_history()
        self.load_config()

        self.threads = []
        self.create_widgets()

    def create_widgets(self):
        wrapper = Frame(self.root, padding=15)
        wrapper.pack(fill="both", expand=True)

        header_frame = Frame(wrapper)
        header_frame.pack(fill="x", pady=(0, 5))

        Label(header_frame, text="YouTube URL").pack(side="left")
        Button(header_frame, text="Close", command=self.root.quit).pack(side="right")

        url_frame = Frame(wrapper)
        url_frame.pack(fill="x", pady=(0, 10))

        self.url_entry = Entry(url_frame, width=100)
        self.url_entry.pack(side="left", fill="x", expand=True)
        self.url_entry.drop_target_register(DND_FILES)
        self.url_entry.dnd_bind("<<Drop>>", self.on_drop)

        self.download_button = Button(url_frame, text="Download", command=self.download)
        self.download_button.pack(side="left", padx=10)

        # Right-click context menu
        menu = self.context_menu = self.create_context_menu()
        self.url_entry.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

        # Quality checkbox
        self.quality_var = BooleanVar(value=False)
        self.quality_checkbox = Checkbutton(wrapper, text="Download in 1080p (default 720p)", variable=self.quality_var)
        self.quality_checkbox.pack(anchor="w", pady=(0, 10))

        # Folder select + download row
        control_frame = Frame(wrapper)
        control_frame.pack(fill="x", pady=(0, 15))

        self.select_folder_button = Button(control_frame, text="Select Folder", command=self.select_folder)
        self.select_folder_button.pack(side="left")

        self.clear_history_button = Button(wrapper, text="Clear History", command=self.clear_history)
        self.clear_history_button.pack(anchor="e", pady=5)

        # Progress bar
        progress_frame = Frame(wrapper)
        progress_frame.pack(fill="x", pady=(0, 15))

        self.progress = Progressbar(progress_frame, length=100, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True)

        self.percentage_var = tk.StringVar()
        self.percentage_label = Label(progress_frame, textvariable=self.percentage_var)
        self.percentage_label.pack(side="left", padx=10)

        self.status_var = tk.StringVar()
        self.status_label = Label(wrapper, textvariable=self.status_var)
        self.status_label.pack(anchor="w", pady=(0, 5))

        self.speed_var = tk.StringVar()
        self.speed_label = Label(wrapper, textvariable=self.speed_var)
        self.speed_label.pack(anchor="w")

        self.size_var = tk.StringVar()
        self.size_label = Label(wrapper, textvariable=self.size_var)
        self.size_label.pack(anchor="w")

        # History label and clear button
        history_header_frame = Frame(wrapper)
        history_header_frame.pack(fill="x", pady=(0, 5))
        Label(history_header_frame, text="Download History").pack(side="left")
        self.clear_history_button = Button(history_header_frame, text="Clear History", command=self.clear_history)
        self.clear_history_button.pack(side="right")

        # History box with scrollbar
        hist_frame = Frame(wrapper)
        hist_frame.pack(fill="both", expand=True)

        self.history_box = Text(hist_frame, wrap="none", height=10)
        self.history_box.pack(side="left", fill="both", expand=True)

        scrollbar = Scrollbar(hist_frame, command=self.history_box.yview)
        scrollbar.pack(side="right", fill="y")
        self.history_box.config(yscrollcommand=scrollbar.set)

        self.update_history_box()

    def _set_ui_state(self, state):
        self.url_entry.config(state=state)
        self.download_button.config(state=state)
        self.quality_checkbox.config(state=state)
        self.select_folder_button.config(state=state)
        self.clear_history_button.config(state=state)

    def create_context_menu(self):
        menu = self.context_menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Paste", command=self.paste_url)
        return menu

    def on_drop(self, event):
        url = event.data.strip("{}")
        self.url_entry.delete(0, END)
        self.url_entry.insert(0, url)

    def paste_url(self):
        try:
            clipboard = self.root.clipboard_get()
            self.url_entry.delete(0, END)
            self.url_entry.insert(0, clipboard)
        except:
            pass

    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.download_dir = path
            self.save_config()

    def download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter or drop a YouTube URL")
            return

        fmt = "bestvideo[height=1080]+bestaudio/best[height=1080]" if self.quality_var.get() else "bestvideo[height=720]+bestaudio/best[height=720]"
        output = os.path.join(self.download_dir, "%(title)s [%(id)s].%(ext)s")
        cmd = [
            "./assets/yt-dlp", url,
            "-f", fmt,
            "--external-downloader", "./assets/aria2c",
            "--external-downloader-args", "-x 16 -k 1M",
            "-o", output,
            "--write-info-json",
            "--no-mtime"
        ]

        self._set_ui_state(DISABLED)
        thread = threading.Thread(target=self.run_download, args=(cmd,))
        thread.start()
        self.threads.append(thread)

    def run_download(self, cmd):
        self.progress.config(mode="determinate", value=0)
        self.percentage_var.set("0%")
        self.status_var.set("Downloading...")
        self.speed_var.set("")
        self.size_var.set("")

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        title = None
        current_video_index = 0
        total_videos = 0

        for line in iter(process.stdout.readline, ''):
            print(line.strip())

            # Detect playlist video start
            playlist_match = re.search(r"^\[download\] Downloading video (\d+) of (\d+)", line)
            if playlist_match:
                current_video_index = int(playlist_match.group(1))
                total_videos = int(playlist_match.group(2))
                self.status_var.set(f"Downloading video {current_video_index}/{total_videos}...")
                self.progress.config(value=0) # Reset progress for new video
                self.percentage_var.set("0%")
                self.speed_var.set("")
                self.size_var.set("")
                self.root.update_idletasks()

            # Detect video destination (title)
            destination_match = re.search(r"^\[download\] Destination: (.+)", line)
            if destination_match:
                title = destination_match.group(1).strip()
                if total_videos > 0:
                    self.status_var.set(f"Downloading video {current_video_index}/{total_videos}: {title}")
                else:
                    self.status_var.set(f"Downloading: {title}")
                self.root.update_idletasks()

            # Look for progress information from yt-dlp (which includes aria2c output)
            progress_match = re.search(r"^\[download\]\s+(\d+\.\d+)% of (\d+\.\d+[KMGT]?i?B) at (\d+\.\d+[KMGT]?i?B/s)", line)
            if progress_match:
                percentage = float(progress_match.group(1))
                size = progress_match.group(2)
                speed = progress_match.group(3)

                self.progress.config(value=percentage)
                self.percentage_var.set(f"{percentage:.1f}%")
                self.speed_var.set(f"Speed: {speed}")
                self.size_var.set(f"Size: {size}")
                self.root.update_idletasks()

        process.wait()
        self.progress.config(value=100)
        self.percentage_var.set("100%")
        if process.returncode == 0:
            self.status_var.set("Download complete!")
        else:
            self.status_var.set("Error: Download failed")

        if title:
            self.history.append(title)
            self.save_history()
            self.update_history_box()
        self._set_ui_state(NORMAL)

    def save_history(self):
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.history, f, indent=2)

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                self.history = json.load(f)

    def save_config(self):
        config = {"download_dir": self.download_dir}
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                self.download_dir = config.get("download_dir", os.getcwd())

    def update_history_box(self):
        self.history_box.config(state=NORMAL)
        self.history_box.delete("1.0", END)
        for item in self.history:
            self.history_box.insert(END, f"{item}\n")
        self.history_box.config(state=DISABLED)

    def clear_history(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to delete all history?"):
            self.history.clear()
            self.save_history()
            self.update_history_box()

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = DownloaderApp(root)
    root.mainloop()
