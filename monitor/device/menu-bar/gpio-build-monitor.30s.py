#!/usr/bin/env python3
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.refreshOnOpen>true</swiftbar.refreshOnOpen>
"""SwiftBar plugin: CI status in the Mac menu bar.

Install SwiftBar, then symlink this file into its plugins folder (keep
``menu_bar.py`` next to it). See docs/macos.md.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from menu_bar import (  # noqa: E402
    DEFAULT_DASHBOARD,
    DEFAULT_STATUS_URL,
    last_valid_payload,
    plugin_output,
    snapshot_headers,
)

TIMEOUT_SECONDS = 10
CACHE_PATH = Path.home() / "Library/Caches/gpio-build-monitor/status.json"


def _read_cache(path: Path) -> dict | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _write_cache(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _error_output(message: str) -> str:
    dashboard = os.environ.get("GPIO_MONITOR_DASHBOARD_URL", DEFAULT_DASHBOARD)
    lines = plugin_output(
        {
            "status": "CONNECTION_ERROR",
            "is_running": False,
            "fetching": False,
            "builds": [],
        },
        dashboard_url=dashboard,
    ).splitlines()
    lines.insert(2, f"{message} | color=purple")
    return "\n".join(lines) + "\n"


def main() -> None:
    status_url = os.environ.get("GPIO_MONITOR_STATUS_URL", DEFAULT_STATUS_URL)
    dashboard_url = os.environ.get("GPIO_MONITOR_DASHBOARD_URL", DEFAULT_DASHBOARD)
    cached = _read_cache(CACHE_PATH)
    request = urllib.request.Request(status_url, headers=snapshot_headers())
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        if cached:
            sys.stdout.write(plugin_output(cached, dashboard_url=dashboard_url))
            return
        sys.stdout.write(_error_output(str(exc)))
        return
    if not isinstance(payload, dict):
        if cached:
            sys.stdout.write(plugin_output(cached, dashboard_url=dashboard_url))
            return
        sys.stdout.write(_error_output("Unexpected status payload"))
        return
    payload = last_valid_payload(cached, payload)
    if payload.get("builds"):
        _write_cache(CACHE_PATH, payload)
    sys.stdout.write(plugin_output(payload, dashboard_url=dashboard_url))


if __name__ == "__main__":
    main()
