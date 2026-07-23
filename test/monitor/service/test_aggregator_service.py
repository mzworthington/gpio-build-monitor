#!/usr/bin/env python3


import aiohttp
import pytest

from monitor.ci_gateway.constants import CiResult, IntegrationType
from monitor.service.aggregator_service import AggregatorService, Result


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
            dict(status=CiResult.PASS, type=IntegrationType.GITHUB, vcs='', id='', name='', start=''),
        ]),
        StubIntegration('c', 'd', IntegrationType.GITHUB, [
            dict(status=CiResult.FAIL, type=IntegrationType.GITHUB, vcs='', id='', name='', start=''),
        ]),
    ]
    async with aiohttp.ClientSession() as session:
        result = await AggregatorService(integrations).run(session)
    assert result["status"] == Result.FAIL


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
