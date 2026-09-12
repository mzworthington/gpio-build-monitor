#!/usr/bin/env python3


import aiohttp
import pytest
from monitor.ci_gateway.constants import CiResult, IntegrationType
from monitor.service.aggregator_service import AggregatorService, Result, repo_summaries


class StubIntegration:
    def __init__(
        self,
        username,
        repo,
        integration_type,
        results=None,
        error=None,
        prs=None,
        pr_error=None,
        security=None,
        security_error=None,
    ):
        self.username = username
        self.repo = repo
        self.integration_type = integration_type
        self.results = results or []
        self.error = error
        self.prs = prs
        self.pr_error = pr_error
        self.security = security
        self.security_error = security_error

    def get_type(self):
        return self.integration_type

    async def get_latest(self, session):
        if self.error:
            raise self.error
        return self.results

    async def open_pull_requests(self, session):
        if self.pr_error:
            raise self.pr_error
        return self.prs

    async def security_findings(self, session):
        if self.security_error:
            raise self.security_error
        return self.security


@pytest.mark.asyncio
async def test_waiting_counts_as_in_progress():
    integrations = [
        StubIntegration('a', 'b', IntegrationType.GITHUB, [
            dict(status=CiResult.PASS, type=IntegrationType.GITHUB, vcs='', id='', name='', start=''),
        ]),
        StubIntegration('c', 'd', IntegrationType.GITHUB, [
            dict(status=CiResult.WAITING, type=IntegrationType.GITHUB, vcs='', id='', name='', start=''),
        ]),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["is_running"] is True
    assert result["status"] == Result.PASS


@pytest.mark.asyncio
async def test_waiting_only_rollups_to_waiting():
    integrations = [
        StubIntegration('c', 'd', IntegrationType.GITHUB, [
            dict(status=CiResult.WAITING, type=IntegrationType.GITHUB, vcs='', id='', name='', start=''),
        ]),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["is_running"] is True
    assert result["status"] == Result.WAITING


@pytest.mark.asyncio
async def test_approval_elevates_status():
    integrations = [
        StubIntegration('a', 'b', IntegrationType.GITHUB, [
            dict(status=CiResult.PASS, type=IntegrationType.GITHUB, vcs='', id='', name='', start=''),
        ]),
        StubIntegration('c', 'd', IntegrationType.GITHUB, [
            dict(status=CiResult.APPROVAL, type=IntegrationType.GITHUB, vcs='', id='', name='Deploy', start=''),
        ]),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["status"] == Result.APPROVAL


@pytest.mark.asyncio
async def test_is_running():
    integrations = [
        StubIntegration('a', 'b', IntegrationType.GITHUB, [
            dict(status=CiResult.PASS, type=IntegrationType.GITHUB, vcs='', id='', name='', start=''),
        ]),
        StubIntegration('c', 'd', IntegrationType.GITHUB, [
            dict(status=CiResult.RUNNING, type=IntegrationType.GITHUB, vcs='', id='', name='', start=''),
        ]),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["is_running"] is True


@pytest.mark.asyncio
async def test_is_not_running():
    integrations = [
        StubIntegration('a', 'b', IntegrationType.GITHUB, [
            dict(status=CiResult.PASS, type=IntegrationType.GITHUB, vcs='', id='', name='', start=''),
        ]),
        StubIntegration('c', 'd', IntegrationType.GITHUB, [
            dict(status=CiResult.FAIL, type=IntegrationType.GITHUB, vcs='', id='', name='', start=''),
        ]),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["is_running"] is False


@pytest.mark.asyncio
async def test_contains_failed():
    integrations = [
        StubIntegration('a', 'b', IntegrationType.GITHUB, [
            dict(status=CiResult.PASS, type=IntegrationType.GITHUB, vcs='', id='', name='CI', start=''),
        ]),
        StubIntegration('c', 'd', IntegrationType.GITHUB, [
            dict(
                status=CiResult.FAIL,
                type=IntegrationType.GITHUB,
                vcs='https://example.com/fail',
                id='',
                name='CI',
                start='',
            ),
        ]),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["status"] == Result.FAIL
    assert result["builds"] == [
        {
            "repo": "a/b",
            "workflow": "CI",
            "status": "PASS",
            "url": "",
            "pull_requests": None,
            "security": None,
        },
        {
            "repo": "c/d",
            "workflow": "CI",
            "status": "FAIL",
            "url": "https://example.com/fail",
            "pull_requests": None,
            "security": None,
        },
    ]


@pytest.mark.asyncio
async def test_all_pass():
    integrations = [
        StubIntegration('a', 'b', IntegrationType.GITHUB, [
            dict(status=CiResult.PASS, type=IntegrationType.GITHUB, vcs='', id='', name='', start=''),
        ]),
        StubIntegration('c', 'd', IntegrationType.GITHUB, [
            dict(status=CiResult.RUNNING, type=IntegrationType.GITHUB, vcs='', id='', name='', start=''),
        ]),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["status"] == Result.PASS


@pytest.mark.asyncio
async def test_no_results():
    integrations = [
        StubIntegration('a', 'b', IntegrationType.GITHUB, [
            dict(status=CiResult.RUNNING, type=IntegrationType.GITHUB, vcs='', id='', name='', start=''),
        ]),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["status"] == Result.RUNNING


@pytest.mark.asyncio
async def test_connection_error_is_reported():
    integrations = [
        StubIntegration('a', 'b', IntegrationType.GITHUB, error=RuntimeError('offline')),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["status"] == Result.CONNECTION_ERROR


@pytest.mark.asyncio
async def test_fail_beats_connection_error():
    integrations = [
        StubIntegration('a', 'b', IntegrationType.GITHUB, [
            dict(status=CiResult.FAIL, type=IntegrationType.GITHUB, vcs='', id='', name='CI', start=''),
        ]),
        StubIntegration('c', 'd', IntegrationType.GITHUB, error=RuntimeError('offline')),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["status"] == Result.FAIL


@pytest.mark.asyncio
async def test_unresolved_settled_status_is_unknown():
    integrations = [
        StubIntegration('a', 'b', IntegrationType.GITHUB, [
            dict(status=CiResult.UNKNOWN, type=IntegrationType.GITHUB, vcs='', id='', name='CI', start=''),
        ]),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["status"] == Result.UNKNOWN


@pytest.mark.asyncio
async def test_cancelled_pass_does_not_make_mixed():
    """Cancelled workflows map to PASS and must not produce UNKNOWN/Mixed."""
    from monitor.ci_gateway.github import GitHubAction

    cancelled = GitHubAction.map_result({
        "id": 1,
        "status": "completed",
        "conclusion": "cancelled",
        "created_at": "2020-12-28T09:23:57Z",
        "html_url": "https://example.com",
        "name": "Pulumi",
    })
    integrations = [
        StubIntegration('a', 'b', IntegrationType.GITHUB, [
            dict(status=CiResult.PASS, type=IntegrationType.GITHUB, vcs='', id='', name='CI', start=''),
        ]),
        StubIntegration('mzworthington', 'edge-dns', IntegrationType.GITHUB, [
            dict(
                status=cancelled["status"],
                type=IntegrationType.GITHUB,
                vcs=cancelled["vcs"],
                id=cancelled["id"],
                name=cancelled["name"],
                start=cancelled["start"],
            ),
        ]),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["status"] == Result.PASS


def test_repo_summaries_groups_workflows_and_worst_status():
    summaries = repo_summaries([
        {
            "repo": "mzworthington/archlens",
            "workflow": "CI",
            "status": "PASS",
            "url": "https://github.com/mzworthington/archlens/actions/1",
        },
        {
            "repo": "mzworthington/edge-dns",
            "workflow": "Pulumi",
            "status": "PASS",
            "url": "https://github.com/mzworthington/edge-dns/actions/1",
        },
        {
            "repo": "mzworthington/archlens",
            "workflow": "Deploy",
            "status": "FAIL",
            "url": "https://github.com/mzworthington/archlens/actions/2",
        },
    ])

    assert summaries == [
        {
            "repo": "mzworthington/archlens",
            "status": "FAIL",
            "workflow_count": 2,
            "is_running": False,
            "url": "https://github.com/mzworthington/archlens",
            "pull_requests": None,
            "security": None,
            "workflows": [
                {
                    "repo": "mzworthington/archlens",
                    "workflow": "CI",
                    "status": "PASS",
                    "url": "https://github.com/mzworthington/archlens/actions/1",
                },
                {
                    "repo": "mzworthington/archlens",
                    "workflow": "Deploy",
                    "status": "FAIL",
                    "url": "https://github.com/mzworthington/archlens/actions/2",
                },
            ],
        },
        {
            "repo": "mzworthington/edge-dns",
            "status": "PASS",
            "workflow_count": 1,
            "is_running": False,
            "url": "https://github.com/mzworthington/edge-dns",
            "pull_requests": None,
            "security": None,
            "workflows": [
                {
                    "repo": "mzworthington/edge-dns",
                    "workflow": "Pulumi",
                    "status": "PASS",
                    "url": "https://github.com/mzworthington/edge-dns/actions/1",
                },
            ],
        },
    ]


@pytest.mark.asyncio
async def test_github_pull_requests_do_not_change_aggregate_status():
    pulls = {
        "count": 3,
        "url": "https://github.com/a/b/pulls",
        "items": [
            {
                "number": 1,
                "title": "One",
                "url": "https://github.com/a/b/pull/1",
                "draft": False,
            },
            {
                "number": 2,
                "title": "Two",
                "url": "https://github.com/a/b/pull/2",
                "draft": True,
            },
            {
                "number": 3,
                "title": "Three",
                "url": "https://github.com/a/b/pull/3",
                "draft": False,
            },
        ],
    }
    integrations = [
        StubIntegration(
            'a',
            'b',
            IntegrationType.GITHUB,
            [
                dict(
                    status=CiResult.PASS,
                    type=IntegrationType.GITHUB,
                    vcs='',
                    id='',
                    name='CI',
                    start='',
                ),
            ],
            prs=pulls,
        ),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["status"] == Result.PASS
    assert result["builds"][0]["pull_requests"] == pulls


@pytest.mark.asyncio
async def test_github_security_findings_do_not_change_aggregate_status():
    findings = {
        "count": 4,
        "url": "https://github.com/a/b/security",
        "vulnerabilities": {
            "count": 3,
            "url": "https://github.com/a/b/security/dependabot",
            "items": [],
        },
        "codeql": {
            "count": 1,
            "url": "https://github.com/a/b/security/code-scanning",
            "items": [
                {
                    "number": 9,
                    "title": "SQL injection",
                    "severity": "high",
                    "url": "https://github.com/a/b/security/code-scanning/9",
                    "state": "open",
                }
            ],
        },
    }
    integrations = [
        StubIntegration(
            'a',
            'b',
            IntegrationType.GITHUB,
            [
                dict(
                    status=CiResult.PASS,
                    type=IntegrationType.GITHUB,
                    vcs='',
                    id='',
                    name='CI',
                    start='',
                ),
            ],
            security=findings,
        ),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["status"] == Result.PASS
    assert result["builds"][0]["security"] == findings


@pytest.mark.asyncio
async def test_failed_security_fetch_leaves_workflows_intact():
    integrations = [
        StubIntegration(
            'a',
            'b',
            IntegrationType.GITHUB,
            [
                dict(
                    status=CiResult.PASS,
                    type=IntegrationType.GITHUB,
                    vcs='',
                    id='',
                    name='CI',
                    start='',
                ),
            ],
            security_error=RuntimeError('security down'),
        ),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["status"] == Result.PASS
    assert result["builds"][0]["security"] is None


@pytest.mark.asyncio
async def test_failed_pr_fetch_leaves_workflows_intact():
    integrations = [
        StubIntegration(
            'a',
            'b',
            IntegrationType.GITHUB,
            [
                dict(
                    status=CiResult.PASS,
                    type=IntegrationType.GITHUB,
                    vcs='',
                    id='',
                    name='CI',
                    start='',
                ),
            ],
            pr_error=RuntimeError('prs down'),
        ),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["status"] == Result.PASS
    assert result["builds"][0]["pull_requests"] is None


def test_repo_summaries_keeps_github_pull_requests_over_circle_null():
    pulls = {
        "count": 2,
        "url": "https://github.com/acme/web/pulls",
        "items": [
            {
                "number": 7,
                "title": "Ready",
                "url": "https://github.com/acme/web/pull/7",
                "draft": False,
            },
            {
                "number": 8,
                "title": "Draft",
                "url": "https://github.com/acme/web/pull/8",
                "draft": True,
            },
        ],
    }
    summaries = repo_summaries([
        {
            "repo": "acme/web",
            "workflow": "CI",
            "status": "PASS",
            "url": "https://github.com/acme/web/actions/1",
            "pull_requests": pulls,
        },
        {
            "repo": "acme/web",
            "workflow": "build",
            "status": "PASS",
            "url": "https://github.com/acme/web",
            "pull_requests": None,
        },
    ])
    assert summaries[0]["pull_requests"] == pulls


def test_repo_summaries_keeps_github_security_over_circle_null():
    findings = {
        "count": 2,
        "url": "https://github.com/acme/web/security",
        "vulnerabilities": {
            "count": 2,
            "url": "https://github.com/acme/web/security/dependabot",
            "items": [],
        },
        "codeql": {
            "count": 0,
            "url": "https://github.com/acme/web/security/code-scanning",
            "items": [],
        },
    }
    summaries = repo_summaries([
        {
            "repo": "acme/web",
            "workflow": "CI",
            "status": "PASS",
            "url": "https://github.com/acme/web/actions/1",
            "security": findings,
        },
        {
            "repo": "acme/web",
            "workflow": "build",
            "status": "PASS",
            "url": "https://github.com/acme/web",
            "security": None,
        },
    ])
    assert summaries[0]["security"] == findings


def test_rollup_status_is_the_ci_result_enum():
    assert Result is CiResult


def test_unused_build_status_rollup_is_gone():
    import monitor.service.aggregator_service as aggregator

    assert not hasattr(aggregator, "get_status")
