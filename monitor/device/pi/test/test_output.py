#!/usr/bin/env python3
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from gpio_pi.gpio.constants import Lights
from gpio_pi.output import GpioStatusOutput
from gpio_pi.status import Result


class TestGpioStatusOutput:
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        self.board = MagicMock()
        self.board.on = MagicMock()
        self.board.off = MagicMock()
        self.board.pulse = AsyncMock()
        self.output = GpioStatusOutput(self.board)

    @pytest.mark.asyncio
    async def test_pass_turns_on_green(self):
        await self.output.publish(Result.PASS, is_running=False)

        assert call(Lights.PURPLE) == self.board.off.call_args_list[0]
        assert call(Lights.GREEN) == self.board.on.call_args_list[0]
        assert call(Lights.RED) == self.board.off.call_args_list[1]
        assert call(Lights.YELLOW) == self.board.off.call_args_list[2]
        assert not self.board.pulse.called

    @pytest.mark.asyncio
    async def test_fail_turns_on_red(self):
        await self.output.publish(Result.FAIL, is_running=False)

        assert call(Lights.GREEN) == self.board.off.call_args_list[1]
        assert call(Lights.RED) == self.board.on.call_args_list[0]

    @pytest.mark.asyncio
    async def test_unknown_turns_on_red_only(self):
        await self.output.publish(Result.UNKNOWN, is_running=False)

        assert call(Lights.GREEN) == self.board.off.call_args_list[1]
        assert call(Lights.RED) == self.board.on.call_args_list[0]

    @pytest.mark.asyncio
    async def test_connection_error_turns_on_purple(self):
        await self.output.publish(Result.CONNECTION_ERROR, is_running=False)

        assert call(Lights.PURPLE) == self.board.on.call_args_list[0]
        assert call(Lights.GREEN) == self.board.off.call_args_list[0]
        assert call(Lights.RED) == self.board.off.call_args_list[1]

    @pytest.mark.asyncio
    async def test_approval_pulses_yellow(self):
        await self.output.publish(Result.APPROVAL, is_running=False)

        assert call(Lights.GREEN) == self.board.off.call_args_list[1]
        assert call(Lights.RED) == self.board.off.call_args_list[2]
        self.board.pulse.assert_awaited_once_with(Lights.YELLOW)

    @pytest.mark.asyncio
    async def test_pulse_when_running(self):
        await self.output.publish(Result.PASS, is_running=True)

        self.board.pulse.assert_awaited_once_with(Lights.YELLOW)
