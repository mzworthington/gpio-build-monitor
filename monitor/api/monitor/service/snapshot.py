#!/usr/bin/env python3

"""Snapshot query model for battery and always-on clients.

The hosted Worker (and local WebSocket adapter) expose aggregated CI status
over HTTP. Always-on clients (browser, Mac menu bar) use the full payload.
Battery clients (Xteink X4) sample the same port, then deep-sleep using
``sleep_seconds`` / ``Retry-After``. Agents sample ``view=agent``, a glance
with ``retry_after_seconds``, and do not poll CI themselves.
"""

from collections.abc import Mapping, Sequence
from hashlib import sha256
from json import dumps
from typing import Any

from monitor.service.aggregator_service import (
    BuildDetail,
    OverallStatus,
    Result,
    builds_in_progress,
    get_status_from_details,
    repo_summaries,
)

# Seconds the device should remain in deep sleep after a successful sample.
# The hub keeps polling on its own cadence; these values are for the radio.
SLEEP_RUNNING_SECONDS = 120
SLEEP_ATTENTION_SECONDS = 180
SLEEP_FETCH_ERROR_SECONDS = 300
SLEEP_SETTLED_SECONDS = 900

EINK_MAX_WORKFLOWS = 16


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
        pulls = build.get("pull_requests")
        if not repo or repo in seen or not isinstance(pulls, Mapping):
            continue
        count = pulls.get("count")
        if count is None:
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
            "count": numeric,
            "url": pulls.get("url") or f"https://github.com/{repo}/pulls",
            "items": list(pulls.get("items") or []),
        })
    return glances


