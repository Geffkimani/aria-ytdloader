"""
Refactored main entrypoint:
- clear startup order: init DB -> check deps -> start GUI -> attach API -> run server
- improved shutdown
"""
import logging
import sys
import tkinter as tk
from tkinter import messagebox
from tkinterdnd2 import TkinterDnD
import ttkbootstrap as ttk
import signal

from gui.main_window import DownloaderApp
from server import Server
from utils import check_dependencies
import database
from api import attach_downloader_instance

import logging.handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            "downloader.log", maxBytes=10 * 1024 * 1024, backupCount=5
        ),
    ],
)


class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Aria YouTube Downloader")
        self.geometry("900x700")
        style = ttk.Style()
        self.app_instance = DownloaderApp(self, style)
        self.server = None

    def on_closing(self):
        logging.info("Shutting down application")
        try:
            self.app_instance.quit()
        except Exception:
            pass
        finally:
            if self.server:
                self.server.shutdown()
                self.server.join(timeout=5)
            try:
                self.destroy()
            except tk.TclError:
                pass

def main():
    database.init_db()
    if not check_dependencies(gui_mode=True):
        logging.error("Missing dependencies; exiting")
        sys.exit(1)
    app = None
    try:
        app = App()
        # Graceful Ctrl+C handling: close window instead of traceback
        def _sigint_handler(signum, frame):
            try:
                app.on_closing()
            except Exception:
                pass
        try:
            signal.signal(signal.SIGINT, _sigint_handler)
        except Exception:
            pass
        attach_downloader_instance(app.app_instance)
        server = Server(app.app_instance)
        server.start()
        app.server = server
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        logging.info("Starting GUI mainloop")
        app.mainloop()
    except Exception:
        logging.exception("Failed to start application")
        if app:
            try:
                app.on_closing()
            except Exception:
                pass
        sys.exit(1)

if __name__ == "__main__":
    main()
