import pytest
from utils import is_valid_url, is_safe_url

class TestURLValidation:
    def test_valid_urls(self):
        assert is_valid_url("https://youtube.com/watch?v=test")
        assert is_valid_url("http://example.com")
        assert is_valid_url("https://www.google.com/search?q=test")
        assert is_valid_url("www.example.com")
    
    def test_invalid_urls(self):
        assert not is_valid_url("not-a-url")
        assert not is_valid_url("file:///etc/passwd")
        assert not is_valid_url("ftp://example.com")
    
    def test_safe_url_private_ips(self):
        assert not is_safe_url("http://192.168.1.1/")
        assert not is_safe_url("http://10.0.0.1/")
        assert not is_safe_url("http://172.16.0.1/")
        assert not is_safe_url("http://localhost/")
        assert not is_safe_url("http://127.0.0.1/")
        assert not is_safe_url("http://[::1]/")

    def test_safe_url_public_ips_and_domains(self):
        assert is_safe_url("https://8.8.8.8/")
        assert is_safe_url("https://www.google.com/")
        assert is_safe_url("http://example.org/")

    def test_safe_url_unsupported_schemes(self):
        assert not is_safe_url("ftp://example.com/")
        assert not is_safe_url("file:///etc/passwd")

