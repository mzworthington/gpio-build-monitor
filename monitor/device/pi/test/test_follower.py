#!/usr/bin/env python3

import socket
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientSession, web
from gpio_pi.follower import follow_api
from gpio_pi.status import Result


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.asyncio
async def test_follow_api_publishes_hosted_status_onto_gpio_output():
    async def status(_request):
        return web.json_response({
            "status": "PASS",
            "is_running": True,
            "fetching": False,
            "builds": [],
        })

    async def ws_handler(request):
        socket = web.WebSocketResponse()
        await socket.prepare(request)
        await socket.send_json({
            "status": "PASS",
            "is_running": True,
            "fetching": False,
        })
        await socket.close()
        return socket

    app = web.Application()
    app.router.add_get("/api/status", status)
    app.router.add_get("/api/ws", ws_handler)
    port = _free_port()
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", port).start()
    output = MagicMock()
    output.begin_fetch = AsyncMock()
    output.end_fetch = AsyncMock()
    output.publish = AsyncMock()
    try:
        async with ClientSession() as session:
            await follow_api(f"http://127.0.0.1:{port}", output, session, once=True)
    finally:
        await runner.cleanup()

    output.publish.assert_awaited()
    args, kwargs = output.publish.await_args
    assert args[0] is Result.PASS
    assert kwargs["is_running"] is True
