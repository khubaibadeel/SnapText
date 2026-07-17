from __future__ import annotations

import datetime as dt
import json
import threading
import uuid
from pathlib import Path
from typing import Any

from .logger import logger
from .paths import get_history_path


def _sanitize_entry(value: Any) -> tuple[dict | None, bool]:
    """Return a safe history entry and whether the original value changed."""
    if not isinstance(value, dict):
        return None, True

    changed = False
    entry = value.copy()

    entry_id = entry.get("id")
    if not isinstance(entry_id, str) or not entry_id.strip():
        entry["id"] = uuid.uuid4().hex
        changed = True

    timestamp = entry.get("timestamp")
    if not isinstance(timestamp, str):
        entry["timestamp"] = dt.datetime.now().isoformat(timespec="seconds")
        changed = True
    else:
        try:
            dt.datetime.fromisoformat(timestamp)
        except ValueError:
            entry["timestamp"] = dt.datetime.now().isoformat(timespec="seconds")
            changed = True

    screenshot_path = entry.get("screenshot_path")
    if screenshot_path is not None and not isinstance(screenshot_path, str):
        entry["screenshot_path"] = str(screenshot_path)
        changed = True

    text = entry.get("text")
    if not isinstance(text, str):
        entry["text"] = "" if text is None else str(text)
        changed = True

    source = entry.get("source")
    if not isinstance(source, str) or not source.strip():
        entry["source"] = "screen"
        changed = True

    return entry, changed or entry != value


class History:
    def __init__(self):
        self.path: Path = get_history_path()
        self.entries: list[dict] = []
        self._lock = threading.RLock()
        self.load()

    def load(self) -> None:
        with self._lock:
            if not self.path.exists():
                self.entries = []
                return
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    self.entries = []
                    self.save()
                    return

                sanitized: list[dict] = []
                changed = False
                for raw_entry in data:
                    entry, entry_changed = _sanitize_entry(raw_entry)
                    if entry is None:
                        changed = True
                        continue
                    sanitized.append(entry)
                    changed = changed or entry_changed

                self.entries = sanitized
                if changed:
                    self.save()
            except Exception as exc:
                logger.error("Failed to load history: %s", exc)
                self.entries = []

    def save(self) -> None:
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temp_path = self.path.with_suffix(".tmp")
                temp_path.write_text(
                    json.dumps(self.entries, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                temp_path.replace(self.path)
            except Exception as exc:
                logger.error("Failed to save history: %s", exc)

    def add_entry(self, screenshot_path, text: str, source: str = "screen") -> dict:
        from .config import config

        entry = {
            "id": uuid.uuid4().hex,
            "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
            "screenshot_path": str(screenshot_path) if screenshot_path else None,
            "text": text or "",
            "source": source or "screen",
        }
        with self._lock:
            self.entries.insert(0, entry)
            max_entries = config.get("max_history_entries", 250)
            try:
                max_entries = int(max_entries)
            except (TypeError, ValueError):
                max_entries = 250
            max_entries = min(5000, max(10, max_entries))
            del self.entries[max_entries:]
            self.save()
        return entry

    def update_entry(self, entry_id: str, **changes) -> bool:
        with self._lock:
            for entry in self.entries:
                if entry.get("id") == entry_id:
                    entry.update(changes)
                    sanitized, _ = _sanitize_entry(entry)
                    if sanitized is not None:
                        entry.clear()
                        entry.update(sanitized)
                    self.save()
                    return True
        return False

    def get_all(self) -> list[dict]:
        with self._lock:
            return [entry.copy() for entry in self.entries]

    def get_by_id(self, entry_id: str) -> dict | None:
        with self._lock:
            for entry in self.entries:
                if entry.get("id") == entry_id:
                    return entry.copy()
        return None

    def delete_entry(self, index_or_id) -> bool:
        with self._lock:
            if isinstance(index_or_id, int):
                if 0 <= index_or_id < len(self.entries):
                    del self.entries[index_or_id]
                    self.save()
                    return True
                return False
            for index, entry in enumerate(self.entries):
                if entry.get("id") == index_or_id:
                    del self.entries[index]
                    self.save()
                    return True
        return False

    def clear(self) -> None:
        with self._lock:
            self.entries = []
            self.save()


history = History()
