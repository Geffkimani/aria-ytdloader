import tkinter as tk
import ttkbootstrap as ttk
from typing import Any, Protocol

class SelectionWindowProtocol(Protocol):
    def _setup_tree_columns(self) -> None: ...
    def _populate_tree(self) -> None: ...
    def _on_confirm(self) -> None: ...

class BaseSelectionWindow(ttk.Toplevel):
    def __init__(self, master: tk.Tk, app_instance: Any, title: str, download_now: bool, geometry: str = "800x600"):
        super().__init__(master)
        self.title(title)
        self.geometry(geometry)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.app = app_instance
        self.download_now = download_now
        self._create_base_widgets()
        self._setup_tree_columns()
        self._populate_tree()
        self._bind_events()

    def _create_base_widgets(self) -> None:
        self.top_button_frame = ttk.Frame(self, padding=(10, 10, 10, 0))
        self.top_button_frame.pack(fill=tk.X)
        tree_frame = ttk.Frame(self, padding=(10, 5, 10, 5))
        tree_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tree_frame, show="headings", bootstyle="info")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview, bootstyle="info-round")
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.bottom_action_frame = ttk.Frame(self, padding=(10, 5, 10, 10))
        self.bottom_action_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.confirm_button = ttk.Button(self.bottom_action_frame, command=self._on_confirm, bootstyle="success")
        self.confirm_button.pack(side=tk.RIGHT, padx=5)
        ttk.Button(self.bottom_action_frame, text="Cancel", command=self.destroy, bootstyle="secondary").pack(side=tk.RIGHT, padx=5)

    def _setup_tree_columns(self) -> None:
        raise NotImplementedError

    def _populate_tree(self) -> None:
        raise NotImplementedError

    def _on_confirm(self) -> None:
        raise NotImplementedError

    def _bind_events(self) -> None:
        self.tree.bind("<Double-1>", lambda e: self._on_confirm())
        self.bind("<Escape>", lambda e: self.destroy())