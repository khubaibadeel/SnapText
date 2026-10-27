"""Generate README screenshots from the real SnapText UI.

Run from the project root on Windows, or on Linux with:
    xvfb-run -a python scripts/capture_screenshots.py
"""

from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
import time
import sys
from pathlib import Path

# Isolate screenshot-generation data from the user's actual SnapText data.
DEMO_DATA = Path(tempfile.mkdtemp(prefix="snaptext-screenshots-"))
os.environ["XDG_DATA_HOME"] = str(DEMO_DATA)

from PIL import Image, ImageDraw, ImageGrab, ImageFont  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "docs" / "screenshots"
OUTPUT.mkdir(parents=True, exist_ok=True)


def create_demo_capture() -> Path:
    image = Image.new("RGB", (900, 320), "white")
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
        body_font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except OSError:
        title_font = body_font = ImageFont.load_default()
    draw.rounded_rectangle((28, 28, 872, 292), radius=24, fill="#F8FAFC", outline="#DDE4EE", width=3)
    draw.text((70, 72), "Quarterly Project Update", font=title_font, fill="#0F172A")
    draw.text((70, 138), "The new capture workflow reduced manual entry time by 42%.", font=body_font, fill="#334155")
    draw.text((70, 184), "Next milestone: production rollout on 28 July 2026.", font=body_font, fill="#334155")
    draw.text((70, 230), "Owner: Application Development Team", font=body_font, fill="#334155")
    path = DEMO_DATA / "demo-capture.png"
    image.save(path)
    return path


def seed_data(capture_path: Path) -> None:
    app_dir = DEMO_DATA / "SnapText"
    app_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "appearance_mode": "light",
        "auto_copy_text": True,
        "auto_save_screenshot": True,
        "close_preview_after_copy": False,
        "save_directory": str(DEMO_DATA / "Screenshots"),
        "ocr_language": "eng",
        "ocr_mode": "balanced",
        "tesseract_path": "",
        "show_notifications": False,
        "minimize_to_tray": False,
        "launch_at_startup": False,
        "capture_hotkey": "ctrl+shift+s",
        "copy_latest_hotkey": "ctrl+shift+c",
        "debug_mode": False,
        "remember_window_position": False,
        "window_geometry": "720x610",
        "first_run_complete": True,
        "max_history_entries": 250,
    }
    (app_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    now = dt.datetime.now()
    entries = [
        {
            "id": "demo-1",
            "timestamp": now.isoformat(timespec="seconds"),
            "screenshot_path": str(capture_path),
            "text": "Quarterly Project Update\nThe new capture workflow reduced manual entry time by 42%.\nNext milestone: production rollout on 28 July 2026.\nOwner: Application Development Team",
            "source": "screen",
        },
        {
            "id": "demo-2",
            "timestamp": (now - dt.timedelta(hours=3)).isoformat(timespec="seconds"),
            "screenshot_path": str(capture_path),
            "text": "Customer reference: ST-2026-0717\nStatus: Approved for release",
            "source": "clipboard",
        },
    ]
    (app_dir / "history.json").write_text(json.dumps(entries, indent=2), encoding="utf-8")


def settle(window, cycles: int = 5) -> None:
    for _ in range(cycles):
        window.update_idletasks()
        window.update()
        time.sleep(0.08)


def capture_window(window, filename: str) -> None:
    settle(window)
    x = window.winfo_rootx()
    y = window.winfo_rooty()
    width = window.winfo_width()
    height = window.winfo_height()
    image = ImageGrab.grab(bbox=(x, y, x + width, y + height))
    image.save(OUTPUT / filename, optimize=True)


def main() -> None:
    capture_path = create_demo_capture()
    seed_data(capture_path)

    # Documentation screenshots must represent the supported Windows release,
    # even when generated in Linux CI under Xvfb. Replace only the status probe;
    # every visible window is still rendered by the real application classes.
    from snaptext_app.core.ocr import OCRStatus
    from snaptext_app.ui import main_window as main_window_module
    from snaptext_app.ui import settings_window as settings_window_module
    from snaptext_app.ui.preview_window import PreviewWindow
    from snaptext_app.ui.theme import apply_theme

    demo_ocr_status = OCRStatus(
        True,
        engine="windows",
        version="Windows built-in OCR",
        languages=("eng",),
        message="Windows OCR ready",
    )
    main_window_module.configure_detected_ocr = lambda language_profile=None: demo_ocr_status
    settings_window_module.configure_detected_ocr = lambda language_profile=None: demo_ocr_status
    settings_window_module.available_language_options = lambda: {"English": "eng"}
    MainWindow = main_window_module.MainWindow

    app = MainWindow()

    def step_main():
        capture_window(app, "main-window.png")
        apply_theme("dark")
        app.after(350, step_dark)

    def step_dark():
        capture_window(app, "main-window-dark.png")
        apply_theme("light")
        app.after(350, step_history)

    def step_history():
        app.show_history()
        app.after(350, capture_history)

    def capture_history():
        history_window = app._history_window
        capture_window(history_window, "history-window.png")
        history_window.destroy()
        app.after(250, step_settings)

    def step_settings():
        app.show_settings()
        app.after(500, capture_settings)

    def capture_settings():
        settings_window = app._settings_window
        capture_window(settings_window, "settings-window.png")
        settings_window.destroy()
        app.after(250, step_preview)

    def step_preview():
        demo_image = Image.open(capture_path).convert("RGB")
        preview = PreviewWindow(
            app,
            demo_image,
            "Quarterly Project Update\nThe new capture workflow reduced manual entry time by 42%.\nNext milestone: production rollout on 28 July 2026.\nOwner: Application Development Team",
            capture_path,
            "demo-1",
        )
        app._demo_preview = preview
        app.after(350, capture_preview)

    def capture_preview():
        preview = app._demo_preview
        capture_window(preview, "preview-window.png")
        preview.destroy()
        print(f"Saved screenshots to {OUTPUT}")
        app.after(100, app.exit_application)

    app.after(900, step_main)
    app.mainloop()


if __name__ == "__main__":
    main()
