import logging
import os
import sys
from logging import Logger, handlers
from pathlib import Path


def default_log_dir() -> Path:
    return Path(os.getenv("MONITOR_LOG_DIR", "logs"))


def setup_logger(level, log_dir: Path | str | None = None) -> Logger:
    directory = Path(log_dir) if log_dir is not None else default_log_dir()
    directory.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')

    file_handler = handlers.RotatingFileHandler(
        directory / "monitor.log",
        maxBytes=10_000_000,
        backupCount=3,
    )
    file_handler.setFormatter(formatter)

    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(screen_handler)
    return logger