def security_glances(builds: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    glances: list[dict[str, Any]] = []
    seen: set[str] = set()
    for build in builds or []:
        repo = str(build.get("repo") or "")
        security = build.get("security")
        if not repo or repo in seen or not isinstance(security, Mapping):
            continue
        count = security.get("count")
        if count is None:
            continue
        try:
            numeric = int(count)
        except (TypeError, ValueError):
            continue
        seen.add(repo)
        glances.append({
            "repo": repo,
            "count": numeric,
            "url": security.get("url") or f"https://github.com/{repo}/security",
            "vulnerabilities": security.get("vulnerabilities") or {
                "count": 0,
                "url": f"https://github.com/{repo}/security/dependabot",
                "items": [],
            },
            "codeql": security.get("codeql") or {
                "count": 0,
                "url": f"https://github.com/{repo}/security/code-scanning",
                "items": [],
            },
        })
    return glances


def _source_count(source: object) -> int:
    if not isinstance(source, Mapping):
        return 0
    try:
        return int(source.get("count") or 0)
    except (TypeError, ValueError):
        return 0


def _pull_count(summary: Mapping[str, Any]) -> int:
    return _source_count(summary.get("pull_requests"))


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
            "security": security_glances(builds),
            "status": value,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = sha256(body.encode("utf-8")).hexdigest()[:16]
    return f'W/"{digest}"'


def eink_repo_row(summary: Mapping[str, Any], *, include_workflows: bool) -> dict[str, Any]:
    row: dict[str, Any] = {
        "repo": summary["repo"],
        "status": summary["status"],
        "workflow_count": summary["workflow_count"],
        "pr_count": _pull_count(summary),
        "security_count": _source_count(summary.get("security")),
        "is_running": bool(summary["is_running"]),
    }
    if include_workflows:
        row["workflows"] = [
            {"workflow": item["workflow"], "status": item["status"]}
            for item in list(summary["workflows"])[:EINK_MAX_WORKFLOWS]
        ]
    return row


def eink_repos(builds: Sequence[BuildDetail] | None, *, include_workflows: bool = False) -> list[dict[str, Any]]:
    return [
        eink_repo_row(summary, include_workflows=include_workflows)
        for summary in repo_summaries(list(builds or []))
    ]


def eink_payload(payload: OverallStatus) -> dict[str, Any]:
    details = list(payload["builds"])
    rolled = get_status_from_details(details)
    status = rolled.value
    is_running = bool(payload.get("is_running")) or builds_in_progress(details)
    return {
        "type": "status",
        "fetching": False,
        "status": status,
        "is_running": is_running,
        "repos": eink_repos(details, include_workflows=False),
        "sleep_seconds": sleep_seconds(status, is_running=is_running),
    }


def eink_repo_payload(payload: OverallStatus, repo: str) -> dict[str, Any]:
    details = list(payload["builds"])
    compact = eink_payload(payload)
    compact["repos"] = [
        row for row in eink_repos(details, include_workflows=True) if row["repo"] == repo
    ]
    return compact


def _details(payload: Mapping[str, Any]) -> list[BuildDetail]:
    return list(payload.get("builds") or [])


def _agent_timing(payload: Mapping[str, Any]) -> dict[str, Any]:
    details = _details(payload)
    status = get_status_from_details(details).value
    is_running = bool(payload.get("is_running")) or builds_in_progress(details)
    return {
        "status": status,
        "is_running": is_running,
        "last_checked_at": payload.get("last_checked_at"),
        "retry_after_seconds": sleep_seconds(status, is_running=is_running),
    }


def agent_payload(payload: OverallStatus) -> dict[str, Any]:
    """Glance an agent can read without the UI build list."""
    return {
        "type": "status",
        **_agent_timing(payload),
        "repos": eink_repos(_details(payload), include_workflows=False),
    }


def _workflow_rows(builds: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    rows = [
        {
            "workflow": str(build.get("workflow") or ""),
            "status": str(build.get("status") or ""),
            "url": str(build.get("url") or ""),
        }
        for build in builds
        if build.get("repo")
    ]
    rows.sort(key=lambda item: item["workflow"].lower())
    return rows


def _pull_items(builds: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    for build in builds:
        pulls = build.get("pull_requests")
        if not isinstance(pulls, Mapping):
            continue
        try:
            count = int(pulls.get("count") or 0)
        except (TypeError, ValueError):
            continue
        if count <= 0:
            continue
        items = []
        for item in pulls.get("items") or []:
            if not isinstance(item, Mapping):
                continue
            if not isinstance(item.get("number"), int) or not isinstance(item.get("title"), str):
                continue
            items.append({
                "number": item["number"],
                "title": item["title"],
                "url": str(item.get("url") or ""),
                "draft": bool(item.get("draft")),
            })
        return items
    return []


def _security_items(builds: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    for build in builds:
        security = build.get("security")
        if not isinstance(security, Mapping) or security.get("count") is None:
            continue
        rows: list[dict[str, Any]] = []
        for source in ("vulnerabilities", "codeql"):
            bucket = security.get(source)
            if not isinstance(bucket, Mapping):
                continue
            for item in bucket.get("items") or []:
                if not isinstance(item, Mapping) or not isinstance(item.get("title"), str):
                    continue
                rows.append({
                    "title": item["title"],
                    "severity": item.get("severity"),
                    "url": str(item.get("url") or ""),
                    "state": str(item.get("state") or ""),
                    "source": source,
                })
        return rows
    return []


def agent_repo_status(payload: OverallStatus, repo: str) -> dict[str, Any] | None:
    details = [build for build in _details(payload) if build.get("repo") == repo]
    if not repo or not details:
        return None
    timing = _agent_timing(payload)
    rolled = get_status_from_details(details)
    return {
        "repo": repo,
        "status": rolled.value,
        "is_running": builds_in_progress(details),
        "last_checked_at": timing["last_checked_at"],
        "retry_after_seconds": timing["retry_after_seconds"],
        "workflows": _workflow_rows(details),
        "pull_requests": _pull_items(details),
        "security": _security_items(details),
    }


def agent_repo_payload(payload: OverallStatus, repo: str) -> dict[str, Any]:
    found = agent_repo_status(payload, repo)
    if found is not None:
        return found
    timing = _agent_timing(payload)
    return {
        "repo": repo,
        "status": "NONE",
        "is_running": False,
        "last_checked_at": timing["last_checked_at"],
        "retry_after_seconds": timing["retry_after_seconds"],
        "workflows": [],
        "pull_requests": [],
        "security": [],
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
