#!/usr/bin/env python3

import asyncio
import logging
from typing import NotRequired, TypedDict

from aiohttp import ClientSession

from monitor.ci_gateway.constants import (
    IN_PROGRESS_VALUES,
    CiResult,
    IntegrationAdapter,
    PullRequests,
    SecurityFindings,
)

Result = CiResult


def _status_value(status: str | CiResult) -> str:
    return status.value if isinstance(status, CiResult) else status


class BuildDetail(TypedDict):
    repo: str
    workflow: str
    status: str
    url: str
    pull_requests: NotRequired[PullRequests | None]
    security: NotRequired[SecurityFindings | None]


def get_status_from_details(builds: list[BuildDetail]) -> Result:
    """Roll up build details.

    Priority: FAIL > fetch/CONNECTION_ERROR > APPROVAL > all PASS.
    RUNNING/WAITING are tracked via ``is_running`` and elevated in the UI.
    """
    settled = [
        build for build in builds
        if _status_value(build["status"]) not in IN_PROGRESS_VALUES
    ]
    if not settled:
        if not builds_in_progress(builds):
            return Result.NONE
        waiting_only = any(
            _status_value(build["status"]) == CiResult.WAITING.value for build in builds
        ) and not any(
            _status_value(build["status"]) == CiResult.RUNNING.value for build in builds
        )
        return Result.WAITING if waiting_only else Result.RUNNING
    if any(_status_value(build["status"]) == CiResult.FAIL.value for build in settled):
        return Result.FAIL
    if any(_status_value(build["status"]) == CiResult.CONNECTION_ERROR.value for build in settled):
        return Result.CONNECTION_ERROR
    if any(_status_value(build["status"]) == CiResult.APPROVAL.value for build in settled):
        return Result.APPROVAL
    if all(_status_value(build["status"]) == CiResult.PASS.value for build in settled):
        return Result.PASS
    return Result.UNKNOWN


def builds_in_progress(builds: list[BuildDetail]) -> bool:
    return any(_status_value(build["status"]) in IN_PROGRESS_VALUES for build in builds)


class OverallStatus(TypedDict):
    type: str
    is_running: bool
    status: Result
    builds: list[BuildDetail]


def attention_builds(builds: list[BuildDetail]) -> list[BuildDetail]:
    """Builds that should be called out in the UI (failed / error / approval / unknown)."""
    return [
        build
        for build in builds
        if _status_value(build["status"]) in {
            CiResult.FAIL.value,
            CiResult.CONNECTION_ERROR.value,
            CiResult.APPROVAL.value,
            CiResult.UNKNOWN.value,
        }
    ]


class RepoSummary(TypedDict):
    repo: str
    status: str
    workflow_count: int
    is_running: bool
    url: str
    pull_requests: PullRequests | None
    security: SecurityFindings | None
    workflows: list[BuildDetail]


def repo_summaries(builds: list[BuildDetail]) -> list[RepoSummary]:
    """One row per repo with worst status across its workflows."""
    by_repo: dict[str, list[BuildDetail]] = {}
    for build in builds:
        by_repo.setdefault(build["repo"], []).append(build)

    summaries: list[RepoSummary] = []
    for repo, repo_builds in by_repo.items():
        status = get_status_from_details(repo_builds).value
        is_running = builds_in_progress(repo_builds)
        url = f"https://github.com/{repo}" if "/" in repo else ""
        pull_requests = next(
            (
                build.get("pull_requests")
                for build in repo_builds
                if build.get("pull_requests") is not None
            ),
            None,
        )
        security = next(
            (build.get("security") for build in repo_builds if build.get("security") is not None),
            None,
        )
        workflows = sorted(
            repo_builds,
            key=lambda item: (item.get("workflow") or "").lower(),
        )
        summaries.append({
            "repo": repo,
            "status": status,
            "workflow_count": len(repo_builds),
            "is_running": is_running,
            "url": url,
            "pull_requests": pull_requests,
            "security": security,
            "workflows": workflows,
        })

    summaries.sort(key=lambda item: item["repo"].lower())
    return summaries


class AggregatorService:
    def __init__(self, integrations: list[IntegrationAdapter]):
        self.integrations = integrations

    async def run(self, session: ClientSession) -> OverallStatus:
        tasks = [
            asyncio.create_task(self._fetch(session, integration))
            for integration in self.integrations
        ]
        completed = await asyncio.gather(*tasks)

        fetched: list[BuildDetail] = []
        for integration_builds in completed:
            fetched.extend(integration_builds)

        builds = [
            BuildDetail(
                repo=build["repo"],
                workflow=build["workflow"],
                status=_status_value(build["status"]),
                url=build["url"],
                pull_requests=build.get("pull_requests"),
                security=build.get("security"),
            )
            for build in fetched
        ]

        return OverallStatus(
            type="AGGREGATED",
            is_running=builds_in_progress(fetched),
            status=get_status_from_details(fetched),
            builds=builds,
        )

    async def _fetch(
        self,
        session: ClientSession,
        integration: IntegrationAdapter,
    ) -> list[BuildDetail]:
        repo = f"{integration.username}/{integration.repo}"
        latest, fetched_pulls, security = await asyncio.gather(
            integration.get_latest(session),
            integration.open_pull_requests(session),
            integration.security_findings(session),
            return_exceptions=True,
        )
        pull_requests: PullRequests | None = None
        if isinstance(fetched_pulls, Exception):
            logging.exception("Failed to fetch pull requests for %s", repo)
        else:
            pull_requests = fetched_pulls

        findings: SecurityFindings | None = None
        if isinstance(security, Exception):
            logging.exception("Failed to fetch security findings for %s", repo)
        else:
            findings = security

        if isinstance(latest, Exception):
            logging.exception("Failed to fetch build status for %s", repo)
            return [
                BuildDetail(
                    repo=repo,
                    workflow="(fetch)",
                    status=CiResult.CONNECTION_ERROR,
                    url="",
                    pull_requests=pull_requests,
                    security=findings,
                )
            ]

        return [
            BuildDetail(
                repo=repo,
                workflow=build["name"],
                status=build["status"],
                url=build["vcs"],
                pull_requests=pull_requests,
                security=findings,
            )
            for build in latest
        ]
