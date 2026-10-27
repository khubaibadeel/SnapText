from __future__ import annotations

from collections.abc import Callable
import sys

import keyboard

from .logger import logger


class ShortcutManager:
    def __init__(self):
        self._handles: list[object] = []

    def clear(self) -> None:
        for handle in self._handles:
            try:
                keyboard.remove_hotkey(handle)
            except Exception:
                pass
        self._handles.clear()

    def register(self, hotkey: str, callback: Callable[[], None]) -> tuple[bool, str]:
        if not hotkey.strip():
            return False, "Shortcut cannot be empty."
        try:
            handle = keyboard.add_hotkey(hotkey, callback, suppress=False)
            self._handles.append(handle)
            return True, ""
        except Exception as exc:
            logger.warning("Could not register shortcut %s: %s", hotkey, exc)
            return False, str(exc)

    def register_defaults(self, app) -> list[str]:
        self.clear()
        if sys.platform != "win32":
            return []
        failures: list[str] = []
        mappings = [
            (app.capture_hotkey, lambda: app.after(0, app.start_snipping)),
            (app.copy_latest_hotkey, lambda: app.after(0, app.copy_latest_text)),
        ]
        for hotkey, callback in mappings:
            ok, error = self.register(hotkey, callback)
            if not ok:
                failures.append(f"{hotkey}: {error}")
        return failures
