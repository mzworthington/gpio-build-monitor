#!/usr/bin/env python3

from unittest import mock

import pytest
from gpio_pi.gpio.board import Board
from gpio_pi.gpio.constants import Lights, reset_pins


def _pin_map() -> dict[str, int]:
    return {light.name: light.pin for light in Lights}


@pytest.fixture(autouse=True)
def _reset_gpio_pins():
    reset_pins()
    yield
    reset_pins()


class TestBoard:
    @mock.patch("gpio_pi.gpio.Mock.GPIO.setwarnings")
    def test_warnings_are_disabled(self, mocked):
        with Board():
            assert mocked.called
        args, kwargs = mocked.call_args
        assert args[0] is False

    @mock.patch("gpio_pi.gpio.Mock.GPIO.setup")
    def test_pin_overrides_apply_when_board_starts(self, mocked):
        mocked.setup.return_value = None
        defaults = _pin_map()
        board = Board(pin_overrides={"GREEN": 5, "RED": 6})

        assert _pin_map() == defaults

        with board:
            assert Lights.GREEN.pin == 5
            assert Lights.RED.pin == 6
            assert Lights.YELLOW.pin == defaults["YELLOW"]
            mocked.assert_any_call(5, 0, initial=0)
            mocked.assert_any_call(6, 0, initial=0)
