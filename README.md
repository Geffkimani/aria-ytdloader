# 🎬 YouTube Downloader PC App

A modernish, user-friendly desktop YouTube video downloader built with Python, `yt-dlp`, and `aria2c`, featuring:

- 🔥 720p/1080p quality selection  
- 💾 Download folder selector  
- ⚡ Fast multithreaded downloads via `aria2c`  
- 🧠 Persistent download history (`history.json`)  
- 🌙 Dark Mode GUI with Tkinter + ttkbootstrap  
- 📥 Drag-and-drop URLs & Right-click context menu  
- 📊 Progress bar with ETA and speed tracking  

---

## 🚀 Features

- ✅ Drag-and-drop YouTube URLs
- ✅ Download progress with speed & file size
- ✅ Save location selection
- ✅ Persistent download history with clear option
- ✅ 720p by default, 1080p optional
- ✅ Portable, no installation required (after `.exe` build)

---

## 📦 Requirements (for development)

To run it from source:

```bash
git clone https://github.com/yourusername/youtube-downloader-app.git
cd youtube-downloader-app
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt


##Python Dependencies
ttkbootstrap

tkinterdnd2

Install with:

bash
Copy
Edit
pip install ttkbootstrap tkinterdnd2
