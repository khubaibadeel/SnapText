from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .logger import logger
from .paths import get_log_path

APP_NAME = "SnapText"
STARTUP_VALUE_NAME = "SnapText"


def enable_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        # Per-monitor V2 where supported.
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception as exc:
        logger.debug("Could not enable DPI awareness: %s", exc)


def open_path(path: str | Path) -> bool:
    target = Path(path)
    if not target.exists():
        return False
    try:
        if sys.platform == "win32":
            os.startfile(str(target))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
        return True
    except Exception as exc:
        logger.error("Failed to open %s: %s", target, exc)
        return False


def startup_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    root = Path(__file__).resolve().parents[2]
    return f'"{sys.executable}" "{root / "run.py"}"'


def set_launch_at_startup(enabled: bool) -> tuple[bool, str]:
    if sys.platform != "win32":
        return False, "Launch at startup is currently supported on Windows only."
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(key, STARTUP_VALUE_NAME, 0, winreg.REG_SZ, startup_command())
            else:
                try:
                    winreg.DeleteValue(key, STARTUP_VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True, "Startup setting updated."
    except Exception as exc:
        logger.error("Could not update startup setting: %s", exc)
        return False, str(exc)


def open_logs_folder() -> bool:
    return open_path(get_log_path().parent)


class SingleInstance:
    """Best-effort single-instance guard; uses a named mutex on Windows."""

    def __init__(self, name: str = "Local\\SnapTextSingleInstance"):
        self.handle = None
        self.already_running = False
        if sys.platform != "win32":
            return
        try:
            import ctypes

            self.handle = ctypes.windll.kernel32.CreateMutexW(None, False, name)
            self.already_running = ctypes.windll.kernel32.GetLastError() == 183
        except Exception as exc:
            logger.debug("Single-instance guard unavailable: %s", exc)

    def close(self) -> None:
        if self.handle and sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.kernel32.CloseHandle(self.handle)
            except Exception:
                pass
