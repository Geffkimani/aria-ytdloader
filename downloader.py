import os
import json
import subprocess
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
from ttkbootstrap import Style
from ttkbootstrap.constants import *
from ttkbootstrap import Frame, Label, Entry, Button, Progressbar, Checkbutton, BooleanVar, Text, Scrollbar

HISTORY_FILE = "history.json"
ARIA2_SESSION = "aria2.session"

class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.geometry("700x500")
        self.style = Style("darkly")

        self.download_dir = os.getcwd()
        self.download_threads = []
        self.history = []
        self.load_history()

        self.create_widgets()

    def create_widgets(self):
        main_frame = Frame(self.root, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        Label(main_frame, text="Enter or Drop YouTube URL:").pack(anchor=W)

        self.url_entry = Entry(main_frame, width=100)
        self.url_entry.pack(fill=X, pady=5)
        self.url_entry.drop_target_register(DND_FILES)
        self.url_entry.dnd_bind('<<Drop>>', self.on_drop)

        right_click_menu = tk.Menu(self.root, tearoff=0)
        right_click_menu.add_command(label="Paste", command=self.paste_url)
        self.url_entry.bind("<Button-3>", lambda e: right_click_menu.tk_popup(e.x_root, e.y_root))

        self.quality_var = BooleanVar(value=False)
        Checkbutton(main_frame, text="Download 1080p (default is 720p)", variable=self.quality_var).pack(anchor=W)

        Button(main_frame, text="Select Download Folder", command=self.select_folder).pack(anchor=W, pady=(5, 10))
        Button(main_frame, text="Download", command=self.download).pack(anchor=W)
        Button(main_frame, text="Close", command=self.root.quit).pack(anchor=W, pady=(5, 10))

        self.progress = Progressbar(main_frame, length=300, mode='determinate')
        self.progress.pack(fill=X, pady=(5, 5))

        Label(main_frame, text="Download History:").pack(anchor=W)

        hist_frame = Frame(main_frame)
        hist_frame.pack(fill=BOTH, expand=True)

        self.history_box = Text(hist_frame, height=10, wrap="none")
        self.history_box.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar = Scrollbar(hist_frame, command=self.history_box.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.history_box.config(yscrollcommand=scrollbar.set)

        Button(main_frame, text="Delete History", command=self.clear_history).pack(anchor=W, pady=5)

        self.update_history_box()

    def on_drop(self, event):
        dropped = event.data.strip('{}')
        self.url_entry.delete(0, END)
        self.url_entry.insert(0, dropped)

    def paste_url(self):
        self.url_entry.delete(0, END)
        self.url_entry.insert(0, self.root.clipboard_get())

    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.download_dir = path

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

        thread = threading.Thread(target=self.run_download, args=(cmd, url))
        thread.start()
        self.download_threads.append(thread)

    def run_download(self, cmd, url):
        self.progress.config(mode="indeterminate")
        self.progress.start(10)

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        title = None
        for line in process.stdout:
            print(line.strip())
            if '[download] Destination:' in line:
                title = line.split('Destination:')[1].strip()

        self.progress.stop()
        self.progress.config(mode="determinate", value=100)

        if title:
            self.history.append(title)
            self.save_history()
            self.update_history_box()

    def update_history_box(self):
        self.history_box.config(state=NORMAL)
        self.history_box.delete(1.0, END)
        for item in self.history:
            self.history_box.insert(END, f"{item}\n")
        self.history_box.config(state=DISABLED)

    def save_history(self):
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.history, f, indent=2)

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                self.history = json.load(f)

    def clear_history(self):
        if messagebox.askyesno("Confirm", "Delete download history?"):
            self.history.clear()
            self.save_history()
            self.update_history_box()

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = DownloaderApp(root)
    root.mainloop()
