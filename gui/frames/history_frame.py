import tkinter as tk
import webbrowser
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

class HistoryFrame(ttk.Frame):
    def __init__(self, master, app_logic):
        super().__init__(master)
        self.app = app_logic
        self.pack(fill=BOTH, expand=YES, pady=(5, 0))

        # --- Widgets ---
        self._create_toolbar()
        self._create_treeview()
        self._create_context_menu()

        # --- Bindings ---
        self.history_view.bind("<Button-3>", self.show_history_menu)
        self.history_view.bind("<Double-1>", self.open_selected_url)
        self.history_view.bind("<<TreeviewSelect>>", self.on_selection_change)

    def _create_toolbar(self):
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=X, pady=5)

        self.clear_history_button = ttk.Button(button_frame, text="Clear History", command=self.app.clear_history, bootstyle=DANGER)
        self.clear_history_button.pack(side=RIGHT, padx=5)

        self.actions_button = ttk.Button(button_frame, text="Actions", command=self.show_actions_menu, bootstyle=SECONDARY, state=DISABLED)
        self.actions_button.pack(side=RIGHT)

    def _create_treeview(self):
        self.history_view = ttk.Treeview(
            master=self, bootstyle=INFO, columns=['status', 'title', 'size', 'date', 'url'], show=HEADINGS
        )
        self.history_view.pack(side=LEFT, fill=BOTH, expand=YES)

        scrollbar = ttk.Scrollbar(self, orient=VERTICAL, command=self.history_view.yview)
        self.history_view.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.history_view.heading('status', text='Status', anchor=W)
        self.history_view.heading('title', text='Title', anchor=W)
        self.history_view.heading('size', text='Size', anchor=W)
        self.history_view.heading('date', text='Date', anchor=W)
        self.history_view.heading('url', text='Video URL', anchor=W)

        self.history_view.column('status', anchor=W, width=110, stretch=False)
        self.history_view.column('title', anchor=W, width=350)
        self.history_view.column('size', anchor=W, width=90, stretch=False)
        self.history_view.column('date', anchor=W, width=160, stretch=False)
        self.history_view.column('url', anchor=W, width=320)

    def _create_context_menu(self):
        self.history_menu = tk.Menu(self.master, tearoff=0)
        self.history_menu.add_command(label="Open File", command=self.app.open_history_file)
        self.history_menu.add_command(label="Show in Folder", command=self.app.reveal_history_file)
        self.history_menu.add_separator()
        self.history_menu.add_command(label="Copy Filename", command=self.app.copy_history_filename)
        self.history_menu.add_command(label="Copy File Path", command=self.app.copy_history_filepath)
        self.history_menu.add_command(label="Copy URL", command=self.app.copy_history_url)
        self.history_menu.add_separator()
        self.history_menu.add_command(label="Re-download", command=self.app.redownload_history_item)
        self.history_menu.add_command(label="Remove from List", command=self.app.remove_history_item)

    def show_history_menu(self, event):
        iid = self.history_view.identify_row(event.y)
        if iid:
            self.history_view.selection_set(iid)
            self.history_menu.tk_popup(event.x_root, event.y_root)

    def show_actions_menu(self):
        if not self.history_view.selection():
            return
        x = self.actions_button.winfo_rootx()
        y = self.actions_button.winfo_rooty() + self.actions_button.winfo_height()
        self.history_menu.tk_popup(x, y)

    def on_selection_change(self, event=None):
        if self.history_view.selection():
            self.actions_button.config(state=NORMAL)
        else:
            self.actions_button.config(state=DISABLED)

    def get_selected_item(self):
        selected_iids = self.history_view.selection()
        if not selected_iids: return None
        item_values = self.history_view.item(selected_iids[0], 'values')
        if not item_values: return None
        return {
            'status': item_values[0],
            'title': item_values[1],
            'size': item_values[2],
            'date': item_values[3],
            'url': item_values[4]
        }

    def update_view(self, queue, history):
        self.history_view.delete(*self.history_view.get_children())
        all_items = queue + history
        for item in all_items:
            status_text = item.get('status', 'N/A')
            if status_text == 'Completed' or status_text == 'Done':
                status_icon = '✅ Completed'
            elif status_text == 'Error' or status_text == 'Failed':
                status_icon = '❌ Failed'
            elif status_text == 'Downloading' or status_text == 'Queued':
                status_icon = '⏳ ' + status_text
            else:
                status_icon = status_text
            self.history_view.insert(
                parent='', index=0,
                values=(
                    status_icon,
                    item.get('title', 'N/A'),
                    item.get('size', ''),
                    item.get('date', ''), 
                    item.get('url', 'N/A')
                )
            )
        self.on_selection_change() # Update button state after view is updated

    def open_selected_url(self, event=None):
        item = self.get_selected_item()
        if item and item.get('url'):
            try:
                webbrowser.open(item['url'])
            except Exception:
                pass