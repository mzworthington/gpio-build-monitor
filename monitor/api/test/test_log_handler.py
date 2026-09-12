import logging

from monitor.log_handler import setup_logger


def test_setup_logger_writes_rotating_file(tmp_path):
    logger = setup_logger(logging.INFO, tmp_path)
    logger.info("coverage-check")
    for handler in logger.handlers:
        handler.flush()
    text = (tmp_path / "monitor.log").read_text(encoding="utf-8")
    assert "coverage-check" in text
