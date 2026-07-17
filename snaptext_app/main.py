from __future__ import annotations

from .core.config import config
from .core.logger import logger, set_debug_logging
from .core.system import SingleInstance, enable_dpi_awareness
from .ui.main_window import MainWindow


def run():
    enable_dpi_awareness()
    set_debug_logging(config.get("debug_mode", False))
    instance = SingleInstance()
    if instance.already_running:
        logger.warning("SnapText is already running")
        instance.close()
        return

    logger.info("Starting SnapText")
    app = None
    try:
        app = MainWindow()
        app.mainloop()
    except KeyboardInterrupt:
        logger.info("SnapText stopped by user")
    except Exception:
        logger.exception("SnapText terminated unexpectedly")
        raise
    finally:
        if app:
            try:
                app.shortcuts.clear()
                app.tray.stop()
            except Exception:
                pass
        instance.close()


if __name__ == "__main__":
    run()
