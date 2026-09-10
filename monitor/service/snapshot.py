#!/usr/bin/env python3

"""Snapshot query model for battery and always-on clients.

The hosted Worker (and local WebSocket adapter) expose aggregated CI status
over HTTP. Always-on clients (browser, Mac menu bar) use the full payload.
Battery clients (Xteink X4) sample the same port, then deep-sleep using
``sleep_seconds`` / ``Retry-After``.
"""

from collections.abc import Mapping, Sequence
from hashlib import sha256
from json import dumps
from typing import Any

from monitor.service.aggregator_service import BuildDetail, Result, repo_summaries

# Seconds the device should remain in deep sleep after a successful sample.
# The hub keeps polling on its own cadence; these values are for the radio.
SLEEP_RUNNING_SECONDS = 120
SLEEP_ATTENTION_SECONDS = 180
SLEEP_FETCH_ERROR_SECONDS = 300
SLEEP_SETTLED_SECONDS = 900

_GLANCEABLE = frozenset({
    "FAIL",
    "CONNECTION_ERROR",
    "APPROVAL",
    "UNKNOWN",
    "RUNNING",
    "WAITING",
})


def sleep_seconds(status: str | Result, *, is_running: bool) -> int:
    """How long a battery client should deep-sleep after this snapshot.

    Running builds win so the panel catches completion. Failures and
    approvals stay shorter than green so the desk still feels live.
    Connection errors back off to avoid a Wi-Fi death spiral.
    """
    value = status.value if isinstance(status, Result) else status
    if is_running:
        return SLEEP_RUNNING_SECONDS
    if value in {Result.FAIL.value, Result.UNKNOWN.value, Result.APPROVAL.value}:
        return SLEEP_ATTENTION_SECONDS
    if value == Result.CONNECTION_ERROR.value:
        return SLEEP_FETCH_ERROR_SECONDS
    return SLEEP_SETTLED_SECONDS


def open_pr_glances(builds: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    glances: list[dict[str, Any]] = []
    seen: set[str] = set()
    for build in builds or []:
        repo = str(build.get("repo") or "")
        count = build.get("pr_count")
        if not repo or repo in seen or count is None:
            continue
        try:
            numeric = int(count)
        except (TypeError, ValueError):
            continue
        if numeric <= 0:
            continue
        seen.add(repo)
        glances.append({
            "repo": repo,
            "pr_count": numeric,
            "pr_url": build.get("pr_url") or f"https://github.com/{repo}/pulls",
        })
    return glances


def snapshot_etag(
    status: str | Result,
    *,
    is_running: bool,
    builds: Sequence[Mapping[str, Any]] | None = None,
) -> str:
    """Weak ETag of glance-relevant fields (not fetch timestamps)."""
    value = status.value if isinstance(status, Result) else status
    body = dumps(
        {
            "builds": list(builds or []),
            "is_running": is_running,
            "open_prs": open_pr_glances(builds),
            "status": value,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = sha256(body.encode("utf-8")).hexdigest()[:16]
    return f'W/"{digest}"'


def eink_builds(builds: Sequence[Mapping[str, Any]] | None) -> list[Mapping[str, Any]]:
    """Keep failures, in-progress, and other attention rows for the panel."""
    return [
        build
        for build in (builds or [])
        if str(build.get("status")) in _GLANCEABLE
    ]


def eink_repos(builds: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    details: list[BuildDetail] = []
    for item in builds or []:
        row: BuildDetail = {
            "repo": str(item.get("repo") or ""),
            "workflow": str(item.get("workflow") or ""),
            "status": str(item.get("status") or ""),
            "url": str(item.get("url") or ""),
        }
        pr_count = item.get("pr_count")
        if pr_count is not None:
            row["pr_count"] = int(pr_count)
        pr_url = item.get("pr_url")
        if pr_url:
            row["pr_url"] = str(pr_url)
        details.append(row)
    return [
        {
            "repo": summary["repo"],
            "status": summary["status"],
            "workflow_count": summary["workflow_count"],
            "pr_count": int(summary["pr_count"] or 0),
            "is_running": bool(summary["is_running"]),
        }
        for summary in repo_summaries(details)
    ]


def eink_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Compact snapshot: same keys, but only glanceable builds."""
    status = str(payload.get("status") or Result.NONE.value)
    is_running = bool(payload.get("is_running"))
    raw_builds = payload.get("builds")
    raw_list = raw_builds if isinstance(raw_builds, list) else []
    builds = eink_builds(raw_list)
    return {
        "type": "status",
        "fetching": False,
        "status": status,
        "is_running": is_running,
        "builds": builds,
        "repos": eink_repos(raw_list),
        "open_prs": open_pr_glances(raw_list),
        "poll_in_seconds": payload.get("poll_in_seconds"),
        "last_checked_at": payload.get("last_checked_at"),
        "next_check_at": payload.get("next_check_at"),
        "sleep_seconds": sleep_seconds(status, is_running=is_running),
    }


def snapshot_headers(
    status: str | Result,
    *,
    is_running: bool,
    builds: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, str]:
    seconds = sleep_seconds(status, is_running=is_running)
    return {
        "Cache-Control": "no-store",
        "ETag": snapshot_etag(status, is_running=is_running, builds=builds),
        "Retry-After": str(seconds),
    }


def etag_matches(if_none_match: str | None, etag: str) -> bool:
    if not if_none_match:
        return False
    offered = {part.strip() for part in if_none_match.split(",") if part.strip()}
    return "*" in offered or etag in offered
