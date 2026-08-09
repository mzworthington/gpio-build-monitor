#!/usr/bin/env python3


import aiohttp
import pytest

from monitor.ci_gateway.constants import CiResult, IntegrationType
from monitor.service.aggregator_service import AggregatorService, Result, repo_summaries


class StubIntegration:
    def __init__(self, username, repo, integration_type, results=None, error=None):
        self.username = username
        self.repo = repo
        self.integration_type = integration_type
        self.results = results or []
        self.error = error

    def get_type(self):
        return self.integration_type

    async def get_latest(self, session):
        if self.error:
            raise self.error
        return self.results


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
        },
        {
            "repo": "c/d",
            "workflow": "CI",
            "status": "FAIL",
            "url": "https://example.com/fail",
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
    assert result["status"] == Result.NONE


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
