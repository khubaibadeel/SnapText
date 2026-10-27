from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

from .logger import logger
from .paths import get_config_path, get_screenshots_dir

DEFAULT_CONFIG = {
    "appearance_mode": "system",
    "auto_copy_text": True,
    "auto_save_screenshot": True,
    "close_preview_after_copy": False,
    "save_directory": str(get_screenshots_dir()),
    "ocr_language": "eng",
    "ocr_mode": "balanced",
    "tesseract_path": "",
    "show_notifications": True,
    "minimize_to_tray": True,
    "launch_at_startup": False,
    "capture_hotkey": "ctrl+shift+s",
    "copy_latest_hotkey": "ctrl+shift+c",
    "debug_mode": False,
    "remember_window_position": True,
    "window_geometry": "720x610",
    "first_run_complete": False,
    "max_history_entries": 250,
}

_BOOLEAN_KEYS = {
    "auto_copy_text",
    "auto_save_screenshot",
    "close_preview_after_copy",
    "show_notifications",
    "minimize_to_tray",
    "launch_at_startup",
    "debug_mode",
    "remember_window_position",
    "first_run_complete",
}
_VALID_APPEARANCE = {"light", "dark", "system"}
_VALID_OCR_MODES = {"fast", "balanced", "accurate"}
_VALID_OCR_LANGUAGES = {"eng", "urd", "eng+urd"}
_GEOMETRY_RE = re.compile(r"^\d{3,5}x\d{3,5}([+-]\d{1,6}[+-]\d{1,6})?$")


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return default


def _coerce_nonempty_string(value: Any, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _sanitize_settings(values: dict[str, Any]) -> dict[str, Any]:
    sanitized = DEFAULT_CONFIG.copy()

    for key in _BOOLEAN_KEYS:
        sanitized[key] = _coerce_bool(values.get(key, sanitized[key]), sanitized[key])

    save_directory = values.get("save_directory", sanitized["save_directory"])
    sanitized["save_directory"] = _coerce_nonempty_string(save_directory, DEFAULT_CONFIG["save_directory"])

    for key in ("capture_hotkey", "copy_latest_hotkey"):
        sanitized[key] = _coerce_nonempty_string(values.get(key, sanitized[key]), DEFAULT_CONFIG[key]).lower()

    appearance = str(values.get("appearance_mode", sanitized["appearance_mode"])).lower()
    sanitized["appearance_mode"] = appearance if appearance in _VALID_APPEARANCE else DEFAULT_CONFIG["appearance_mode"]

    ocr_mode = str(values.get("ocr_mode", sanitized["ocr_mode"])).lower()
    sanitized["ocr_mode"] = ocr_mode if ocr_mode in _VALID_OCR_MODES else DEFAULT_CONFIG["ocr_mode"]

    ocr_language = str(values.get("ocr_language", sanitized["ocr_language"])).lower()
    sanitized["ocr_language"] = ocr_language if ocr_language in _VALID_OCR_LANGUAGES else DEFAULT_CONFIG["ocr_language"]

    tesseract_path = str(values.get("tesseract_path", "") or "").strip()
    sanitized["tesseract_path"] = tesseract_path if tesseract_path and Path(tesseract_path).exists() else ""

    geometry = str(values.get("window_geometry", sanitized["window_geometry"]) or "")
    sanitized["window_geometry"] = geometry if _GEOMETRY_RE.fullmatch(geometry) else DEFAULT_CONFIG["window_geometry"]

    try:
        max_history_entries = int(values.get("max_history_entries", sanitized["max_history_entries"]))
    except (TypeError, ValueError):
        max_history_entries = DEFAULT_CONFIG["max_history_entries"]
    sanitized["max_history_entries"] = min(5000, max(10, max_history_entries))

    return sanitized


class Config:
    def __init__(self):
        self.path: Path = get_config_path()
        self.settings: dict[str, Any] = DEFAULT_CONFIG.copy()
        self._lock = threading.RLock()
        self.load()

    def load(self) -> None:
        with self._lock:
            if not self.path.exists():
                self.save()
                return
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(loaded, dict):
                    raise ValueError("Configuration root must be an object")
                self.settings = _sanitize_settings(loaded)
                if loaded != self.settings:
                    self.save()
            except Exception as exc:
                logger.error("Failed to load config: %s. Using defaults.", exc)
                self.settings = DEFAULT_CONFIG.copy()
                self.save()

    def save(self) -> None:
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temp_path = self.path.with_suffix(".tmp")
                temp_path.write_text(
                    json.dumps(self.settings, indent=4, ensure_ascii=False),
                    encoding="utf-8",
                )
                temp_path.replace(self.path)
            except Exception as exc:
                logger.error("Failed to save config: %s", exc)

    def get(self, key: str, default=None):
        with self._lock:
            return self.settings.get(key, default)

    def set(self, key: str, value) -> None:
        self.set_many({key: value})

    def set_many(self, values: dict[str, Any]) -> None:
        with self._lock:
            merged = self.settings.copy()
            merged.update(values)
            self.settings = _sanitize_settings(merged)
            self.save()

    def reset(self) -> None:
        with self._lock:
            self.settings = DEFAULT_CONFIG.copy()
            self.save()


config = Config()
