import ttkbootstrap as ttk
from ttkbootstrap.constants import *

class OptionsFrame(ttk.Frame):
    def __init__(self, master, app_logic):
        super().__init__(master)
        self.app = app_logic
        self.pack(fill=X, expand=YES, pady=5)

        # Left side for quality and audio options
        left_frame = ttk.Frame(self)
        left_frame.pack(side=LEFT, fill=X, expand=YES, padx=5)

        self.quality_combobox = ttk.Combobox(left_frame, textvariable=self.app.quality_var,
                                            values=['1080p', '720p', '480p', '360p'],
                                            state="readonly", width=10)
        self.quality_combobox.pack(side=LEFT, padx=(0, 5))
        ttk.Label(left_frame, text="Quality:").pack(side=LEFT)

        self.audio_only_checkbox = ttk.Checkbutton(left_frame, text="Audio Only", variable=self.app.audio_only_var,
                                                  bootstyle="round-toggle", command=self.app.update_option_states)
        self.audio_only_checkbox.pack(side=LEFT, padx=15)

        self.embed_thumbnail_checkbox = ttk.Checkbutton(left_frame, text="Embed Thumbnail",
                                                       variable=self.app.embed_thumbnail_var, bootstyle="round-toggle")
        self.embed_thumbnail_checkbox.pack(side=LEFT, padx=5)

        # Right side for action buttons
        right_frame = ttk.Frame(self)
        right_frame.pack(side=RIGHT, fill=X, padx=5)

        self.select_folder_button = ttk.Button(right_frame, text="Save Location", command=self.app.select_folder, width=15,
                                              bootstyle=OUTLINE)
        self.select_folder_button.pack(side=LEFT, padx=5)

        self.settings_button = ttk.Button(right_frame, text="Settings", command=self.app.open_settings, width=10,
                                         bootstyle=INFO)
        self.settings_button.pack(side=LEFT, padx=5)

    def set_state(self, state):
        is_disabled = state == DISABLED
        audio_only = self.app.audio_only_var.get()

        self.quality_combobox.config(state=DISABLED if is_disabled or audio_only else 'readonly')
        self.audio_only_checkbox.config(state=state)
        self.embed_thumbnail_checkbox.config(state=DISABLED if is_disabled or not audio_only else NORMAL)
        self.select_folder_button.config(state=state)
        self.settings_button.config(state=state)

        if not audio_only:
            self.app.embed_thumbnail_var.set(False)
