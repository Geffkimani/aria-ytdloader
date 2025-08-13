import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
import time

class ProgressFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill=X, expand=NO, pady=5)
        
        # --- State Variables ---
        self._details_visible = False
        self._last_progress_update = 0.0
        self._last_output_line = None
        self._max_output_lines = 500

        # --- UI Creation ---
        self._create_widgets()
        self.set_idle_state() # Set initial state

    def _create_widgets(self):
        # --- Compact Info Bar (Always Visible) ---
        info_bar = ttk.Frame(self)
        info_bar.pack(fill=X, expand=YES, padx=5, pady=2)

        self.progress = ttk.Progressbar(info_bar, mode='determinate', bootstyle=(STRIPED, SUCCESS))
        self.progress.pack(side=LEFT, fill=X, expand=YES)

        self.toggle_details_button = ttk.Button(info_bar, text="Show Details", command=self.toggle_details, bootstyle=SECONDARY, width=12)
        self.toggle_details_button.pack(side=RIGHT, padx=(10, 0))

        # Prominent progress label below the bar
        self.progress_label = ttk.Label(self, text="", font=("", 10, "bold"))
        self.progress_label.pack(anchor=W, fill=X, padx=5, pady=(2, 4))

        # --- Collapsible Details Area ---
        self.details_frame = ttk.Frame(self)

        self.output_text = tk.Text(self.details_frame, height=12, wrap=tk.WORD, font=("Consolas", 9), relief=tk.SOLID, borderwidth=1)
        self.output_text.pack(side=LEFT, fill=BOTH, expand=YES, padx=(5,0), pady=5)
        
        scrollbar = ttk.Scrollbar(self.details_frame, orient=tk.VERTICAL, command=self.output_text.yview, bootstyle="info-round")
        self.output_text.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=tk.Y, padx=(0,5), pady=5)

    def set_idle_state(self):
        """Resets the progress frame to its default idle state."""
        self.progress['value'] = 0
        self.progress_label.config(text="✅ Ready for new download", bootstyle=SUCCESS)
        if hasattr(self, 'playlist_label'):
            self.playlist_label.config(text="")

    def toggle_details(self):
        if self._details_visible:
            self.details_frame.pack_forget()
            self.toggle_details_button.config(text="Show Details")
            self._details_visible = False
        else:
            self.details_frame.pack(fill=BOTH, expand=YES, padx=0, pady=0)
            self.toggle_details_button.config(text="Hide Details")
            self._details_visible = True

    def add_output_line(self, text: str):
        """Add a new line to the output display, ensuring it is visible."""
        self.output_text.insert(tk.END, text + "\n")
        try:
            line_count = int(self.output_text.index('end-1c').split('.')[0])
            if line_count > self._max_output_lines:
                self.output_text.delete('1.0', f'{line_count - self._max_output_lines}.0')
        except Exception:
            pass
        self.output_text.see(tk.END)  # Auto-scroll to bottom
        
    def clear_output(self):
        """Clear the text log and prepare labels for a new download."""
        self.output_text.delete(1.0, tk.END)
        self.progress_label.config(text="Preparing download...", bootstyle=INFO)
        self.progress['value'] = 0
        self._last_progress_update = 0.0
        self._last_output_line = None

    def update_progress_display(self, percent: float, text: str):
        """Update a prominent progress label, throttled to ~1Hz."""
        now = time.time()
        if now - self._last_progress_update < 1.0 and percent < 100:
            return
        self._last_progress_update = now
        self.progress_label.config(text=text, bootstyle=INFO)

    def show_success(self, message: str):
        self.progress_label.config(text=f"✅ {message}", bootstyle=SUCCESS)

    def set_playlist_summary(self, text: str):
        if not hasattr(self, 'playlist_label'):
            self.playlist_label = ttk.Label(self, text="", font=("", 9))
            self.playlist_label.pack(anchor=W, padx=5, before=self.details_frame)
        self.playlist_label.config(text=text)

    def bind_verbose_var(self, tk_bool_var):
        # This frame no longer has a verbose checkbox, but we keep the method
        # to avoid breaking the main window's call to it.
        pass
