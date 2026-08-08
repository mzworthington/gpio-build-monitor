#!/usr/bin/env python3

import asyncio
import json
import logging
from pathlib import Path

from aiohttp import ClientSession, WSMsgType, web

from monitor.client.render import StatusPageRenderer
from monitor.service.aggregator_service import Result

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class HtmlStatusClient:
    """Python HTML client: consumes monitor WebSocket status and serves rendered pages."""

    def __init__(
        self,
        server_ws_url: str,
        *,
        host: str = "127.0.0.1",
        port: int = 8090,
        refresh_seconds: int = 0,
        renderer: StatusPageRenderer | None = None,
        web_dir: Path | None = None,
    ):
        self._server_ws_url = server_ws_url
        self._host = host
        self._port = port
        self._refresh_seconds = refresh_seconds
        self._renderer = renderer or StatusPageRenderer()
        self._web_dir = web_dir or WEB_DIR
        self._connected = False
        self._status = Result.NONE.value
        self._fetching = False
        self._is_running = False
        self._builds: list = []
        self._poll_in_seconds = 30
        self._last_checked_at: float | None = None
        self._next_check_at: float | None = None
        self._browser_clients: set[web.WebSocketResponse] = set()
        self._runner: web.AppRunner | None = None
        self._listen_task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def __aenter__(self) -> "HtmlStatusClient":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/", self._index_handler)
        app.router.add_get("/ws", self._browser_websocket_handler)
        for name, content_type in (
            ("styles.css", "text/css"),
            ("countdown.js", "application/javascript"),
            ("app.js", "application/javascript"),
            ("favicon.svg", "image/svg+xml"),
            ("favicon-32.png", "image/png"),
            ("apple-touch-icon.png", "image/png"),
            ("logo.svg", "image/svg+xml"),
            ("logo.png", "image/png"),
        ):
            path = self._web_dir / name
            if path.is_file():
                app.router.add_get(f"/{name}", self._asset_handler(name, content_type))
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()
        self._listen_task = asyncio.create_task(self._listen_forever())
        logging.info(
            "HTML status client listening on http://%s:%s (source %s)",
            self._host,
            self._port,
            self._server_ws_url,
        )

    async def stop(self) -> None:
        self._stop.set()
        clients = list(self._browser_clients)
        self._browser_clients.clear()
        await asyncio.gather(*(client.close() for client in clients), return_exceptions=True)
        if self._listen_task is not None:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    async def run_forever(self) -> None:
        await self._stop.wait()

    def _payload(self) -> dict:
        return {
            "type": "status",
            "fetching": self._fetching,
            "status": self._status,
            "is_running": self._is_running,
            "builds": self._builds,
            "poll_in_seconds": self._poll_in_seconds,
            "last_checked_at": self._last_checked_at,
            "next_check_at": self._next_check_at,
        }

    def _render(self) -> str:
        return self._renderer.render(
            status=self._status,
            fetching=self._fetching,
            is_running=self._is_running,
            connected=self._connected,
            refresh_seconds=self._refresh_seconds,
            builds=self._builds,
            poll_in_seconds=self._poll_in_seconds,
            last_checked_at=self._last_checked_at,
            next_check_at=self._next_check_at,
        )

    async def _index_handler(self, _request: web.Request) -> web.Response:
        return web.Response(text=self._render(), content_type="text/html")

    def _asset_handler(self, filename: str, content_type: str):
        async def handler(_request: web.Request) -> web.FileResponse:
            return web.FileResponse(
                self._web_dir / filename,
                headers={"Content-Type": content_type},
            )

        return handler

    async def _browser_websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        self._browser_clients.add(ws)
        try:
            await ws.send_json(self._payload())
            async for msg in ws:
                if msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                    break
        finally:
            self._browser_clients.discard(ws)
        return ws

    async def _broadcast_to_browsers(self) -> None:
        if not self._browser_clients:
            return
        message = json.dumps(self._payload())
        stale: list[web.WebSocketResponse] = []
        for client in list(self._browser_clients):
            if client.closed:
                stale.append(client)
                continue
            try:
                await client.send_str(message)
            except ConnectionResetError:
                stale.append(client)
            except Exception:
                logging.exception("Failed to send status to browser client")
                stale.append(client)
        for client in stale:
            self._browser_clients.discard(client)

    async def _listen_forever(self) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            try:
                async with ClientSession() as session:
                    async with session.ws_connect(self._server_ws_url, heartbeat=30) as ws:
                        self._connected = True
                        backoff = 1.0
                        logging.info("Connected to monitor WebSocket %s", self._server_ws_url)
                        await self._broadcast_to_browsers()
                        async for msg in ws:
                            if msg.type == WSMsgType.TEXT:
                                self._apply_payload(msg.json())
                                await self._broadcast_to_browsers()
                            elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                                break
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception("Monitor WebSocket disconnected; retrying in %.0fs", backoff)
            finally:
                self._connected = False
                await self._broadcast_to_browsers()

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=backoff)
            except TimeoutError:
                backoff = min(backoff * 2, 15.0)

    def _apply_payload(self, payload: dict) -> None:
        if payload.get("type") not in (None, "status"):
            return
        self._status = str(payload.get("status") or Result.NONE.value)
        self._fetching = bool(payload.get("fetching"))
        self._is_running = bool(payload.get("is_running"))
        builds = payload.get("builds") or []
        self._builds = builds if isinstance(builds, list) else []
        poll = payload.get("poll_in_seconds")
        if isinstance(poll, int) and poll > 0:
            self._poll_in_seconds = poll
        last_checked = payload.get("last_checked_at")
        self._last_checked_at = (
            float(last_checked) if isinstance(last_checked, (int, float)) else None
        )
        next_check = payload.get("next_check_at")
        self._next_check_at = float(next_check) if isinstance(next_check, (int, float)) else None


def normalize_ws_url(url: str) -> str:
    """Accept http(s)://host:port[/] and map to the monitor /ws endpoint."""
    trimmed = url.strip().rstrip("/")
    if trimmed.startswith("http://"):
        return "ws://" + trimmed[len("http://") :] + "/ws"
    if trimmed.startswith("https://"):
        return "wss://" + trimmed[len("https://") :] + "/ws"
    if trimmed.endswith("/ws"):
        return trimmed
    if trimmed.startswith(("ws://", "wss://")):
        return trimmed + "/ws"
    raise ValueError(f"Unsupported monitor URL: {url}")


async def main(
    server_url: str,
    *,
    host: str,
    port: int,
    refresh_seconds: int,
) -> None:
    ws_url = normalize_ws_url(server_url)
    async with HtmlStatusClient(
        ws_url,
        host=host,
        port=port,
        refresh_seconds=refresh_seconds,
    ) as client:
        await client.run_forever()
