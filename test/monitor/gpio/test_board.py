#!/usr/bin/env python3

from unittest import mock

import pytest

from monitor.gpio.board import Board
from monitor.gpio.constants import Lights, reset_pins


@pytest.fixture(autouse=True)
def _reset_gpio_pins():
    reset_pins()
    yield
    reset_pins()


class TestBoard:
    @mock.patch('monitor.gpio.Mock.GPIO.setwarnings')
    def test_warnings_are_disabled(self, mocked):
        with Board():
            assert mocked.called
        args, kwargs = mocked.call_args
        assert args[0] is False

    @mock.patch('monitor.gpio.Mock.GPIO.cleanup')
    def test_cleanup_is_called(self, mocked):
        with Board():
            assert not mocked.called
        assert mocked.called

    @mock.patch('monitor.gpio.Mock.GPIO.setup')
    def test_pin_setup(self, mocked):
        mocked.setup.return_value = None
        with Board():
            calls = [mock.call(Lights.GREEN.pin, 0, initial=0),
                     mock.call(Lights.YELLOW.pin, 0, initial=0),
                     mock.call(Lights.RED.pin, 0, initial=0),
                     mock.call(Lights.BLUE.pin, 0, initial=0),
                     mock.call(Lights.PURPLE.pin, 0, initial=0)]
            mocked.assert_has_calls(calls, any_order=True)

    @mock.patch('monitor.gpio.Mock.GPIO.output')
    def test_turn_on(self, mocked):
        with Board() as board:
            board.on(Lights.BLUE)
            mocked.assert_called_with(Lights.BLUE.pin, 1)

    @mock.patch('monitor.gpio.Mock.GPIO.output')
    def test_turn_off(self, mocked):
        with Board() as board:
            board.off(Lights.BLUE)
            mocked.assert_called_with(Lights.BLUE.pin, 0)

    @pytest.mark.asyncio
    @mock.patch('monitor.gpio.Mock.GPIO.PWM')
    async def test_pulse(self, mocked):
        import asyncio
        mocked.return_value.ChangeDutyCycle = mock.MagicMock()
        mocked.return_value.stop = mock.MagicMock()
        with Board() as board:
            await board.pulse(Lights.PURPLE)
            await asyncio.sleep(1)
            mocked.assert_called_with(Lights.PURPLE.pin, 100)
            board.off(Lights.PURPLE)
            assert mocked.return_value.stop.called
            assert mocked.return_value.ChangeDutyCycle.called

    @pytest.mark.asyncio
    @mock.patch('monitor.gpio.Mock.GPIO.PWM')
    async def test_pulse_not_called_if_active(self, mocked):
        import asyncio
        mocked.return_value.start = mock.MagicMock()
        mocked.return_value.stop = mock.MagicMock()
        with Board() as board:
            assert mocked.return_value.start.call_count == 0
            await board.pulse(Lights.BLUE)
            await asyncio.sleep(1)
            assert mocked.return_value.start.call_count == 1
            await board.pulse(Lights.BLUE)
            await asyncio.sleep(1)
            assert mocked.return_value.start.call_count == 1
            board.off(Lights.BLUE)
