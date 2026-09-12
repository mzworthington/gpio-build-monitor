#!/usr/bin/env python3

from unittest import mock

from gpio_pi.gpio.board import Board


class TestBoard:
    @mock.patch("gpio_pi.gpio.Mock.GPIO.setwarnings")
    def test_warnings_are_disabled(self, mocked):
        with Board():
            assert mocked.called
        args, kwargs = mocked.call_args
        assert args[0] is False
