#!/usr/bin/env python3

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from monitor.app import _maybe_start_webhooks, _run_loop
from monitor.service.refresh_signal import RefreshSignal


class StopLoop(Exception):
    pass


@pytest.mark.asyncio
async def test_run_loop_runs_again_after_webhook_wake():
    monitor = MagicMock()
    monitor.run = AsyncMock()
    session = MagicMock()
    refresh = RefreshSignal()
    call_count = {"n": 0}

    async def wait_then_stop(timeout):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return True
        raise StopLoop()

    refresh.wait = wait_then_stop  # type: ignore[method-assign]

    with pytest.raises(StopLoop):
        await _run_loop(monitor, session, refresh, poll_in_seconds=30)

    assert monitor.run.await_count == 2


@pytest.mark.asyncio
async def test_run_loop_reconciles_after_timed_poll():
    monitor = MagicMock()
    monitor.run = AsyncMock()
    session = MagicMock()
    refresh = RefreshSignal()
    call_count = {"n": 0}

    async def wait_then_stop(timeout):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return False
        raise StopLoop()

    refresh.wait = wait_then_stop  # type: ignore[method-assign]

    with pytest.raises(StopLoop):
        await _run_loop(monitor, session, refresh, poll_in_seconds=30)

    assert monitor.run.await_count == 2


@pytest.mark.asyncio
async def test_maybe_start_webhooks_skips_when_disabled():
    refresh = RefreshSignal()
    runner = await _maybe_start_webhooks(
        {
            "poll_in_seconds": 30,
            "integrations": [],
            "outputs": {"gpio": False},
        },
        refresh,
    )
    assert runner is None


@pytest.mark.asyncio
async def test_maybe_start_webhooks_starts_ingress_when_enabled():
    refresh = RefreshSignal()
    started = AsyncMock(return_value=MagicMock())
    with patch("monitor.app.start_server", started):
        runner = await _maybe_start_webhooks(
            {
                "poll_in_seconds": 30,
                "integrations": [],
                "outputs": {"gpio": False},
                "webhooks": {"enabled": True, "host": "127.0.0.1", "port": 8765},
            },
            refresh,
        )
    assert runner is started.return_value
    started.assert_awaited_once()
    kwargs = started.await_args.kwargs
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 8765
