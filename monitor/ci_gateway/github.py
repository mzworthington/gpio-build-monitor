#!/usr/bin/env python3

import logging
import os
import re
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


class GitHubAction(IntegrationAdapter):
    def __init__(
        self,
        *,
        username: str,
        repo: str,
        token: str | None = None,
        excluded_workflows: list[str] | None = None,
        excluded_workflow_patterns: list[str] | None = None,
        branch: str = "main",
    ):
        self.username = username
        self.repo = repo
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.excluded_workflows = excluded_workflows or []
        self.excluded_workflow_patterns = excluded_workflow_patterns or []
        self.branch = branch

    def get_type(self) -> IntegrationType:
        return IntegrationType.GITHUB

    @property
    def filters_by_branch(self) -> bool:
        return bool(self.branch) and self.branch != ALL_BRANCHES

    def _public_headers(self) -> dict[str, str]:
        return {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'gpio-build-monitor',
        }

    def _auth_headers(self) -> dict[str, str]:
        return {
            **self._public_headers(),
            'Authorization': f'Bearer {self.token}',
        }

    async def _get_json(
        self,
        session: ClientSession,
        url: str,
        params: dict[str, str],
    ) -> object:
        attempts = []
        if self.token:
            attempts.append(self._auth_headers())
        attempts.append(self._public_headers())

        last_status = 0
        for index, headers in enumerate(attempts):
            resp = await session.get(url, params=params, headers=headers)
            last_status = resp.status
            if resp.status == 200:
                return await resp.json()
            await resp.release()
            if resp.status not in {401, 403}:
                break
            if index < len(attempts) - 1:
                logging.warning(
                    'GitHub %s returned %s; retrying without credentials',
                    url,
                    resp.status,
                )

        raise APIError('GET', url, last_status)

    async def _active_workflow_ids(self, session: ClientSession) -> set[int]:
        """Workflow IDs that still have YAML and are enabled (state=active).

        Deleted workflows remain in run history but can never run again; hide them.
        """
        base = 'https://api.github.com'
        url = f'{base}/repos/{self.username}/{self.repo}/actions/workflows'
        logging.debug('Calling %s', url)
        payload = await self._get_json(session, url, {'per_page': '100'})
        workflows = payload.get('workflows') or [] if isinstance(payload, dict) else []
        active_ids = {
            workflow['id']
            for workflow in workflows
            if workflow.get('state') == 'active' and workflow.get('id') is not None
        }
        logging.debug(
            'Active workflows for %s/%s: %s',
            self.username,
            self.repo,
            sorted(active_ids),
        )
        return active_ids

    async def get_latest(self, session: ClientSession) -> list[BuildStatus]:
        base = 'https://api.github.com'
        active_ids = await self._active_workflow_ids(session)

        url = f'{base}/repos/{self.username}/{self.repo}/actions/runs'
        params: dict[str, str] = {'per_page': '100'}
        if self.filters_by_branch:
            params['branch'] = self.branch

        logging.debug('Calling %s (branch=%s)', url, self.branch)

        payload = await self._get_json(session, url, params)
        workflow_runs = (
            payload.get('workflow_runs') or [] if isinstance(payload, dict) else []
        )
        runs = [
            run
            for run in workflow_runs
            if run.get('workflow_id') in active_ids
        ]
        runs = self.get_unique_latest_jobs(runs)
        response = list(map(GitHubAction.map_result, runs))
        logging.info('Called %s (branch=%s)', url, self.branch)
        logging.info('Response %s', response)
        return response

    async def open_pull_requests(self, session: ClientSession) -> tuple[int | None, str | None]:
        base = 'https://api.github.com'
        url = f'{base}/repos/{self.username}/{self.repo}/pulls'
        try:
            payload = await self._get_json(
                session,
                url,
                {'state': 'open', 'per_page': '100'},
            )
        except APIError:
            logging.warning(
                'GitHub pull requests unavailable for %s/%s',
                self.username,
                self.repo,
            )
            return None, None
        if not isinstance(payload, list):
            return None, None
        return (
            len(payload),
            f'https://github.com/{self.username}/{self.repo}/pulls',
        )

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
