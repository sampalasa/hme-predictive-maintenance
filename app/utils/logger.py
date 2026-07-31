"""Centralized logging configuration.

Every module in the application should obtain its logger via
``get_logger(__name__)`` instead of configuring ``logging`` ad hoc, so that
log format and destinations stay consistent across the whole system.
"""

import logging
from pathlib import Path


_CONFIGURED = False


def _configure_root_logger(logs_dir: Path) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "application.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger, configuring handlers on first use."""

    from app.config.settings import Config

    _configure_root_logger(Config.LOGS_DIR)
    return logging.getLogger(name)
