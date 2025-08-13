import unittest
from downloader_core import YtDlpParser, DownloadItem

class Dummy:
    def __init__(self):
        self.events = []
    def send(self, event_type, **kwargs):
        self.events.append((event_type, kwargs))

class TestParsers(unittest.TestCase):
    def setUp(self):
        self.item = DownloadItem(url="http://example.com/video")
        self.dummy = Dummy()

    def test_ytdlp_progress(self):
        line = "[download] 35.2% of 5.73MiB at 1.37MiB/s ETA 00:15"
        YtDlpParser.parse_line(line, self.item, self.dummy.send)
        ev = next((e for e in self.dummy.events if e[0]=="progress"), None)
        self.assertIsNotNone(ev)
        self.assertIn('percent', ev[1])
        self.assertAlmostEqual(ev[1]['percent'], 35.2, places=1)
        self.assertEqual(ev[1]['size'], '5.73MiB')

    def test_aria2c_progress(self):
        self.dummy.events.clear()
        line = "[#2e5c86 48KiB/5.7MiB(0%) CN:5 DL:153KiB ETA:37s]"
        YtDlpParser.parse_line(line, self.item, self.dummy.send)
        ev = next((e for e in self.dummy.events if e[0]=="progress"), None)
        self.assertIsNotNone(ev)
        self.assertEqual(ev[1]['size'], '5.7MiB')
        self.assertEqual(ev[1]['downloaded'], '48KiB')
        self.assertEqual(ev[1]['eta'], '37s')

    def test_merge_message(self):
        self.dummy.events.clear()
        line = "[Merger] Merging formats into \"Some Title [ID].mp4\""
        YtDlpParser.parse_line(line, self.item, self.dummy.send)
        ev = next((e for e in self.dummy.events if e[0]=="status"), None)
        self.assertIsNotNone(ev)
        self.assertIn("Merge complete", ev[1]['text'])

if __name__ == '__main__':
    unittest.main()


