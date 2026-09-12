#!/usr/bin/env python3

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_make_test_fails_when_hub_coverage_drops_below_floor():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "--cov=monitor" in makefile
    assert "--cov-fail-under=84" in makefile
    assert "--cov-omit=monitor/__main__.py" in makefile or "omit" in (
        ROOT / "pyproject.toml"
    ).read_text(encoding="utf-8")
