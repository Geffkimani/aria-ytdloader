"""
Refactored utilities:
- Robust binary detection (assets, PATH, env override)
- Hardened URL validation and safety checks
- check_dependencies returns True/False and logs actionable instructions
- notify with fallback
- improved log_error
"""
import logging
import os
import re
import sys
import shutil
import traceback
from urllib.parse import urlparse
from ipaddress import ip_address, AddressValueError
from tkinter import messagebox
from plyer import notification

logger = logging.getLogger(__name__)

YT_DLP_NAME = f"yt-dlp{'.exe' if sys.platform == 'win32' else ''}"
ARIA2C_NAME = f"aria2c{'.exe' if sys.platform == 'win32' else ''}"
ASSETS_DIR = os.path.abspath(os.environ.get("ASSETS_DIR", "./assets"))

def find_binary(binary_name: str, asset_dir: str = ASSETS_DIR) -> str:
    # 1) env override
    env_path = os.environ.get(binary_name.upper() + "_PATH")
    if env_path and os.path.isfile(env_path) and os.access(env_path, os.X_OK):
        return os.path.abspath(env_path)

    # 2) assets dir
    asset_path = os.path.join(asset_dir, binary_name)
    if os.path.isfile(asset_path) and os.access(asset_path, os.X_OK):
        return os.path.abspath(asset_path)

    # 3) PATH
    path_bin = shutil.which(binary_name)
    if path_bin:
        return os.path.abspath(path_bin)

    return ""

# Expose as globals to keep compatibility
YT_DLP_PATH = find_binary(YT_DLP_NAME)
ARIA2C_PATH = find_binary(ARIA2C_NAME)

# URL validation: permissive but safe for typical video hosts
_VALID_URL_RE = re.compile(
    r"""^(https?://)"""  # scheme required
    r"([A-Za-z0-9.-]+)"  # host
    r"(:[0-9]+)?"  # optional port
    r"(/[A-Za-z0-9_.~:/?#\[\]@!$&'()*+,;=-]*)?"""  # optional path
)

def is_valid_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not url:
        return False
    # require scheme for clarity
    if not url.lower().startswith(("http://", "https://")):
        return False
    return _VALID_URL_RE.match(url) is not None

def is_safe_url(url: str) -> bool:
    """Reject non-http(s), localhost, and private IP addresses."""
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https"):
            return False
        host = parsed.hostname
        if not host:
            return False
        # explicit disallow localhost
        if host in ("localhost", "127.0.0.1", "::1"):
            return False
        # If host looks like an IP, check if it's public
        try:
            ip = ip_address(host)
            # reject private, loopback, reserved, multicast
            return not (ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast)
        except AddressValueError:
            # not an IP -> assume domain name; optionally whitelist hosts
            return True
    except Exception:
        logger.exception("is_safe_url error for %s", url)
        return False

def check_dependencies(gui_mode=True) -> bool:
    missing = []
    if not YT_DLP_PATH:
        missing.append(YT_DLP_NAME)
    if not ARIA2C_PATH:
        missing.append(ARIA2C_NAME)
    if missing:
        msg = "Missing required executables: " + ", ".join(missing)
        logger.error(msg)
        if gui_mode:
            try:
                messagebox.showerror("Missing Dependencies", msg + "\n\nPlace the binaries in ./assets or add to PATH, or set env vars like YT_DLP_PATH.")
            except Exception:
                logger.exception("Failed to show messagebox for missing dependencies")
        return False
    logger.info("Dependencies found: yt-dlp=%s aria2c=%s", YT_DLP_PATH, ARIA2C_PATH)
    return True

def notify(title: str, message: str):
    try:
        notification.notify(title=title, message=message, timeout=5, app_name="Aria Downloader")
    except Exception:
        # Fallback: log only (do not raise)
        logger.debug("Notification fallback: %s - %s", title, message)

def log_error(exc: Exception, context: str = "") -> str:
    tb = traceback.format_exc()
    logger.error("Error in %s: %s\n%s", context, exc, tb)
    return f"Error in {context}: {str(exc)}"

# --- Human-friendly size/rate normalization ---
_SIZE_UNIT_MULTIPLIERS = {
    'b': 1,
    'kb': 1000,
    'mb': 1000**2,
    'gb': 1000**3,
    'kib': 1024,
    'mib': 1024**2,
    'gib': 1024**3,
}

def _parse_number_unit(text: str):
    if not text:
        return None, None
    s = text.strip()
    m = re.match(r"^([\d\.]+)\s*([A-Za-z/]+)?$", s)
    if not m:
        return None, None
    num = float(m.group(1))
    unit = (m.group(2) or '').strip()
    return num, unit

def parse_size_to_bytes(text: str) -> float | None:
    num, unit = _parse_number_unit(text)
    if num is None:
        return None
    unit_key = (unit or 'B').lower()
    unit_key = unit_key.replace('i', 'i')
    # Normalize to include B suffix
    if unit_key in ('k', 'kb'):
        mult = _SIZE_UNIT_MULTIPLIERS['kb']
    elif unit_key in ('m', 'mb'):
        mult = _SIZE_UNIT_MULTIPLIERS['mb']
    elif unit_key in ('g', 'gb'):
        mult = _SIZE_UNIT_MULTIPLIERS['gb']
    elif unit_key in ('kib',):
        mult = _SIZE_UNIT_MULTIPLIERS['kib']
    elif unit_key in ('mib',):
        mult = _SIZE_UNIT_MULTIPLIERS['mib']
    elif unit_key in ('gib',):
        mult = _SIZE_UNIT_MULTIPLIERS['gib']
    elif unit_key in ('b', 'byte', 'bytes'):
        mult = 1
    else:
        # Unknown -> best effort treat as bytes
        mult = 1
    return num * mult

def format_bytes_size(num_bytes: float, binary: bool = True) -> str:
    if num_bytes is None:
        return 'N/A'
    base = 1024 if binary else 1000
    units = ['B', 'KiB', 'MiB', 'GiB'] if binary else ['B', 'KB', 'MB', 'GB']
    idx = 0
    value = float(num_bytes)
    while value >= base and idx < len(units) - 1:
        value /= base
        idx += 1
    if idx == 0:
        return f"{int(value)} {units[idx]}"
    return f"{value:.1f} {units[idx]}"

def parse_rate_to_bps(text: str) -> float | None:
    if not text:
        return None
    s = text.strip()
    s = s[:-2] if s.lower().endswith('/s') else s
    bytes_val = parse_size_to_bytes(s)
    return bytes_val

def format_bps_to_rate(bps: float, binary: bool = True) -> str:
    if bps is None:
        return 'N/A'
    return f"{format_bytes_size(bps, binary)} /s"

def normalize_size_str(text: str) -> str:
    return format_bytes_size(parse_size_to_bytes(text), binary=True)

def normalize_rate_str(text: str) -> str:
    return format_bps_to_rate(parse_rate_to_bps(text), binary=True)