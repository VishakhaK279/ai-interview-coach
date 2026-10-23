import logging
from logging.handlers import RotatingFileHandler

from app.logging_config import configure_logging


def test_configure_logging_writes_and_rotates_log_file(tmp_path) -> None:
    log_file = tmp_path / "logs" / "app.log"
    logger = logging.getLogger("test.rotating_file")
    logger.setLevel(logging.INFO)
    logger.propagate = True

    configure_logging(log_file, max_bytes=80, backup_count=1)
    configured_handlers = [
        handler
        for handler in logging.getLogger().handlers
        if isinstance(handler, RotatingFileHandler)
        and handler.baseFilename == str(log_file.resolve())
    ]
    assert len(configured_handlers) == 1

    configure_logging(log_file, max_bytes=80, backup_count=1)
    configured_handlers_after_repeat = [
        handler
        for handler in logging.getLogger().handlers
        if isinstance(handler, RotatingFileHandler)
        and handler.baseFilename == str(log_file.resolve())
    ]
    assert len(configured_handlers_after_repeat) == 1

    logger.info("first diagnostic record")
    logger.info("second diagnostic record which triggers rotation")

    assert log_file.exists()
    assert log_file.with_name("app.log.1").exists()
    assert "second diagnostic record" in log_file.read_text(encoding="utf-8")
    assert "first diagnostic record" in log_file.with_name(
        "app.log.1"
    ).read_text(encoding="utf-8")

    for handler in configured_handlers:
        logging.getLogger().removeHandler(handler)
        handler.close()
