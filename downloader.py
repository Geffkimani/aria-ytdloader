import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import os

# === Paths ===
YT_DLP_PATH = "./assets/yt-dlp"
ARIA2C_PATH = "./assets/aria2c"
SESSION_FILE = "aria2.session"

# === App ===
root = tk.Tk()
root.title("YouTube Downloader")
root.geometry("600x400")

# === URL Entry ===
tk.Label(root, text="Video URL:").pack()
url_entry = tk.Entry(root, width=70)
url_entry.pack(pady=5)

# === 1080p Checkbox ===
quality_var = tk.BooleanVar()
quality_checkbox = tk.Checkbutton(root, text="Download in 1080p (unchecked = 720p)", variable=quality_var)
quality_checkbox.pack()

# === Progress Bar ===
progress = ttk.Progressbar(root, orient=tk.HORIZONTAL, length=500, mode='determinate')
progress.pack(pady=10)

# === Format Code Entry ===
tk.Label(root, text="Format Code (Optional):").pack()
format_entry = tk.Entry(root, width=20)
format_entry.pack()


# === Notifications ===
def notify(msg):
    messagebox.showinfo("Info", msg)


# === Start Aria2c ===
def start_aria2c():
    if not os.path.exists(SESSION_FILE):
        open(SESSION_FILE, 'w').close()
    try:
        subprocess.Popen([
            ARIA2C_PATH,
            "--enable-rpc", "--rpc-listen-all=true", "--rpc-allow-origin-all",
            "--continue", f"--input-file={SESSION_FILE}", f"--save-session={SESSION_FILE}"
        ])
        notify("aria2c started successfully")
    except Exception as e:
        messagebox.showerror("Aria2c Error", str(e))


# === Fetch Formats ===
def fetch_formats():
    url = url_entry.get()
    if not url:
        return notify("Please enter a URL")
    progress.config(mode='indeterminate')
    progress.start()

    def run():
        try:
            subprocess.run([YT_DLP_PATH, "-F", url], check=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to fetch formats:\n{e}")
        finally:
            progress.stop()

    threading.Thread(target=run).start()


# === Download ===
def download():
    url = url_entry.get()
    format_code = format_entry.get()
    if not url:
        return notify("Please enter a URL")

    quality = "bestvideo[height=1080]+bestaudio/best[height=1080]" if quality_var.get() else \
        "bestvideo[height=720]+bestaudio/best[height=720]"

    cmd = [
        YT_DLP_PATH,
        "-f", format_code if format_code else quality,
        "--external-downloader", "aria2c",
        "--external-downloader-args", "-x 16 -k 1M",
        url
    ]

    progress.config(mode='determinate', value=0)

    def run():
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                print(line.strip())
                # simulate progress (optional: real parsing with regex)
                if "%" in line:
                    try:
                        pct = float(line.split('%')[0].strip().split()[-1])
                        progress["value"] = pct
                    except:
                        pass
            process.wait()
            notify("Download completed!")
        except Exception as e:
            messagebox.showerror("Download Error", str(e))
        finally:
            progress["value"] = 100

    threading.Thread(target=run).start()


# === Buttons ===
tk.Button(root, text="Start aria2c", command=start_aria2c).pack(pady=5)
tk.Button(root, text="Fetch Formats", command=fetch_formats).pack(pady=5)
tk.Button(root, text="Download", command=download).pack(pady=5)
tk.Button(root, text="Close", command=root.quit, fg="red").pack(pady=20)

# === Launch GUI ===
root.mainloop()
