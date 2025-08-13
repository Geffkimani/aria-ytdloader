import tkinter as tk
from tkinterdnd2 import DND_FILES
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

class URLFrame(ttk.Frame):
    def __init__(self, master, app_logic):
        super().__init__(master)
        self.app = app_logic
        self.pack(fill=X, expand=YES, pady=5)
        ttk.Label(self, text="Video URL:", width=10).pack(side=LEFT, padx=(0,5))
        self.url_entry = ttk.Entry(self, textvariable=self.app.url_var)
        self.url_entry.pack(side=LEFT, fill=X, expand=YES, padx=5)
        try:
            self.url_entry.drop_target_register(DND_FILES)
            self.url_entry.dnd_bind("<<Drop>>", self.on_drop)
        except Exception:
            pass
        menu = tk.Menu(self.master, tearoff=0)
        menu.add_command(label="Paste", command=self.app.paste_url)
        self.url_entry.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))
        button_frame = ttk.Frame(self)
        button_frame.pack(side=LEFT, padx=5)
        self.add_to_queue_button = ttk.Button(button_frame, text="Add to Queue", command=self.app.add_to_queue, width=12, bootstyle=OUTLINE)
        self.add_to_queue_button.pack(side=LEFT, padx=2)
        self.download_now_button = ttk.Button(button_frame, text="Download Now", command=self.app.download_now, width=15, bootstyle=SUCCESS)
        self.download_now_button.pack(side=LEFT, padx=2)
        self.start_queue_button = ttk.Button(button_frame, text="Start Queue", command=self.app.start_queue, width=12, bootstyle=SUCCESS)
        self.start_queue_button.pack(side=LEFT, padx=2)
        self.cancel_button = ttk.Button(button_frame, text="Cancel All", command=self.app.cancel_download, width=12, bootstyle=DANGER)
    def on_drop(self, event):
        self.app.url_var.set(event.data.strip("{}"))
    def set_state(self, state):
        is_disabled = state == DISABLED
        self.url_entry.config(state=state)
        self.add_to_queue_button.config(state=state)
        self.download_now_button.config(state=state)
        self.start_queue_button.config(state=state)
        if is_disabled:
            self.start_queue_button.pack_forget()
            self.cancel_button.pack(side=LEFT, padx=2)
        else:
            self.cancel_button.pack_forget()
            self.start_queue_button.pack(side=LEFT, padx=2)
