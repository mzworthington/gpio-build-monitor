#!/usr/bin/env python3

import asyncio
import logging
from typing import NotRequired, TypedDict

from aiohttp import ClientSession

from monitor.ci_gateway.constants import (
    IN_PROGRESS_VALUES,
    CiResult,
    IntegrationAdapter,
)

Result = CiResult


class BuildDetail(TypedDict):
    repo: str
    workflow: str
    status: str
    url: str
    pr_count: NotRequired[int | None]
    pr_url: NotRequired[str | None]


def get_status_from_details(builds: list[BuildDetail]) -> Result:
    """Roll up build details.

    Priority: FAIL > fetch/CONNECTION_ERROR > APPROVAL > all PASS.
    RUNNING/WAITING are tracked via ``is_running`` and elevated in the UI.
    """
    settled = [
        build for build in builds
        if build["status"] not in IN_PROGRESS_VALUES
    ]
    if not settled:
        if not builds_in_progress(builds):
            return Result.NONE
        waiting_only = any(
            build["status"] == CiResult.WAITING.value for build in builds
        ) and not any(build["status"] == CiResult.RUNNING.value for build in builds)
        return Result.WAITING if waiting_only else Result.RUNNING
    if any(build["status"] == CiResult.FAIL.value for build in settled):
        return Result.FAIL
    if any(build["status"] == CiResult.CONNECTION_ERROR.value for build in settled):
        return Result.CONNECTION_ERROR
    if any(build["status"] == CiResult.APPROVAL.value for build in settled):
        return Result.APPROVAL
    if all(build["status"] == CiResult.PASS.value for build in settled):
        return Result.PASS
    return Result.UNKNOWN


def builds_in_progress(builds: list[BuildDetail]) -> bool:
    return any(build["status"] in IN_PROGRESS_VALUES for build in builds)


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
        if build["status"] in {
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
    pr_count: int | None
    pr_url: str | None
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
        pr_count = next(
            (build.get("pr_count") for build in repo_builds if build.get("pr_count") is not None),
            None,
        )
        pr_url = next(
            (build.get("pr_url") for build in repo_builds if build.get("pr_url")),
            None,
        )
        if pr_count is not None and not pr_url and "/" in repo:
            pr_url = f"https://github.com/{repo}/pulls"
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
            "pr_count": pr_count,
            "pr_url": pr_url,
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

        builds: list[BuildDetail] = []
        for integration_builds in completed:
            builds.extend(integration_builds)

        return OverallStatus(
            type="AGGREGATED",
            is_running=builds_in_progress(builds),
            status=get_status_from_details(builds),
            builds=builds,
        )

    async def _fetch(
        self,
        session: ClientSession,
        integration: IntegrationAdapter,
    ) -> list[BuildDetail]:
        repo = f"{integration.username}/{integration.repo}"
        latest, pull_requests = await asyncio.gather(
            integration.get_latest(session),
            integration.open_pull_requests(session),
            return_exceptions=True,
        )
        pr_count: int | None = None
        pr_url: str | None = None
        if isinstance(pull_requests, Exception):
            logging.exception("Failed to fetch pull requests for %s", repo)
        else:
            pr_count, pr_url = pull_requests

        if isinstance(latest, Exception):
            logging.exception("Failed to fetch build status for %s", repo)
            return [
                BuildDetail(
                    repo=repo,
                    workflow="(fetch)",
                    status=CiResult.CONNECTION_ERROR.value,
                    url="",
                    pr_count=pr_count,
                    pr_url=pr_url,
                )
            ]

        return [
            BuildDetail(
                repo=repo,
                workflow=build["name"],
                status=build["status"].value,
                url=build["vcs"],
                pr_count=pr_count,
                pr_url=pr_url,
            )
            for build in latest
        ]
