from __future__ import annotations

from .config import config
from .logger import logger


def notify(title: str, message: str) -> None:
    if not config.get("show_notifications", True):
        return
    try:
        from plyer import notification

        notification.notify(
            title=title,
            message=message,
            app_name="SnapText",
            timeout=3,
        )
    except Exception as exc:
        logger.debug("Notification unavailable: %s", exc)
