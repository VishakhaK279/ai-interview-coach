"""Configure console and rotating file logging for the application."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 3
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(
    log_file: Path,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> None:
    """Add an idempotent rotating log file handler to the root logger."""
    if max_bytes <= 0:
        raise ValueError("max_bytes must be greater than zero.")
    if backup_count < 0:
        raise ValueError("backup_count cannot be negative.")

    resolved_log_file = log_file.resolve()
    resolved_log_file.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    for handler in root_logger.handlers:
        if isinstance(handler, RotatingFileHandler) and (
            Path(handler.baseFilename).resolve() == resolved_log_file
        ):
            return

    file_handler = RotatingFileHandler(
        resolved_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(file_handler)

