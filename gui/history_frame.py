import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

class HistoryFrame(ttk.Frame):
    def __init__(self, master, app_logic):
        super().__init__(master)
        self.app = app_logic
        self.pack(fill=BOTH, expand=YES, pady=(5, 0))
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=X, pady=5)
        self.clear_history_button = ttk.Button(button_frame, text="Clear History", command=self.app.clear_history, bootstyle=DANGER)
        self.clear_history_button.pack(side=RIGHT, padx=5)
        self.history_view = ttk.Treeview(master=self, bootstyle=INFO, columns=['status', 'title', 'date', 'url'], show=HEADINGS)
        self.history_view.pack(side=LEFT, fill=BOTH, expand=YES)
        scrollbar = ttk.Scrollbar(self, orient=VERTICAL, command=self.history_view.yview)
        self.history_view.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.history_view.heading('status', text='Status', anchor=W)
        self.history_view.heading('title', text='Title', anchor=W)
        self.history_view.heading('date', text='Date', anchor=W)
        self.history_view.heading('url', text='Video URL', anchor=W)
        self.history_view.column('status', anchor=W, width=100, stretch=False)
        self.history_view.column('title', anchor=W, width=350)
        self.history_view.column('date', anchor=W, width=150, stretch=False)
        self.history_view.column('url', anchor=W, width=300)
        self.history_menu = tk.Menu(self.master, tearoff=0)
        self.history_menu.add_command(label="Copy URL", command=self.app.copy_history_url)
        self.history_menu.add_command(label="Re-download", command=self.app.redownload_history_item)
        self.history_menu.add_separator()
        self.history_menu.add_command(label="Remove from List", command=self.app.remove_history_item)
        self.history_view.bind("<Button-3>", self.show_history_menu)

    def show_history_menu(self, event):
        iid = self.history_view.identify_row(event.y)
        if iid:
            self.history_view.selection_set(iid)
            self.history_menu.tk_popup(event.x_root, event.y_root)

    def get_selected_item(self):
        selected_iids = self.history_view.selection()
        if not selected_iids: return None
        item_values = self.history_view.item(selected_iids[0], 'values')
        if not item_values: return None
        return {'status': item_values[0], 'title': item_values[1], 'date': item_values[2], 'url': item_values[3]}

    def update_view(self, queue, history):
        self.history_view.delete(*self.history_view.get_children())
        all_items = queue + history
        for item in all_items:
            self.history_view.insert(parent='', index=0, values=(item.get('status','N/A'), item.get('title','N/A'), item.get('date',''), item.get('url','N/A')))
