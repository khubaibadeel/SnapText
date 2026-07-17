from __future__ import annotations

import pyperclip

from .logger import logger


def copy_to_clipboard(text: str) -> bool:
    """Copy text to the system clipboard.

    Clipboard support is environment-dependent. A failure should not be treated as
    an OCR/capture failure because the recognized text is still valid and should
    remain visible in the preview/history.
    """
    try:
        pyperclip.copy(text)
        logger.debug("Text copied to clipboard")
        return True
    except Exception as exc:
        logger.warning("Failed to copy text to clipboard: %s", exc)
        return False
