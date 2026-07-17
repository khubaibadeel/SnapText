from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .paths import get_log_path


def setup_logger(debug: bool = False) -> logging.Logger:
    logger = logging.getLogger("SnapText")
    logger.propagate = False
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler = RotatingFileHandler(
        get_log_path(), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def set_debug_logging(enabled: bool) -> None:
    logger.setLevel(logging.DEBUG if enabled else logging.INFO)


logger = setup_logger()
