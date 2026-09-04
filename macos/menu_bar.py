"""Map monitor status JSON onto a SwiftBar menu extra."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

DEFAULT_DASHBOARD = "https://monitor.mzworthington.co.uk"
DEFAULT_STATUS_URL = f"{DEFAULT_DASHBOARD}/status"
SNAPSHOT_USER_AGENT = (
    "gpio-build-monitor/1.0 (+https://github.com/mzworthington/gpio-build-monitor)"
)

_BUILD_COLORS = {
    "FAIL": "red",
    "CONNECTION_ERROR": "purple",
    "RUNNING": "yellow",
    "WAITING": "yellow",
    "APPROVAL": "yellow",
    "PASS": "green",
    "UNKNOWN": "red",
}

_TITLE_SYMBOLS = {
    "FAIL": "xmark.octagon.fill",
    "UNK": "questionmark.diamond.fill",
    "ERR": "exclamationmark.triangle.fill",
    "RUN": "arrow.triangle.2.circlepath",
    "WAIT": "hand.raised.fill",
    "PASS": "checkmark.circle.fill",
    "…": "ellipsis.circle.fill",
    "IDLE": "circle",
}

_STATUS_SYMBOLS = {
    "FAIL": "xmark.octagon.fill",
    "CONNECTION_ERROR": "wifi.exclamationmark",
    "RUNNING": "arrow.triangle.2.circlepath",
    "WAITING": "clock.fill",
    "APPROVAL": "hand.raised.fill",
    "PASS": "checkmark.circle.fill",
    "UNKNOWN": "questionmark.diamond.fill",
}

_ATTENTION = frozenset({"FAIL", "CONNECTION_ERROR", "APPROVAL", "UNKNOWN"})
_IN_PROGRESS = frozenset({"RUNNING", "WAITING"})
_REPO_SORT = {
    "FAIL": 0,
    "UNKNOWN": 1,
    "CONNECTION_ERROR": 2,
    "APPROVAL": 3,
    "RUNNING": 4,
    "WAITING": 5,
    "PASS": 6,
    "NONE": 7,
}


def snapshot_headers() -> dict[str, str]:
    # Cloudflare 403s python-urllib when Accept is set without a User-Agent.
    return {
        "Accept": "application/json",
        "User-Agent": SNAPSHOT_USER_AGENT,
    }


def title_for(payload: Mapping[str, Any]) -> tuple[str, str, str]:
    """Return (label, SwiftBar color, SF Symbol) using the same priority as the desk LEDs."""
    status = str(payload.get("status") or "NONE")
    is_running = bool(payload.get("is_running"))
    fetching = bool(payload.get("fetching"))

    if status == "CONNECTION_ERROR":
        label, color = "ERR", "purple"
    elif status == "FAIL" or status == "UNKNOWN":
        label, color = ("FAIL" if status == "FAIL" else "UNK"), "red"
    elif is_running:
        label, color = "RUN", "yellow"
    elif status == "APPROVAL":
        label, color = "WAIT", "yellow"
    elif status == "PASS":
        label, color = "PASS", "green"
    elif fetching:
        label, color = "…", "blue"
    else:
        label, color = "IDLE", "gray"
    return label, color, _TITLE_SYMBOLS[label]


def _line(text: str, **params: str) -> str:
    extras = " ".join(f"{key}={value}" for key, value in params.items() if value)
    return f"{text} | {extras}" if extras else text


def _short_repo(repo: str) -> str:
    return repo.rsplit("/", 1)[-1] if "/" in repo else repo


def _status_symbol(status: str) -> str:
    return _STATUS_SYMBOLS.get(status, "circle")


def _roll_up_repo(builds: Sequence[Mapping[str, Any]]) -> tuple[str, bool]:
    settled = [build for build in builds if str(build.get("status")) not in _IN_PROGRESS]
    is_running = any(str(build.get("status")) in _IN_PROGRESS for build in builds)
    if any(str(build.get("status")) == "FAIL" for build in settled):
        status = "FAIL"
    elif any(str(build.get("status")) == "CONNECTION_ERROR" for build in settled):
        status = "CONNECTION_ERROR"
    elif any(str(build.get("status")) == "APPROVAL" for build in settled):
        status = "APPROVAL"
    elif settled and all(str(build.get("status")) == "PASS" for build in settled):
        status = "PASS"
    elif settled:
        status = "UNKNOWN"
    else:
        status = "NONE"
    if status == "NONE" and is_running:
        has_running = any(str(build.get("status")) == "RUNNING" for build in builds)
        has_waiting = any(str(build.get("status")) == "WAITING" for build in builds)
        status = "WAITING" if has_waiting and not has_running else "RUNNING"
    return status, is_running


def _group_by_repo(builds: Sequence[Mapping[str, Any]]) -> list[tuple[str, str, bool, list[Mapping[str, Any]]]]:
    by_repo: dict[str, list[Mapping[str, Any]]] = {}
    for build in builds:
        repo = str(build.get("repo") or "?")
        by_repo.setdefault(repo, []).append(build)
    grouped: list[tuple[str, str, bool, list[Mapping[str, Any]]]] = []
    for repo, repo_builds in by_repo.items():
        status, is_running = _roll_up_repo(repo_builds)
        workflows = sorted(repo_builds, key=lambda item: str(item.get("workflow") or "").lower())
        grouped.append((repo, status, is_running, workflows))
    grouped.sort(key=lambda item: (_REPO_SORT.get(item[1], 9), item[0].lower()))
    return grouped


def _workflow_line(build: Mapping[str, Any], *, nested: bool = False) -> str:
    workflow = str(build.get("workflow") or "?")
    status = str(build.get("status") or "?")
    url = str(build.get("url") or "")
    color = _BUILD_COLORS.get(status, "gray")
    prefix = "-- " if nested else ""
    params = {
        "color": color,
        "sfimage": _status_symbol(status),
        "sfcolor": color,
        "length": "56",
        "tooltip": status,
    }
    if url:
        params["href"] = url
    return prefix + _line(workflow, **params)


def _attention_line(build: Mapping[str, Any]) -> str:
    repo = _short_repo(str(build.get("repo") or "?"))
    workflow = str(build.get("workflow") or "?")
    status = str(build.get("status") or "?")
    url = str(build.get("url") or "")
    color = _BUILD_COLORS.get(status, "gray")
    params = {
        "color": color,
        "sfimage": _status_symbol(status),
        "sfcolor": color,
        "length": "56",
        "tooltip": f"{build.get('repo') or '?'} {status}",
    }
    if url:
        params["href"] = url
    return _line(f"{repo} · {workflow}", **params)


def plugin_output(
    payload: Mapping[str, Any],
    *,
    dashboard_url: str = DEFAULT_DASHBOARD,
) -> str:
    label, color, symbol = title_for(payload)
    lines = [
        _line(
            "\u200b",
            sfimage=symbol,
            sfcolor=color,
            tooltip=label,
        ),
        "---",
    ]
    raw_builds: Sequence[Any] = payload.get("builds") or []
    builds = [build for build in raw_builds if isinstance(build, Mapping)]
    if builds:
        attention = [build for build in builds if str(build.get("status")) in _ATTENTION]
        attention.sort(key=lambda item: (_REPO_SORT.get(str(item.get("status")), 9), str(item.get("repo") or "")))
        if attention:
            lines.append(_line("Needs attention", disabled="true"))
            lines.extend(_attention_line(build) for build in attention)
            lines.append("---")
        lines.append(_line("Watched", disabled="true"))
        for repo, status, is_running, workflows in _group_by_repo(builds):
            color = _BUILD_COLORS.get(status, "gray")
            count = len(workflows)
            meta = f"{count} workflow" if count == 1 else f"{count} workflows"
            if is_running:
                meta += " · running"
            params = {
                "sfimage": _status_symbol(status),
                "sfcolor": color,
                "color": color,
                "tooltip": f"{repo} · {meta}",
            }
            lines.append(_line(_short_repo(repo), **params))
            lines.extend(_workflow_line(build, nested=True) for build in workflows)
            if "/" in repo:
                lines.append(_line("-- Open on GitHub", href=f"https://github.com/{repo}"))
        lines.append("---")
    else:
        lines.append(_line("No builds yet", disabled="true"))
        lines.append("---")
    lines.append(_line("Open monitor", href=dashboard_url, sfimage="safari"))
    lines.append(_line("Refresh", refresh="true", sfimage="arrow.clockwise"))
    return "\n".join(lines) + "\n"
