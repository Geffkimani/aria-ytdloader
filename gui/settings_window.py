import tkinter as tk
import ttkbootstrap as ttk
from tkinter import StringVar, IntVar

class SettingsWindow(ttk.Toplevel):
    def __init__(self, master: tk.Tk, app_instance):
        super().__init__(master)
        self.title("Settings")
        self.geometry("550x400")
        self.app = app_instance
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self._create_widgets()

    def _create_widgets(self) -> None:
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        self._create_combobox_row(main_frame, "Theme:", self.app.theme_var, self.app.style.theme_names(), self.app.change_theme)
        self._create_entry_button_row(main_frame, "Download Folder:", self.app.download_dir, "Browse", self.app.select_folder)
        self._create_combobox_row(main_frame, "Video Format:", self.app.video_format_var, ["mp4", "mkv", "webm"])
        self._create_combobox_row(main_frame, "Audio Format:", self.app.audio_format_var, ["mp3", "m4a", "wav"])
        self._create_combobox_row(main_frame, "Concurrent Downloads:", self.app.concurrent_downloads_var, [1,2,3,4,5])
        self._create_entry_row(main_frame, "Chrome Extension ID:", self.app.extension_id_var)
        # Verbose toggle
        self._create_checkbox_row(main_frame, "Verbose Logs:", self.app.verbose_logs_var)
        action_frame = ttk.Labelframe(main_frame, text="Actions", padding=10)
        action_frame.pack(fill=tk.X, pady=15)
        self._create_button_row(action_frame, "Update yt-dlp", self.app.update_yt_dlp, "primary")
        self._create_button_row(action_frame, "Clear Completed History", self.app.clear_history, "danger")
        save_frame = ttk.Frame(main_frame, padding=(0, 10))
        save_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(save_frame, text="Save and Close", command=self.save_and_close, bootstyle="success").pack()

    def _create_combobox_row(self, parent, label: str, variable: StringVar | IntVar, values: list, callback=None):
        frame = ttk.Frame(parent, padding=(0,5))
        frame.pack(fill=tk.X)
        ttk.Label(frame, text=label, width=20).pack(side=tk.LEFT)
        combobox = ttk.Combobox(frame, textvariable=variable, values=values, state="readonly")
        combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        if callback:
            combobox.bind("<<ComboboxSelected>>", callback)

    def _create_entry_button_row(self, parent, label: str, variable: StringVar, button_text: str, command):
        frame = ttk.Frame(parent, padding=(0,5))
        frame.pack(fill=tk.X)
        ttk.Label(frame, text=label, width=20).pack(side=tk.LEFT)
        ttk.Entry(frame, textvariable=variable, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(frame, text=button_text, command=command, bootstyle="info-outline").pack(side=tk.LEFT)

    def _create_entry_row(self, parent, label: str, variable: StringVar):
        frame = ttk.Frame(parent, padding=(0,5))
        frame.pack(fill=tk.X)
        ttk.Label(frame, text=label, width=20).pack(side=tk.LEFT)
        ttk.Entry(frame, textvariable=variable).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    def _create_button_row(self, parent, text: str, command, style: str):
        ttk.Button(parent, text=text, command=command, bootstyle=style).pack(fill=tk.X, pady=2)

    def _create_checkbox_row(self, parent, label: str, variable: tk.BooleanVar):
        frame = ttk.Frame(parent, padding=(0,5))
        frame.pack(fill=tk.X)
        ttk.Label(frame, text=label, width=20).pack(side=tk.LEFT)
        ttk.Checkbutton(frame, variable=variable, bootstyle="round-toggle").pack(side=tk.LEFT)

    def save_and_close(self):
        self.app.save_config()
        # Immediately apply theme without restart
        try:
            self.app.style.theme_use(self.app.theme_var.get())
        except Exception:
            pass
        self.destroy()