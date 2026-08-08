#!/usr/bin/env python3

from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from monitor.service.aggregator_service import (
    BuildDetail,
    Result,
    attention_builds,
    repo_summaries,
)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "web" / "templates"

SUMMARIES = {
    Result.PASS.value: "All builds passed",
    Result.FAIL.value: "At least one build failed",
    Result.UNKNOWN.value: "Mixed or unknown status",
    Result.CONNECTION_ERROR.value: "Could not reach a CI provider",
    Result.NONE.value: "No build results yet",
    "RUNNING": "Build in progress",
}

STATUS_WORDS = {
    Result.PASS.value: "Passing",
    Result.FAIL.value: "Failing",
    Result.UNKNOWN.value: "Mixed",
    Result.CONNECTION_ERROR.value: "Offline",
    Result.NONE.value: "Idle",
    "RUNNING": "Running",
}

# When something is running and nothing has failed/errored, the dial leads with Running.
_RUNNING_OVERRIDES = {
    Result.PASS.value,
    Result.NONE.value,
    Result.UNKNOWN.value,
}


def _display_status(status: str, *, is_running: bool, fetching: bool) -> str:
    if fetching:
        return status
    if is_running and status in _RUNNING_OVERRIDES:
        return "RUNNING"
    return status


class StatusPageRenderer:
    """Renders the status page HTML from a WebSocket payload."""

    def __init__(self, template_dir: Path | None = None):
        directory = template_dir or TEMPLATE_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(directory)),
            autoescape=select_autoescape(["html", "xml", "j2"]),
        )
        self._template = self._env.get_template("status.html.j2")

    def render(
        self,
        *,
        status: str = Result.NONE.value,
        fetching: bool = False,
        is_running: bool = False,
        connected: bool = False,
        refresh_seconds: int = 0,
        builds: Sequence[BuildDetail] | None = None,
        poll_in_seconds: int = 30,
        last_checked_at: float | None = None,
        next_check_at: float | None = None,
    ) -> str:
        shown = _display_status(status, is_running=is_running, fetching=fetching)
        if fetching:
            status_word = "Checking"
            summary = SUMMARIES.get(status, SUMMARIES[Result.NONE.value]) + " · fetching"
        elif shown == "RUNNING":
            status_word = STATUS_WORDS["RUNNING"]
            summary = SUMMARIES["RUNNING"]
        else:
            status_word = STATUS_WORDS.get(status, STATUS_WORDS[Result.NONE.value])
            summary = SUMMARIES.get(status, SUMMARIES[Result.NONE.value])
            if is_running:
                summary += " · build running"

        build_list = list(builds or [])
        issues = attention_builds(build_list)
        repos = repo_summaries(build_list)
        last_checked_label = _format_last_checked(last_checked_at)

        return self._template.render(
            refresh_seconds=refresh_seconds,
            connection_state="live" if connected else "offline",
            connection_label="Live" if connected else "Waiting for monitor…",
            fetching=fetching,
            green_on=status in {Result.PASS.value, Result.UNKNOWN.value},
            yellow_on=is_running,
            red_on=status in {Result.FAIL.value, Result.UNKNOWN.value},
            purple_on=status == Result.CONNECTION_ERROR.value,
            summary=summary,
            status_word=status_word,
            issues=issues,
            repos=repos,
            poll_in_seconds=poll_in_seconds,
            last_checked_at=last_checked_at,
            last_checked_label=last_checked_label,
            next_check_at=next_check_at,
            status=shown,
        )


def _format_last_checked(timestamp: float | None) -> str:
    if timestamp is None:
        return "Not checked yet"
    checked = datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone()
    return f"Checked {checked.strftime('%H:%M:%S')}"
