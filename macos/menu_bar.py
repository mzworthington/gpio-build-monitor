"""Map monitor status JSON onto a SwiftBar menu extra."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

DEFAULT_DASHBOARD = "https://monitor.mzworthington.co.uk"
DEFAULT_STATUS_URL = f"{DEFAULT_DASHBOARD}/status"
SNAPSHOT_USER_AGENT = (
    "gpio-build-monitor/1.0 (+https://github.com/mzworthington/gpio-build-monitor)"
)


def snapshot_headers() -> dict[str, str]:
    # Cloudflare 403s python-urllib when Accept is set without a User-Agent.
    return {
        "Accept": "application/json",
        "User-Agent": SNAPSHOT_USER_AGENT,
    }

_BUILD_COLORS = {
    "FAIL": "red",
    "CONNECTION_ERROR": "purple",
    "RUNNING": "yellow",
    "WAITING": "yellow",
    "APPROVAL": "yellow",
    "PASS": "green",
    "UNKNOWN": "red",
}


def title_for(payload: Mapping[str, Any]) -> tuple[str, str]:
    """Return (label, SwiftBar color) using the same priority as the desk LEDs."""
    status = str(payload.get("status") or "NONE")
    is_running = bool(payload.get("is_running"))
    fetching = bool(payload.get("fetching"))

    if status == "CONNECTION_ERROR":
        return "ERR", "purple"
    if status == "FAIL" or status == "UNKNOWN":
        return ("FAIL" if status == "FAIL" else "UNK"), "red"
    if is_running:
        return "RUN", "yellow"
    if status == "APPROVAL":
        return "WAIT", "yellow"
    if status == "PASS":
        return "PASS", "green"
    if fetching:
        return "…", "blue"
    return "IDLE", "gray"


def _build_line(build: Mapping[str, Any]) -> str:
    repo = str(build.get("repo") or "?")
    workflow = str(build.get("workflow") or "?")
    status = str(build.get("status") or "?")
    url = str(build.get("url") or "")
    color = _BUILD_COLORS.get(status, "gray")
    href = f" href={url}" if url else ""
    return f"{repo} {workflow} {status} |{href} color={color}"


def plugin_output(
    payload: Mapping[str, Any],
    *,
    dashboard_url: str = DEFAULT_DASHBOARD,
) -> str:
    label, color = title_for(payload)
    lines = [f"{label} | color={color}", "---"]
    builds: Sequence[Any] = payload.get("builds") or []
    if builds:
        for build in builds:
            if isinstance(build, Mapping):
                lines.append(_build_line(build))
        lines.append("---")
    else:
        lines.append("No builds yet")
        lines.append("---")
    lines.append(f"Open monitor | href={dashboard_url}")
    lines.append("Refresh | refresh=true")
    return "\n".join(lines) + "\n"
