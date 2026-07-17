from __future__ import annotations

import datetime as dt
from pathlib import Path

from PIL import Image

from .config import config
from .logger import logger


def save_screenshot(img: Image.Image) -> Path:
    """Save a screenshot using a collision-resistant timestamped filename."""
    save_dir = Path(config.get("save_directory")).expanduser()
    save_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")[:-3]
    filepath = save_dir / f"SnapText_{timestamp}.png"
    try:
        img.save(filepath, "PNG", optimize=True)
        logger.info("Screenshot saved to %s", filepath)
        return filepath
    except Exception as exc:
        logger.error("Failed to save screenshot: %s", exc)
        raise RuntimeError(f"Could not save screenshot: {exc}") from exc
