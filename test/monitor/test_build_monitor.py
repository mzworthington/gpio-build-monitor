#!/usr/bin/env python3
from unittest.mock import AsyncMock

import aiohttp
import pytest

from monitor.build_monitor import BuildMonitor
from monitor.service.aggregator_service import Result


class TestBuildMonitor:
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        self.output = AsyncMock()
        self.aggregator = AsyncMock()
        self.aggregator.run = AsyncMock()
        self.session = AsyncMock(spec=aiohttp.ClientSession)

    @pytest.mark.asyncio
    async def test_begin_and_end_fetch_around_aggregator(self):
        self.aggregator.run.return_value = dict(
            is_running=True,
            status=Result.PASS,
            builds=[],
        )
        monitor = BuildMonitor(self.output, self.aggregator)

        await monitor.run(self.session)

        self.output.begin_fetch.assert_awaited_once()
        assert self.aggregator.run.called
        self.output.end_fetch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_publishes_pass_status(self):
        builds = [{
            "repo": "org/repo",
            "workflow": "CI",
            "status": "PASS",
            "url": "https://example.com",
        }]
        self.aggregator.run.return_value = dict(
            is_running=False,
            status=Result.PASS,
            builds=builds,
        )
        monitor = BuildMonitor(self.output, self.aggregator)

        await monitor.run(self.session)

        self.output.publish.assert_awaited_once_with(
            Result.PASS, is_running=False, builds=builds)

    @pytest.mark.asyncio
    async def test_publishes_fail_status(self):
        self.aggregator.run.return_value = dict(
            is_running=False,
            status=Result.FAIL,
            builds=[],
        )
        monitor = BuildMonitor(self.output, self.aggregator)

        await monitor.run(self.session)

        self.output.publish.assert_awaited_once_with(
            Result.FAIL, is_running=False, builds=[])

    @pytest.mark.asyncio
    async def test_publishes_running_flag(self):
        self.aggregator.run.return_value = dict(
            is_running=True,
            status=Result.PASS,
            builds=[],
        )
        monitor = BuildMonitor(self.output, self.aggregator)

        await monitor.run(self.session)

        self.output.publish.assert_awaited_once_with(
            Result.PASS, is_running=True, builds=[])

    @pytest.mark.asyncio
    async def test_end_fetch_when_aggregator_fails(self):
        self.aggregator.run.side_effect = RuntimeError("boom")
        monitor = BuildMonitor(self.output, self.aggregator)

        with pytest.raises(RuntimeError):
            await monitor.run(self.session)

        self.output.begin_fetch.assert_awaited_once()
        self.output.end_fetch.assert_awaited_once()
        self.output.publish.assert_not_awaited()
