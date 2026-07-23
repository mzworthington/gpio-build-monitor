#!/usr/bin/env python3
from unittest import mock
from unittest.mock import MagicMock, call

import pytest
from aioresponses import aioresponses

import monitor.ci_gateway.integration_actions as available_integrations
from monitor.build_monitor import BuildMonitor
from monitor.gpio.board import Board
from monitor.gpio.constants import Lights
from monitor.service.aggregator_service import AggregatorService
from monitor.service.integration_mapper import IntegrationMapper


async def run(mocked_pwm):
    mocked_pwm.return_value.ChangeDutyCycle = MagicMock()
    mocked_pwm.return_value.stop = MagicMock()
    data = {
        "workflow_runs": [
            dict(id=448533827,
                 name="CI",
                 created_at="2020-12-28T09:23:57Z",
                 html_url="http://cheese.com",
                 status="in_progress",
                 conclusion=None),
            dict(id=448533828,
                 name="Another",
                 created_at="2020-12-28T09:23:57Z",
                 html_url="http://cheese.com",
                 status="completed",
                 conclusion="success")
        ]
    }

    integrations = [dict(
        type='GITHUB',
        username='super-man',
        repo='awesome')]

    with aioresponses() as m:
        m.get('https://api.github.com/repos/super-man/awesome/actions/runs',
              payload=data, status=200)
        aggregator = AggregatorService(
            IntegrationMapper(
                available_integrations.get_all()).get(
                integrations))

        with Board() as board:
            monitor = BuildMonitor(board, aggregator)
            import aiohttp
            async with aiohttp.ClientSession() as session:
                await monitor.run(session)


@pytest.mark.asyncio
@mock.patch('monitor.gpio.Mock.GPIO.PWM')
@mock.patch('monitor.gpio.Mock.GPIO.output')
async def test_blue_light(mocked_output, mocked_pwm):
    await run(mocked_pwm)
    assert call(Lights.BLUE.pin, 1) in mocked_output.call_args_list
    assert call(Lights.BLUE.pin, 0) in mocked_output.call_args_list


@pytest.mark.asyncio
@mock.patch('monitor.gpio.Mock.GPIO.PWM')
@mock.patch('monitor.gpio.Mock.GPIO.output')
async def test_pulse(mocked_output, mocked_pwm):
    await run(mocked_pwm)
    assert mocked_pwm.return_value.start.call_count == 1
    assert mocked_pwm.return_value.ChangeDutyCycle.called


@pytest.mark.asyncio
@mock.patch('monitor.gpio.Mock.GPIO.PWM')
@mock.patch('monitor.gpio.Mock.GPIO.output')
async def test_result(mocked_output, mocked_pwm):
    await run(mocked_pwm)
    assert call(Lights.GREEN.pin, 1) in mocked_output.call_args_list
    assert call(Lights.RED.pin, 0) in mocked_output.call_args_list
