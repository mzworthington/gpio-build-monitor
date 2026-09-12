#!/usr/bin/env python3

import asyncio
import logging
import os
import re
from collections.abc import Callable
from fnmatch import fnmatch
from itertools import groupby
from typing import TypeVar

from aiohttp import ClientSession

from monitor.ci_gateway.constants import (
    APIError,
    BuildStatus,
    CiResult,
    IntegrationAdapter,
    IntegrationType,
    PullRequestItem,
    PullRequests,
    SecurityFinding,
    SecurityFindings,
    SecuritySource,
)

ALL_BRANCHES = "*"

# Dependabot version checks: unique Update #ID (and optional package list) per run.
# Collapse to ecosystem + directory so a newer check supersedes a historic fail.
_DEPENDABOT_UPDATE_KEY = re.compile(
    r"^(?P<head>.+?)(?: for .+?)? - Update #\d+$"
)
_LINK_NEXT = re.compile(r'<([^>]+)>\s*;\s*rel="next"', re.IGNORECASE)
_ALERT_PAGE_CAP = 10
_ALERT_PAGE_SIZE = "100"


def github_security_payload(
    username: str,
    repo: str,
    *,
    vulnerabilities: list[SecurityFinding],
    codeql: list[SecurityFinding],
) -> SecurityFindings:
    base = f"https://github.com/{username}/{repo}/security"
    return {
        "count": len(vulnerabilities) + len(codeql),
        "url": base,
        "vulnerabilities": _security_source(
            f"{base}/dependabot",
            vulnerabilities,
        ),
        "codeql": _security_source(f"{base}/code-scanning", codeql),
    }


def github_pull_requests_payload(
    username: str,
    repo: str,
    items: list[PullRequestItem],
) -> PullRequests:
    return {
        "count": len(items),
        "url": f"https://github.com/{username}/{repo}/pulls",
        "items": items,
    }


def _security_source(url: str, items: list[SecurityFinding]) -> SecuritySource:
    return {"count": len(items), "url": url, "items": items}


def map_dependabot_alert(alert: object) -> SecurityFinding | None:
    if not isinstance(alert, dict):
        return None
    number = alert.get("number")
    if not isinstance(number, int):
        return None
    advisory = alert.get("security_advisory") if isinstance(alert.get("security_advisory"), dict) else {}
    vuln = (
        alert.get("security_vulnerability")
        if isinstance(alert.get("security_vulnerability"), dict)
        else {}
    )
    dependency = alert.get("dependency") if isinstance(alert.get("dependency"), dict) else {}
    package = dependency.get("package") if isinstance(dependency.get("package"), dict) else {}
    title = (
        advisory.get("summary")
        or package.get("name")
        or f"Dependabot alert #{number}"
    )
    severity = vuln.get("severity") or advisory.get("severity")
    return {
        "number": number,
        "title": str(title),
        "severity": str(severity) if severity else None,
        "url": str(alert.get("html_url") or ""),
        "state": str(alert.get("state") or "open"),
    }


def map_codeql_alert(alert: object) -> SecurityFinding | None:
    if not isinstance(alert, dict):
        return None
    number = alert.get("number")
    if not isinstance(number, int):
        return None
    rule = alert.get("rule") if isinstance(alert.get("rule"), dict) else {}
    title = rule.get("description") or rule.get("id") or f"CodeQL alert #{number}"
    severity = rule.get("security_severity_level") or rule.get("severity")
    return {
        "number": number,
        "title": str(title),
        "severity": str(severity) if severity else None,
        "url": str(alert.get("html_url") or ""),
        "state": str(alert.get("state") or "open"),
    }


def map_pull_request(pull: object) -> PullRequestItem | None:
    if not isinstance(pull, dict):
        return None
    number = pull.get("number")
    if not isinstance(number, int):
        return None
    return {
        "number": number,
        "title": str(pull.get("title") or f"Pull request #{number}"),
        "url": str(pull.get("html_url") or ""),
        "draft": bool(pull.get("draft")),
    }


