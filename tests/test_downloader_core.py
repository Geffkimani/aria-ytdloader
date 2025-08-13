from queue import Queue
from unittest.mock import patch, MagicMock
from downloader_core import DownloaderCore, DownloadItem, YtDlpParser

class TestDownloaderCore:
    def setup_method(self):
        self.event_queue = Queue()
        self.core = DownloaderCore(
            event_queue=self.event_queue,
            download_dir="/tmp/downloads",
            concurrent_workers=1
        )

    def test_enqueue_and_get_urls(self):
        item = DownloadItem(url="https://example.com/video")
        self.core.enqueue(item, start_workers=False)
        urls = self.core.get_queued_urls()
        assert "https://example.com/video" in urls

    def test_build_command_video(self):
        item = DownloadItem(url="https://example.com/video", quality="720p")
        cmd = self.core._build_command(item)
        assert any("720" in c for c in cmd)
        assert cmd[0].endswith("yt-dlp")

    def test_build_command_audio_only(self):
        item = DownloadItem(url="https://example.com/audio", audio_only=True)
        cmd = self.core._build_command(item)
        assert "-x" in cmd
        assert "--audio-format" in cmd
        assert "mp3" in cmd

    @patch("downloader_core.YtDlpParser.parse_line")
    def test_progress_parsing(self, mock_parse_line):
        item = DownloadItem(url="https://example.com/video")
        test_line = "[download]   23.4% of 5.00MiB at 1.23MiB/s ETA 00:20"
        YtDlpParser.parse_line(test_line, item, self.core._send_event)
        mock_parse_line.assert_called_with(test_line, item, self.core._send_event)

    @patch("downloader_core.DownloadProcess")
    def test_run_subprocess_success(self, mock_download_process):
        mock_process_instance = MagicMock()
        mock_process_instance.run.return_value = []
        mock_download_process.return_value = mock_process_instance

        item = DownloadItem(url="https://example.com/video")
        self.core._process_item(item)

        mock_download_process.assert_called_once()
        mock_process_instance.run.assert_called_once()
