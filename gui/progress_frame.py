import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk

class ProgressFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill=X, expand=NO, pady=5)

        # Progress bar
        self.progress = ttk.Progressbar(self, mode='determinate', bootstyle=(STRIPED, SUCCESS))
        self.progress.pack(fill=X, padx=5, pady=5)

        # Label for detailed progress text (e.g., percentage, speed, ETA)
        self.progress_label = ttk.Label(self, text="", font=("Consolas", 9))
        self.progress_label.pack(anchor=W, padx=5)

        # Text area for general output/logs
        ttk.Label(self, text="Download Output:", font=("", 10, "bold")).pack(anchor=W, padx=5, pady=(5,2))
        self.output_text = tk.Text(self, height=10, wrap=tk.WORD, font=("Consolas", 9), relief=tk.SOLID, borderwidth=1)
        self.output_text.pack(side=LEFT, fill=BOTH, expand=YES, padx=5, pady=5)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.output_text.yview, bootstyle="info-round")
        self.output_text.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)

    def update_progress_display(self, percent: float, text: str):
        self.progress['value'] = percent
        self.progress_label['text'] = text
        self.add_output_line(text) # also log to the main output

    def add_output_line(self, text: str):
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)

    def clear_output(self):
        self.output_text.delete(1.0, tk.END)
        self.progress_label['text'] = ""
        self.progress['value'] = 0

