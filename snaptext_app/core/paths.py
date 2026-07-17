from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "SnapText"


def get_app_data_dir() -> Path:
    """Return a writable platform-specific application data directory."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_screenshots_dir() -> Path:
    """Return the default screenshot directory."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            CSIDL_MYPICTURES = 39
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_MYPICTURES, None, 0, buf)
            base = Path(buf.value) if buf.value else Path.home() / "Pictures"
        except Exception:
            base = Path.home() / "Pictures"
    else:
        base = Path.home() / "Pictures"
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_path() -> Path:
    return get_app_data_dir() / "config.json"


def get_history_path() -> Path:
    return get_app_data_dir() / "history.json"


def get_log_path() -> Path:
    return get_app_data_dir() / "app.log"


def resource_path(relative_path: str) -> Path:
    """Resolve resources both from source and from a PyInstaller bundle."""
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base_path = Path(__file__).resolve().parents[2]
    return base_path / relative_path
