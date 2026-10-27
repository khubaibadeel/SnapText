from __future__ import annotations

import sys
import threading

from PIL import Image

from .logger import logger
from .paths import resource_path


class TrayController:
    def __init__(self, app):
        self.app = app
        self.icon = None
        self.thread = None

    @property
    def available(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            import pystray  # noqa: F401

            return True
        except Exception:
            return False

    def start(self) -> None:
        if self.icon is not None or not self.available:
            return
        try:
            import pystray

            image_path = resource_path("assets/icon.png")
            image = Image.open(image_path).convert("RGBA")
            menu = pystray.Menu(
                pystray.MenuItem("New Capture", self._capture, default=True),
                pystray.MenuItem("Show SnapText", self._show),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("History", self._history),
                pystray.MenuItem("Settings", self._settings),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", self._exit),
            )
            self.icon = pystray.Icon("SnapText", image, "SnapText", menu)
            self.thread = threading.Thread(target=self.icon.run, daemon=True)
            self.thread.start()
        except Exception as exc:
            logger.warning("System tray could not start: %s", exc)
            self.icon = None

    def stop(self) -> None:
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
        self.icon = None

    def _schedule(self, callback) -> None:
        self.app.after(0, callback)

    def _capture(self, *_):
        self._schedule(self.app.start_snipping)

    def _show(self, *_):
        self._schedule(self.app.show_main_window)

    def _history(self, *_):
        self._schedule(self.app.show_history)

    def _settings(self, *_):
        self._schedule(self.app.show_settings)

    def _exit(self, *_):
        self._schedule(self.app.exit_application)