_T = TypeVar("_T")


def _map_items(payload: list[object], mapper: Callable[[object], _T | None]) -> list[_T]:
    items: list[_T] = []
    for row in payload:
        mapped = mapper(row)
        if mapped is not None:
            items.append(mapped)
    return items


def link_rel_next(link_header: str | None) -> str | None:
    if not link_header:
        return None
    match = _LINK_NEXT.search(link_header)
    return match.group(1) if match else None


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

    async def open_pull_requests(self, session: ClientSession) -> PullRequests | None:
        base = 'https://api.github.com'
        url = f'{base}/repos/{self.username}/{self.repo}/pulls'
        payload = await self._paged_list(
            session,
            url,
            allow_public_retry=True,
            empty_on_404=False,
        )
        if payload is None:
            logging.warning(
                'GitHub pull requests unavailable for %s/%s',
                self.username,
                self.repo,
            )
            return None
        return github_pull_requests_payload(
            self.username,
            self.repo,
            _map_items(payload, map_pull_request),
        )

    async def security_findings(self, session: ClientSession) -> SecurityFindings | None:
        """Open Dependabot (vulnerabilities) + CodeQL alerts with item rows."""
        if not self.token:
            return None
        base = f"https://api.github.com/repos/{self.username}/{self.repo}"
        try:
            vuln_rows, codeql_rows = await asyncio.gather(
                self._paged_list(
                    session,
                    f"{base}/dependabot/alerts",
                    allow_public_retry=False,
                    empty_on_404=True,
                ),
                self._paged_list(
                    session,
                    f"{base}/code-scanning/alerts",
                    extra={"tool_name": "CodeQL"},
                    allow_public_retry=False,
                    empty_on_404=True,
                ),
            )
        except Exception:
            logging.warning(
                "GitHub security findings unavailable for %s/%s",
                self.username,
                self.repo,
            )
            return None
        if vuln_rows is None and codeql_rows is None:
            return None
        return github_security_payload(
            self.username,
            self.repo,
            vulnerabilities=_map_items(vuln_rows or [], map_dependabot_alert),
            codeql=_map_items(codeql_rows or [], map_codeql_alert),
        )

    async def _paged_list(
        self,
        session: ClientSession,
        url: str,
        extra: dict[str, str] | None = None,
        *,
        allow_public_retry: bool,
        empty_on_404: bool,
    ) -> list[object] | None:
        """Fetch open-state list pages. None means unavailable."""
        params: dict[str, str] = {
            "state": "open",
            "per_page": _ALERT_PAGE_SIZE,
            **(extra or {}),
        }
        headers = self._auth_headers() if self.token else self._public_headers()
        next_url: str | None = url
        collected: list[object] = []
        pages = 0
        public_retried = False
        while next_url and pages < _ALERT_PAGE_CAP:
            resp = await session.get(
                next_url,
                params=params if pages == 0 else None,
                headers=headers,
            )
            status = resp.status
            link = resp.headers.get("Link")
            if (
                status in {401, 403}
                and allow_public_retry
                and self.token
                and not public_retried
                and pages == 0
            ):
                await resp.release()
                headers = self._public_headers()
                public_retried = True
                logging.warning(
                    'GitHub %s returned %s; retrying without credentials',
                    url,
                    status,
                )
                continue
            if status == 404:
                await resp.release()
                if pages == 0:
                    return [] if empty_on_404 else None
                return collected
            if status != 200:
                await resp.release()
                return None if pages == 0 else collected
            payload = await resp.json()
            if not isinstance(payload, list):
                return None if pages == 0 else collected
            collected.extend(payload)
            next_url = link_rel_next(link)
            pages += 1
            params = {}
        return collected

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
        """Stable key for 'latest per workflow'."""
        match = _DEPENDABOT_UPDATE_KEY.match(name or "")
        if match:
            return match.group("head")
        return name or ""

    def _include_run(self, run: dict) -> bool:
        name = run.get('name') or ''
        if _DEPENDABOT_UPDATE_KEY.match(name):
            return False
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
