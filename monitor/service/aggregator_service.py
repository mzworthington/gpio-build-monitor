#!/usr/bin/env python3

import asyncio
import enum
import logging
from typing import TypedDict

from aiohttp import ClientSession

from monitor.ci_gateway.constants import BuildStatus, CiResult, IntegrationAdapter


class Result(enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    NONE = "NONE"

    def __eq__(self, other):
        return self.value == other.value


class BuildDetail(TypedDict):
    repo: str
    workflow: str
    status: str
    url: str


def get_status(results: list[BuildStatus]) -> Result:
    if len(results) == 0:
        return Result.NONE
    if any(r['status'] == CiResult.CONNECTION_ERROR for r in results):
        return Result.CONNECTION_ERROR
    if any(r['status'] == CiResult.FAIL for r in results):
        return Result.FAIL
    if all(r['status'] == CiResult.PASS for r in results):
        return Result.PASS
    return Result.UNKNOWN


def get_status_from_details(builds: list[BuildDetail]) -> Result:
    non_running = [
        build for build in builds
        if build["status"] != CiResult.RUNNING.value
    ]
    if not non_running:
        return Result.NONE
    if any(build["status"] == CiResult.CONNECTION_ERROR.value for build in non_running):
        return Result.CONNECTION_ERROR
    if any(build["status"] == CiResult.FAIL.value for build in non_running):
        return Result.FAIL
    if all(build["status"] == CiResult.PASS.value for build in non_running):
        return Result.PASS
    return Result.UNKNOWN


class OverallStatus(TypedDict):
    type: str
    is_running: bool
    status: Result
    builds: list[BuildDetail]


def attention_builds(builds: list[BuildDetail]) -> list[BuildDetail]:
    """Builds that should be called out in the UI (failed / error / unknown)."""
    return [
        build
        for build in builds
        if build["status"] in {
            CiResult.FAIL.value,
            CiResult.CONNECTION_ERROR.value,
            CiResult.UNKNOWN.value,
        }
    ]


class RepoSummary(TypedDict):
    repo: str
    status: str
    workflow_count: int
    is_running: bool
    url: str
    workflows: list[BuildDetail]


def repo_summaries(builds: list[BuildDetail]) -> list[RepoSummary]:
    """One row per repo with worst status across its workflows."""
    by_repo: dict[str, list[BuildDetail]] = {}
    for build in builds:
        by_repo.setdefault(build["repo"], []).append(build)

    summaries: list[RepoSummary] = []
    for repo, repo_builds in by_repo.items():
        status = get_status_from_details(repo_builds).value
        is_running = any(b["status"] == CiResult.RUNNING.value for b in repo_builds)
        if status == Result.NONE.value and is_running:
            status = CiResult.RUNNING.value
        url = f"https://github.com/{repo}" if "/" in repo else ""
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
            is_running=any(build["status"] == CiResult.RUNNING.value for build in builds),
            status=get_status_from_details(builds),
            builds=builds,
        )

    async def _fetch(
        self,
        session: ClientSession,
        integration: IntegrationAdapter,
    ) -> list[BuildDetail]:
        repo = f"{integration.username}/{integration.repo}"
        try:
            results = await integration.get_latest(session)
        except Exception:
            logging.exception("Failed to fetch build status for %s", repo)
            return [
                BuildDetail(
                    repo=repo,
                    workflow="(fetch)",
                    status=CiResult.CONNECTION_ERROR.value,
                    url="",
                )
            ]

        return [
            BuildDetail(
                repo=repo,
                workflow=build["name"],
                status=build["status"].value,
                url=build["vcs"],
            )
            for build in results
        ]
