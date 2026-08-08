#!/usr/bin/env python3

import asyncio
import json
import socket

import pytest
from aiohttp import ClientSession, web

from monitor.client.app import HtmlStatusClient, normalize_ws_url


def test_normalize_ws_url_from_http():
    assert normalize_ws_url("http://127.0.0.1:8080") == "ws://127.0.0.1:8080/ws"
    assert normalize_ws_url("https://example.com/") == "wss://example.com/ws"
    assert normalize_ws_url("ws://127.0.0.1:8080/ws") == "ws://127.0.0.1:8080/ws"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.asyncio
async def test_html_client_renders_status_from_websocket():
    payload = {
        "type": "status",
        "fetching": False,
        "status": "FAIL",
        "is_running": False,
        "builds": [{
            "repo": "mzworthington/edge-dns",
            "workflow": "Pulumi",
            "status": "FAIL",
            "url": "https://example.com/run",
        }],
    }
    server_port = _free_port()
    client_port = _free_port()

    async def ws_handler(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_str(json.dumps(payload))
        try:
            async for _ in ws:
                pass
        finally:
            await ws.close()
        return ws

    app = web.Application()
    app.router.add_get("/ws", ws_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", server_port).start()

    try:
        async with HtmlStatusClient(
            f"ws://127.0.0.1:{server_port}/ws",
            host="127.0.0.1",
            port=client_port,
            refresh_seconds=0,
        ):
            html = ""
            async with ClientSession() as session:
                for _ in range(50):
                    async with session.get(f"http://127.0.0.1:{client_port}/") as response:
                        assert response.status == 200
                        html = await response.text()
                        if "At least one build failed" in html:
                            break
                    await asyncio.sleep(0.05)

            assert "At least one build failed" in html
            assert "mzworthington/" in html
            assert "edge-dns" in html
            assert "Pulumi" in html
            assert 'data-state="live"' in html
            assert "app.js" in html
    finally:
        await runner.cleanup()
