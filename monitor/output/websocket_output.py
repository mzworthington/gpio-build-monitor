#!/usr/bin/env python3

import asyncio
import json
import logging
import time
from collections.abc import Sequence
from pathlib import Path

from aiohttp import WSMsgType, web

from monitor.service.aggregator_service import BuildDetail, Result

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class WebSocketStatusOutput:
    """Broadcasts CI status to browser clients over WebSockets."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        web_dir: Path | None = None,
        poll_in_seconds: int = 30,
    ):
        self._host = host
        self._port = port
        self._web_dir = web_dir or WEB_DIR
        self._poll_in_seconds = poll_in_seconds
        self._clients: set[web.WebSocketResponse] = set()
        self._fetching = False
        self._status = Result.NONE
        self._is_running = False
        self._builds: list[BuildDetail] = []
        self._last_checked_at: float | None = None
        self._next_check_at: float | None = None
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    async def __aenter__(self) -> "WebSocketStatusOutput":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/ws", self._websocket_handler)
        app.router.add_get("/status", self._status_handler)
        if self._web_dir.is_dir():
            app.router.add_get("/", self._index_handler)
            for name, content_type in (
                ("app.js", "application/javascript"),
                ("countdown.js", "application/javascript"),
                ("styles.css", "text/css"),
                ("favicon.svg", "image/svg+xml"),
                ("favicon.png", "image/png"),
                ("favicon-32.png", "image/png"),
                ("apple-touch-icon.png", "image/png"),
                ("logo.svg", "image/svg+xml"),
                ("logo.png", "image/png"),
                ("icon-192.png", "image/png"),
                ("icon-512.png", "image/png"),
                ("social-share.png", "image/png"),
                ("manifest.webmanifest", "application/manifest+json"),
            ):
                if (self._web_dir / name).is_file():
                    app.router.add_get(f"/{name}", self._asset_handler(name, content_type))
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()
        logging.info("WebSocket status UI listening on http://%s:%s", self._host, self._port)

    async def stop(self) -> None:
        clients = list(self._clients)
        self._clients.clear()
        await asyncio.gather(
            *(client.close() for client in clients),
            return_exceptions=True,
        )
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
            self._site = None

    async def begin_fetch(self) -> None:
        # Mid-poll signal for the fetch light / dial spinner only.
        # Keep next_check_at so the countdown does not reset.
        self._fetching = True
        await self._broadcast(self._payload())

    async def end_fetch(self) -> None:
        self._fetching = False

    async def publish(
        self,
        status: Result,
        *,
        is_running: bool,
        builds: Sequence[BuildDetail] | None = None,
    ) -> None:
        self._status = status
        self._is_running = is_running
        self._builds = list(builds or [])
        self._fetching = False
        self._last_checked_at = time.time()
        self._next_check_at = self._last_checked_at + self._poll_in_seconds
        await self._broadcast(self._payload())

    def _payload(self) -> dict:
        return {
            "type": "status",
            "fetching": self._fetching,
            "status": self._status.value,
            "is_running": self._is_running,
            "builds": self._builds,
            "poll_in_seconds": self._poll_in_seconds,
            "last_checked_at": self._last_checked_at,
            "next_check_at": self._next_check_at,
        }

    async def _status_handler(self, _request: web.Request) -> web.Response:
        return web.json_response(self._payload(), headers={"Cache-Control": "no-store"})

    async def _index_handler(self, _request: web.Request) -> web.FileResponse:
        return web.FileResponse(self._web_dir / "index.html")

    def _asset_handler(self, filename: str, content_type: str):
        async def handler(_request: web.Request) -> web.FileResponse:
            return web.FileResponse(
                self._web_dir / filename,
                headers={"Content-Type": content_type},
            )

        return handler

    async def _websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        self._clients.add(ws)
        logging.debug("WebSocket client connected (%s total)", len(self._clients))
        try:
            await ws.send_json(self._payload())
            async for msg in ws:
                if msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                    break
        finally:
            self._clients.discard(ws)
            logging.debug("WebSocket client disconnected (%s total)", len(self._clients))
        return ws

    async def _broadcast(self, payload: dict) -> None:
        if not self._clients:
            return
        message = json.dumps(payload)
        stale: list[web.WebSocketResponse] = []
        for client in list(self._clients):
            if client.closed:
                stale.append(client)
                continue
            try:
                await client.send_str(message)
            except ConnectionResetError:
                stale.append(client)
            except Exception:
                logging.exception("Failed to send status to WebSocket client")
                stale.append(client)
        for client in stale:
            self._clients.discard(client)
