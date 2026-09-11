#!/usr/bin/env python3
import re
from unittest import mock
from unittest.mock import MagicMock, call

import pytest
from aioresponses import aioresponses

import monitor.ci_gateway.integration_actions as available_integrations
from monitor.app import build_status_outputs
from monitor.build_monitor import BuildMonitor
from monitor.gpio.board import Board
from monitor.gpio.constants import Lights
from monitor.output.gpio_output import GpioStatusOutput
from monitor.service.aggregator_service import AggregatorService
from monitor.service.integration_mapper import IntegrationMapper


def test_build_status_outputs_applies_pin_overrides():
    build_status_outputs({
        "poll_in_seconds": 30,
        "integrations": [],
        "outputs": {"gpio": True},
        "pins": {"GREEN": 5},
    })
    assert Lights.GREEN.pin == 5


def test_build_status_outputs_skips_pins_when_gpio_disabled():
    build_status_outputs({
        "poll_in_seconds": 30,
        "integrations": [],
        "outputs": {"gpio": False},
        "pins": {"GREEN": 5},
    })
    assert Lights.GREEN.pin == 17


def test_build_status_outputs_gpio_only():
    adapters, board, websocket = build_status_outputs({
        "poll_in_seconds": 30,
        "integrations": [],
        "outputs": {"gpio": True},
    })
    assert [type(adapter).__name__ for adapter in adapters] == ["GpioStatusOutput"]
    assert board is not None
    assert websocket is None


def test_build_status_outputs_websocket_only():
    adapters, board, websocket = build_status_outputs({
        "poll_in_seconds": 30,
        "integrations": [],
        "outputs": {
            "gpio": False,
            "websocket": {"enabled": True, "host": "127.0.0.1", "port": 8080},
        },
    })
    assert [type(adapter).__name__ for adapter in adapters] == ["WebSocketStatusOutput"]
    assert board is None
    assert websocket is adapters[0]


def test_build_status_outputs_gpio_and_websocket():
    adapters, board, websocket = build_status_outputs({
        "poll_in_seconds": 30,
        "integrations": [],
        "outputs": {
            "gpio": True,
            "websocket": {"enabled": True, "host": "127.0.0.1", "port": 8080},
        },
    })
    assert [type(adapter).__name__ for adapter in adapters] == [
        "GpioStatusOutput",
        "WebSocketStatusOutput",
    ]
    assert board is not None
    assert websocket is adapters[1]


async def run(mocked_pwm):
    mocked_pwm.return_value.ChangeDutyCycle = MagicMock()
    mocked_pwm.return_value.stop = MagicMock()
    data = {
        "workflow_runs": [
            dict(id=448533827,
                 workflow_id=1001,
                 name="CI",
                 created_at="2020-12-28T09:23:57Z",
                 html_url="http://cheese.com",
                 status="in_progress",
                 conclusion=None),
            dict(id=448533828,
                 workflow_id=1001,
                 name="Another",
                 created_at="2020-12-28T09:23:57Z",
                 html_url="http://cheese.com",
                 status="completed",
                 conclusion="success")
        ]
    }
    workflows = {
        "workflows": [
            dict(id=1001, name="CI", path=".github/workflows/ci.yml", state="active"),
        ]
    }

    integrations = [dict(
        type="GITHUB",
        username="super-man",
        repo="awesome")]

    with aioresponses() as m:
        m.get(re.compile(
            r"https://api\.github\.com/repos/super-man/awesome/actions/workflows(\?.*)?"
        ), payload=workflows, status=200)
        m.get(re.compile(
            r"https://api\.github\.com/repos/super-man/awesome/actions/runs(\?.*)?"
        ), payload=data, status=200)
        aggregator = AggregatorService(
            IntegrationMapper(
                available_integrations.get_all()).get(
                integrations))

        with Board() as board:
            monitor = BuildMonitor(GpioStatusOutput(board), aggregator)
            import aiohttp
            async with aiohttp.ClientSession() as session:
                await monitor.run(session)


@pytest.mark.asyncio
@mock.patch("monitor.gpio.Mock.GPIO.PWM")
@mock.patch("monitor.gpio.Mock.GPIO.output")
async def test_blue_light(mocked_output, mocked_pwm):
    await run(mocked_pwm)
    assert call(Lights.BLUE.pin, 1) in mocked_output.call_args_list
    assert call(Lights.BLUE.pin, 0) in mocked_output.call_args_list


@pytest.mark.asyncio
@mock.patch("monitor.gpio.Mock.GPIO.PWM")
@mock.patch("monitor.gpio.Mock.GPIO.output")
async def test_pulse(mocked_output, mocked_pwm):
    await run(mocked_pwm)
    assert mocked_pwm.return_value.start.call_count == 1
    assert mocked_pwm.return_value.ChangeDutyCycle.called


@pytest.mark.asyncio
@mock.patch("monitor.gpio.Mock.GPIO.PWM")
@mock.patch("monitor.gpio.Mock.GPIO.output")
async def test_result(mocked_output, mocked_pwm):
    await run(mocked_pwm)
    assert call(Lights.GREEN.pin, 1) in mocked_output.call_args_list
    assert call(Lights.RED.pin, 0) in mocked_output.call_args_list
