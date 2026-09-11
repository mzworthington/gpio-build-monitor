#!/usr/bin/env python3

import logging
from pathlib import Path

from monitor.log_handler import default_log_dir, setup_logger


def test_default_log_dir_uses_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MONITOR_LOG_DIR", str(tmp_path / "from-env"))
    assert default_log_dir() == tmp_path / "from-env"


def test_default_log_dir_falls_back_to_logs(monkeypatch):
    monkeypatch.delenv("MONITOR_LOG_DIR", raising=False)
    assert default_log_dir() == Path("logs")


def test_setup_logger_writes_rotating_file_and_stdout(tmp_path, capsys):
    logger = setup_logger(logging.INFO, tmp_path)
    logger.info("hub-wired")
    for handler in logger.handlers:
        handler.flush()

    log_text = (tmp_path / "monitor.log").read_text(encoding="utf-8")
    assert "hub-wired" in log_text
    assert "hub-wired" in capsys.readouterr().out
    assert logger.level == logging.INFO
    assert len(logger.handlers) == 2


def test_setup_logger_creates_missing_directory(tmp_path):
    log_dir = tmp_path / "nested" / "logs"
    setup_logger(logging.WARNING, log_dir)
    assert log_dir.is_dir()
    assert (log_dir / "monitor.log").is_file()


def test_setup_logger_defaults_when_log_dir_omitted(tmp_path, monkeypatch):
    monkeypatch.setenv("MONITOR_LOG_DIR", str(tmp_path / "defaulted"))
    setup_logger(logging.DEBUG)
    assert (tmp_path / "defaulted" / "monitor.log").is_file()


def test_setup_logger_replaces_existing_handlers(tmp_path):
    root = logging.getLogger()
    root.addHandler(logging.NullHandler())
    setup_logger(logging.ERROR, tmp_path)
    kinds = {type(handler).__name__ for handler in logging.getLogger().handlers}
    assert kinds == {"RotatingFileHandler", "StreamHandler"}
