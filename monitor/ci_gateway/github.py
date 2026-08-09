#!/usr/bin/env python3

import logging
import os
import re
from abc import ABC
from fnmatch import fnmatch
from itertools import groupby

from aiohttp import ClientSession

from monitor.ci_gateway.constants import (
    APIError,
    BuildStatus,
    CiResult,
    IntegrationAdapter,
    IntegrationType,
)

ALL_BRANCHES = "*"

# Dependabot version checks: unique Update #ID (and optional package list) per run.
# Collapse to ecosystem + directory so a newer check supersedes a historic fail.
_DEPENDABOT_UPDATE_KEY = re.compile(
    r"^(?P<head>.+?)(?: for .+?)? - Update #\d+$"
)


class GitHubAction(IntegrationAdapter, ABC):
    def __init__(self, **kwargs):
        self.username = kwargs.get('username')
        self.repo = kwargs.get('repo')
        self.token = kwargs.get('token') or os.getenv('GITHUB_TOKEN')
        self.excluded_workflows = kwargs.get('excluded_workflows') or []
        self.excluded_workflow_patterns = kwargs.get('excluded_workflow_patterns') or []
        self.branch = kwargs.get('branch', 'main')

    def get_type(self) -> IntegrationType:
        return IntegrationType.GITHUB

    @property
    def filters_by_branch(self) -> bool:
        return bool(self.branch) and self.branch != ALL_BRANCHES

    async def get_latest(self, session: ClientSession) -> list[BuildStatus]:
        base = 'https://api.github.com'
        url = f'{base}/repos/{self.username}/{self.repo}/actions/runs'
        params: dict[str, str] = {'per_page': '100'}
        if self.filters_by_branch:
            params['branch'] = self.branch

        logging.debug('Calling %s (branch=%s)', url, self.branch)

        resp = await session.get(
            url,
            params=params,
            headers={
                'Authorization': f'Bearer {self.token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28',
            },
        )

        if resp.status != 200:
            raise APIError('GET', url, resp.status)

        payload = await resp.json()
        runs = self.get_unique_latest_jobs(payload.get('workflow_runs') or [])
        response = list(map(GitHubAction.map_result, runs))
        logging.info('Called %s (branch=%s)', url, self.branch)
        logging.info('Response %s', response)
        return response

    @staticmethod
    def map_result(latest) -> BuildStatus:
        return BuildStatus(
            type=IntegrationType.GITHUB,
            vcs=latest["html_url"],
            id=latest["id"],
            name=latest["name"],
            start=latest["created_at"],
            status=GitHubAction._map_status(latest["status"], latest["conclusion"]),
        )

    @staticmethod
    def _map_status(status: str, conclusion: str | None) -> CiResult:
        """Map a GitHub Actions run onto the board's priority statuses.

        Cancelled/skipped/neutral do not pollute the aggregate (PASS).
        Waiting (concurrency) and approval gates stay descriptive.
        """
        if conclusion is None:
            if status == "in_progress":
                return CiResult.RUNNING
            if status in {"waiting", "queued", "pending"}:
                return CiResult.WAITING
            return CiResult.UNKNOWN
        if status != "completed":
            return CiResult.UNKNOWN
        if conclusion in {"failure", "timed_out", "startup_failure"}:
            return CiResult.FAIL
        if conclusion == "success":
            return CiResult.PASS
        if conclusion == "action_required":
            return CiResult.APPROVAL
        # cancelled / skipped / neutral / stale — ignore for the desk board
        if conclusion in {"cancelled", "skipped", "neutral", "stale"}:
            return CiResult.PASS
        return CiResult.UNKNOWN

    @staticmethod
    def workflow_identity_key(name: str) -> str:
        """Stable key for 'latest per workflow', collapsing Dependabot Update noise."""
        match = _DEPENDABOT_UPDATE_KEY.match(name or "")
        if match:
            return match.group("head")
        return name or ""

    def _include_run(self, run: dict) -> bool:
        name = run.get('name') or ''
        if name in self.excluded_workflows:
            return False
        if any(fnmatch(name, pattern) for pattern in self.excluded_workflow_patterns):
            logging.debug('Skipping workflow %s matching exclusion pattern', name)
            return False
        if self.filters_by_branch:
            head_branch = run.get('head_branch')
            if head_branch is not None and head_branch != self.branch:
                logging.debug(
                    'Skipping %s run %s on branch %s (want %s)',
                    name,
                    run.get('id'),
                    head_branch,
                    self.branch,
                )
                return False
        return True

    def get_unique_latest_jobs(self, runs: list[dict]) -> list[dict]:
        jobs = []
        filtered = [run for run in runs if self._include_run(run)]
        keyed = sorted(
            filtered,
            key=lambda run: self.workflow_identity_key(run.get("name") or ""),
        )
        for _, group in groupby(
            keyed,
            key=lambda run: self.workflow_identity_key(run.get("name") or ""),
        ):
            newest = max(
                group,
                key=lambda run: run.get("created_at") or "",
            )
            jobs.append(newest)
        return jobs


if __name__ == "__main__":
    import argparse
    import asyncio
    import sys

    parser = argparse.ArgumentParser()

    parser.add_argument('--username', help='repo username')
    parser.add_argument('--repo', help='repo to query')
    parser.add_argument(
        '--branch',
        default='main',
        help='branch to monitor, or * for all branches',
    )

    args = parser.parse_args()

    screen_handler = logging.StreamHandler(stream=sys.stdout)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(screen_handler)

    async def _main():
        async with ClientSession() as session:
            action = GitHubAction(
                username=args.username,
                repo=args.repo,
                branch=args.branch,
                token=os.getenv('GITHUB_TOKEN'),
            )
            result = await action.get_latest(session)
            print(result)

    asyncio.run(_main())
