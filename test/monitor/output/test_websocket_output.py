#!/usr/bin/env python3

import socket

import pytest
from aiohttp import ClientSession

from monitor.output.websocket_output import WebSocketStatusOutput
from monitor.service.aggregator_service import Result


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.asyncio
async def test_websocket_broadcasts_status_and_serves_ui(tmp_path):
    (tmp_path / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    (tmp_path / "app.js").write_text("console.log('ok')", encoding="utf-8")
    (tmp_path / "countdown.js").write_text("console.log('tick')", encoding="utf-8")
    (tmp_path / "styles.css").write_text("body{}", encoding="utf-8")
    port = _free_port()

    async with WebSocketStatusOutput(
        host="127.0.0.1",
        port=port,
        web_dir=tmp_path,
        poll_in_seconds=12,
    ) as output:
        async with ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/") as response:
                assert response.status == 200
                assert "ok" in await response.text()

            async with session.ws_connect(f"http://127.0.0.1:{port}/ws") as ws:
                initial = await ws.receive_json()
                assert initial == {
                    "type": "status",
                    "fetching": False,
                    "status": "NONE",
                    "is_running": False,
                    "builds": [],
                    "poll_in_seconds": 12,
                    "last_checked_at": None,
                    "next_check_at": None,
                    "sleep_seconds": 900,
                }

                await output.begin_fetch()
                fetching = await ws.receive_json()
                assert fetching["fetching"] is True
                assert fetching["status"] == "NONE"
                assert fetching["next_check_at"] is None

                await output.publish(Result.PASS, is_running=True)
                published = await ws.receive_json()
                assert published["fetching"] is False
                assert published["status"] == "PASS"
                assert published["is_running"] is True
                assert published["builds"] == []
                assert published["poll_in_seconds"] == 12
                assert published["sleep_seconds"] == 120
                assert isinstance(published["last_checked_at"], (int, float))
                assert (
                    published["last_checked_at"] + 12
                    == published["next_check_at"]
                )


@pytest.mark.asyncio
async def test_status_snapshot_matches_websocket_payload():
    port = _free_port()

    async with WebSocketStatusOutput(
        host="127.0.0.1",
        port=port,
        poll_in_seconds=12,
    ) as output:
        await output.publish(Result.PASS, is_running=False)
        async with ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/status") as response:
                assert response.status == 200
                body = await response.json()
                assert body["type"] == "status"
                assert body["status"] == "PASS"
                assert body["is_running"] is False
                assert body["fetching"] is False
                assert body["poll_in_seconds"] == 12
                assert body["sleep_seconds"] == 900
                etag = response.headers["ETag"]
                assert etag.startswith('W/"')
                assert response.headers["Retry-After"] == "900"

        async with ClientSession() as session:
            async with session.get(
                f"http://127.0.0.1:{port}/status",
                headers={"If-None-Match": etag},
            ) as not_modified:
                assert not_modified.status == 304
                assert not_modified.headers["Retry-After"] == "900"
                assert await not_modified.read() == b""

        await output.publish(
            Result.FAIL,
            is_running=False,
            builds=[
                {
                    "repo": "acme/web",
                    "workflow": "CI",
                    "status": "FAIL",
                    "url": "https://example.com/1",
                },
                {
                    "repo": "acme/web",
                    "workflow": "Deploy",
                    "status": "PASS",
                    "url": "https://example.com/2",
                },
            ],
        )
        async with ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/status?view=eink") as compact:
                assert compact.status == 200
                body = await compact.json()
                assert body["sleep_seconds"] == 180
                assert [build["workflow"] for build in body["builds"]] == ["CI"]
