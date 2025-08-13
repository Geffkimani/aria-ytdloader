import re
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from typing import List, Dict, Optional, Any

from gui.base_selection_window import BaseSelectionWindow

class FormatSelectionWindow(BaseSelectionWindow):
    def __init__(self, master: tk.Tk, app_instance: Any, formats: List[Dict[str, Any]], url: str, download_now: bool):
        self.formats = formats or []
        self.url = url
        self.selected_format_id: Optional[str] = None
        super().__init__(master, app_instance, "Select Format", download_now, geometry="850x500")

    def _setup_tree_columns(self) -> None:
        self.tree["columns"] = ("id", "ext", "res", "vcodec", "acodec", "size", "note")
        columns = [
            ("id", "ID", 100, tk.W),
            ("ext", "Ext", 60, tk.CENTER),
            ("res", "Resolution", 120, tk.W),
            ("vcodec", "Video Codec", 120, tk.W),
            ("acodec", "Audio Codec", 120, tk.W),
            ("size", "Size (MB)", 100, tk.E),
            ("note", "Note", 200, tk.W),
        ]
        for col_id, text, width, anchor in columns:
            self.tree.heading(col_id, text=text, anchor=anchor)
            self.tree.column(col_id, width=width, anchor=anchor)
        self.confirm_button.config(text="Download Selected Format")

    def _populate_tree(self) -> None:
        if not self.formats:
            messagebox.showwarning("No Formats Found", "No available formats to display.")
            self.destroy()
            return
        def sort_key(fmt):
            height = fmt.get("height") or 0
            abr = fmt.get("abr") or 0
            return (height, abr)
        for fmt in sorted(self.formats, key=sort_key, reverse=True):
            filesize = fmt.get("filesize")
            if filesize:
                try:
                    filesize = f"{filesize / (1024*1024):.2f}"
                except Exception:
                    filesize = "N/A"
            else:
                filesize = "N/A"
            self.tree.insert("", tk.END, values=(fmt.get("format_id",""), fmt.get("ext",""), fmt.get("resolution",""), fmt.get("vcodec",""), fmt.get("acodec",""), filesize, fmt.get("format_note","")))
    def _bind_events(self) -> None:
        super()._bind_events()
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
    def _on_select(self, event=None) -> None:
        selected = self.tree.selection()
        if selected:
            self.selected_format_id = self.tree.item(selected[0])["values"][0]
    def _on_confirm(self) -> None:
        if not self.selected_format_id:
            messagebox.showwarning("No Format Selected", "Please select a format to download.", parent=self)
            return
        self.destroy()
        self.app.process_format_selection(self.url, self.selected_format_id, self.download_now)