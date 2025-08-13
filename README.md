# AriaDownloader: A Comprehensive Download Manager

A modern, user-friendly desktop download manager built with Python. It uses `yt-dlp` for video services and `aria2c` for accelerated file downloads, offering a robust feature set accessible through multiple interfaces.

---

## 🏛️ Architecture

AriaDownloader is composed of three main components working together:

1.  **Desktop GUI**: The main interface, built with `Tkinter` and `ttkbootstrap`, for managing downloads, viewing history, and configuring settings.
2.  **Web Server (API)**: A `FastAPI` server that runs in the background, exposing an endpoint to add new downloads programmatically. This is what the browser extension and other tools use.
3.  **Browser Extension**: A simple browser extension to send links from your browser directly to the download queue.

---

## 🚀 Features

- ✅ **Multi-Interface**: Manage downloads via a Desktop GUI, a Web API, or a Browser Extension.
- ✅ **Accelerated Downloads**: Uses `aria2c` for fast, multi-threaded downloading.
- ✅ **Video & Audio**: Supports downloading video and audio from hundreds of sites via `yt-dlp`.
- ✅ **Quality Selection**: Choose between 720p, 1080p, or audio-only formats.
- ✅ **Persistent History**: Keeps a record of all completed and failed downloads.
- ✅ **Modern UI**: A clean, dark-mode-first GUI with drag-and-drop support.

---

## 🏁 Getting Started (for Development)

To run the application from the source code, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/ariadownload.git
    cd ariadownload
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application:**
    ```bash
    python main.py
    ```

---

## ⚙️ Usage

### Desktop GUI

Run `main.py` to launch the main graphical interface. You can drag and drop links into the window or use the input field to add new downloads.

### Web API

The FastAPI server starts automatically with the GUI. You can interact with it to start downloads from the command line or other scripts.

-   **Endpoint**: `POST /add`
-   **Body**: `{"url": "<URL_TO_DOWNLOAD>"}`

**Example using `curl`:**
```bash
curl -X POST -H "Content-Type: application/json" -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}' http://127.0.0.1:8000/add
```

### Browser Extension

The browser extension provides a simple way to send links to the downloader.

1.  Open your browser (Chrome, Firefox, etc.).
2.  Go to the extensions page (`chrome://extensions` or `about:addons`).
3.  Enable "Developer mode".
4.  Click "Load unpacked" and select the `extension` directory from this project.
5.  You can now right-click on links or use the extension icon to send downloads to the app.

---

## 🤝 Contributing

Contributions are welcome! To ensure code quality, please follow these guidelines before submitting a pull request:

1.  **Install development dependencies:**
    ```bash
    pip install ruff pytest
    ```

2.  **Run the linter and formatter:**
    Before committing, run `ruff` to check for issues and format the code.
    ```bash
    # Check for linting errors
    ruff check .
    # Format the code
    ruff format .
    ```

3.  **Run the test suite:**
    Make sure all existing tests pass.
    ```bash
    pytest
    ```