from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_LOGGER_INITIALIZED = False


def setup_logging(*, log_level: str = "INFO", logs_dir: Path = Path("logs"), log_file: str = "app.log") -> None:
    """
    Configure logging for AtlasKernel.

    - Console + rotating file log
    - Idempotent: safe to call multiple times across API/CLI/tests
    """
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED:
        return

    logs_dir.mkdir(parents=True, exist_ok=True)
    file_path = logs_dir / log_file

    level = getattr(logging, log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        filename=str(file_path),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    _LOGGER_INITIALIZED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger. Ensure setup_logging() is called early in main.py / cli.py.
    """
    return logging.getLogger(name if name else "AtlasKernel")
