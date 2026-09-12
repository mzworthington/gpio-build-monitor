#!/usr/bin/env python3

from collections.abc import Mapping

from aiohttp import ClientSession, WSMsgType

from monitor.api_urls import status_http_url, status_ws_url
from monitor.output.port import StatusOutput
from monitor.service.aggregator_service import Result


async def follow_api(
    origin: str,
    output: StatusOutput,
    session: ClientSession,
    *,
    once: bool = False,
) -> None:
    """Drive a local status output from the hosted Python API websocket."""
    async with session.get(status_http_url(origin)) as snapshot:
        if snapshot.status == 200:
            await _apply_payload(output, await snapshot.json())
    async with session.ws_connect(status_ws_url(origin)) as ws:
        async for message in ws:
            if message.type != WSMsgType.TEXT:
                continue
            payload = message.json()
            await _apply_payload(output, payload)
            if once:
                return


async def _apply_payload(output: StatusOutput, payload: Mapping[str, object]) -> None:
    if payload.get("fetching"):
        await output.begin_fetch()
        return
    await output.end_fetch()
    status = Result[str(payload.get("status", "NONE"))]
    await output.publish(
        status,
        is_running=bool(payload.get("is_running")),
        builds=payload.get("builds") or [],  # type: ignore[arg-type]
    )
