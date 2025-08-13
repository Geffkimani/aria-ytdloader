import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from typing import List, Dict, Any

from gui.base_selection_window import BaseSelectionWindow

class PlaylistSelectionWindow(BaseSelectionWindow):
    CHECKED = "☑"
    UNCHECKED = "☐"
    def __init__(self, master: tk.Tk, app_instance: Any, videos: List[Dict[str, Any]], original_url: str, download_now: bool):
        self.videos = videos or []
        self.original_url = original_url
        self.selection_state = {str(v.get('id')): True for v in self.videos}
        super().__init__(master, app_instance, "Select Playlist Videos", download_now, geometry="900x600")
    def _setup_tree_columns(self) -> None:
        ttk.Button(self.top_button_frame, text="Select All", command=lambda: self._toggle_all(True), bootstyle="info").pack(side=tk.LEFT, padx=5)
        ttk.Button(self.top_button_frame, text="Select None", command=lambda: self._toggle_all(False), bootstyle="secondary").pack(side=tk.LEFT, padx=5)
        self.tree["columns"] = ("select", "title", "video_id")
        columns = [("select", "✓", 50, tk.CENTER), ("title", "Title", 600, tk.W), ("video_id", "ID", 150, tk.CENTER)]
        for col, text, width, anchor in columns:
            self.tree.heading(col, text=text, anchor=anchor)
            self.tree.column(col, width=width, anchor=anchor, stretch=False if col != 'title' else True)
        self.confirm_button.config(text="Download Selected Videos")
    def _populate_tree(self) -> None:
        if not self.videos:
            messagebox.showwarning("No Videos Found", "No videos were found in this playlist.", parent=self)
            self.destroy()
            return
        for video in self.videos:
            video_id = str(video.get("id", ""))
            self.tree.insert("", tk.END, iid=video_id, values=(self.CHECKED if self.selection_state.get(video_id) else self.UNCHECKED, video.get("title","Untitled"), video_id))
    def _bind_events(self) -> None:
        super()._bind_events()
        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)
        self.tree.bind("<space>", self._toggle_focused_row)
    def _on_tree_click(self, event):
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if row_id and col_id == "#1":
            self._toggle_item(row_id)
    def _toggle_focused_row(self, event):
        focused_id = self.tree.focus()
        if focused_id:
            self._toggle_item(focused_id)
    def _toggle_item(self, item_id: str):
        if not item_id:
            return
        cur = self.selection_state.get(item_id, False)
        new = not cur
        self.selection_state[item_id] = new
        self.tree.set(item_id, "select", self.CHECKED if new else self.UNCHECKED)
    def _toggle_all(self, select: bool) -> None:
        for item_id in self.tree.get_children():
            self.selection_state[item_id] = select
            self.tree.set(item_id, "select", self.CHECKED if select else self.UNCHECKED)
    def _on_confirm(self) -> None:
        selected_urls = [video["url"] for video in self.videos if self.selection_state.get(str(video.get("id")))]
        if not selected_urls:
            messagebox.showwarning("No Videos Selected", "Please select at least one video to download.", parent=self)
            return
        self.destroy()
        self.app.process_playlist_selection(selected_urls, self.download_now)