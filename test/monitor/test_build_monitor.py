#!/usr/bin/env python3
from unittest.mock import AsyncMock, MagicMock, call

import aiohttp
import pytest

from monitor.build_monitor import BuildMonitor
from monitor.gpio.constants import Lights
from monitor.service.aggregator_service import Result


class TestBuildMonitor:
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        self.board = MagicMock()
        self.board.on = MagicMock()
        self.board.pulse = AsyncMock()
        self.board.off = MagicMock()
        self.aggregator = AsyncMock()
        self.aggregator.run = AsyncMock()
        self.session = AsyncMock(spec=aiohttp.ClientSession)

    @pytest.mark.asyncio
    async def test_blue_light_when_getting_results(self):
        self.aggregator.run.return_value = dict(
            is_running=True,
            status=Result.PASS)
        monitor = BuildMonitor(self.board, self.aggregator)
        assert not self.board.on.called

        await monitor.run(self.session)

        assert call(Lights.BLUE) == self.board.on.call_args_list[0]
        assert self.aggregator.run.called
        assert call(Lights.BLUE) == self.board.off.call_args_list[0]

    @pytest.mark.asyncio
    async def test_on_pass_turn_on_green(self):
        self.aggregator.run.return_value = dict(
            is_running=False,
            status=Result.PASS)
        monitor = BuildMonitor(self.board, self.aggregator)

        await monitor.run(self.session)

        assert call(Lights.PURPLE) == self.board.off.call_args_list[1]
        assert call(Lights.GREEN) == self.board.on.call_args_list[1]
        assert call(Lights.RED) == self.board.off.call_args_list[2]

    @pytest.mark.asyncio
    async def test_on_fail_turn_on_red(self):
        self.aggregator.run.return_value = dict(
            is_running=False,
            status=Result.FAIL)
        monitor = BuildMonitor(self.board, self.aggregator)

        await monitor.run(self.session)

        assert call(Lights.PURPLE) == self.board.off.call_args_list[1]
        assert call(Lights.GREEN) == self.board.off.call_args_list[2]
        assert call(Lights.RED) == self.board.on.call_args_list[1]

    @pytest.mark.asyncio
    async def test_on_unknown_turn_on_green_and_red(self):
        self.aggregator.run.return_value = dict(
            is_running=False,
            status=Result.UNKNOWN)
        monitor = BuildMonitor(self.board, self.aggregator)

        await monitor.run(self.session)

        assert call(Lights.GREEN) == self.board.on.call_args_list[1]
        assert call(Lights.RED) == self.board.on.call_args_list[2]

    @pytest.mark.asyncio
    async def test_on_connection_error_turn_on_purple(self):
        self.aggregator.run.return_value = dict(
            is_running=False,
            status=Result.CONNECTION_ERROR)
        monitor = BuildMonitor(self.board, self.aggregator)

        await monitor.run(self.session)

        assert call(Lights.PURPLE) == self.board.on.call_args_list[1]
        assert call(Lights.GREEN) == self.board.off.call_args_list[1]
        assert call(Lights.RED) == self.board.off.call_args_list[2]

    @pytest.mark.asyncio
    async def test_pulse_when_running(self):
        self.aggregator.run.return_value = dict(
            is_running=True,
            status=Result.PASS)
        monitor = BuildMonitor(self.board, self.aggregator)

        await monitor.run(self.session)

        assert call(Lights.GREEN) == self.board.on.call_args_list[1]
        assert call(Lights.YELLOW) == self.board.pulse.call_args_list[0]

    @pytest.mark.asyncio
    async def test_do_not_pulse_when_not_running(self):
        self.aggregator.run.return_value = dict(
            is_running=False,
            status=Result.PASS)
        monitor = BuildMonitor(self.board, self.aggregator)

        await monitor.run(self.session)

        assert call(Lights.PURPLE) == self.board.off.call_args_list[1]
        assert call(Lights.GREEN) == self.board.on.call_args_list[1]
        assert call(Lights.RED) == self.board.off.call_args_list[2]
        assert not self.board.pulse.called

    @pytest.mark.asyncio
    async def test_blue_light_turns_off_when_aggregator_fails(self):
        self.aggregator.run.side_effect = RuntimeError('boom')
        monitor = BuildMonitor(self.board, self.aggregator)

        with pytest.raises(RuntimeError):
            await monitor.run(self.session)

        assert call(Lights.BLUE) == self.board.on.call_args_list[0]
        assert call(Lights.BLUE) == self.board.off.call_args_list[0]
