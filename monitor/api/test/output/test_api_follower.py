#!/usr/bin/env python3

import socket
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientSession
from monitor.output.api_follower import follow_api
from monitor.output.websocket_output import WebSocketStatusOutput
from monitor.service.aggregator_service import Result


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.asyncio
async def test_follow_api_publishes_websocket_status_onto_gpio_output():
    port = _free_port()
    output = MagicMock()
    output.begin_fetch = AsyncMock()
    output.end_fetch = AsyncMock()
    output.publish = AsyncMock()

    async with WebSocketStatusOutput(host="127.0.0.1", port=port, poll_in_seconds=12) as hub:
        await hub.publish(Result.PASS, is_running=True)
        async with ClientSession() as session:
            await follow_api(f"http://127.0.0.1:{port}", output, session, once=True)

    output.publish.assert_awaited()
    args, kwargs = output.publish.await_args
    assert args[0] is Result.PASS
    assert kwargs["is_running"] is True
