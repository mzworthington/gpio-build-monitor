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

from menu_bar import DEFAULT_DASHBOARD, DEFAULT_STATUS_URL, plugin_output  # noqa: E402

TIMEOUT_SECONDS = 10


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
    request = urllib.request.Request(status_url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        sys.stdout.write(_error_output(str(exc)))
        return
    if not isinstance(payload, dict):
        sys.stdout.write(_error_output("Unexpected status payload"))
        return
    sys.stdout.write(plugin_output(payload, dashboard_url=dashboard_url))


if __name__ == "__main__":
    main()
