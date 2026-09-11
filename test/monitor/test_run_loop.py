#!/usr/bin/env python3

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from monitor.app import _maybe_start_webhooks, _run_loop
from monitor.service.refresh_signal import RefreshSignal


class StopLoop(Exception):
    pass


async def _run_loop_once_then_stop(monitor, session, refresh, poll_in_seconds: int):
    """Drive the infinite poll loop without hanging the suite."""
    await asyncio.wait_for(
        _run_loop(monitor, session, refresh, poll_in_seconds),
        timeout=1,
    )


@pytest.mark.asyncio
async def test_run_loop_runs_again_after_webhook_wake(caplog):
    monitor = MagicMock()
    monitor.run = AsyncMock()
    session = MagicMock()
    refresh = RefreshSignal()
    call_count = {"n": 0}

    async def wait_then_stop(timeout):
        assert timeout == 30
        call_count["n"] += 1
        if call_count["n"] == 1:
            return True
        raise StopLoop()

    refresh.wait = wait_then_stop  # type: ignore[method-assign]
    caplog.set_level(logging.INFO)

    with pytest.raises(StopLoop):
        await _run_loop_once_then_stop(monitor, session, refresh, poll_in_seconds=30)

    assert monitor.run.await_count == 2
    assert "Woken by webhook; refreshing immediately" in caplog.text


@pytest.mark.asyncio
async def test_run_loop_reconciles_after_timed_poll(caplog):
    monitor = MagicMock()
    monitor.run = AsyncMock()
    session = MagicMock()
    refresh = RefreshSignal()
    call_count = {"n": 0}

    async def wait_then_stop(timeout):
        assert timeout == 15
        call_count["n"] += 1
        if call_count["n"] == 1:
            return False
        raise StopLoop()

    refresh.wait = wait_then_stop  # type: ignore[method-assign]
    caplog.set_level(logging.INFO)

    with pytest.raises(StopLoop):
        await _run_loop_once_then_stop(monitor, session, refresh, poll_in_seconds=15)

    assert monitor.run.await_count == 2
    assert "Reconcile poll after 15 seconds without a webhook" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "config, expect_started",
    [
        pytest.param({}, False, id="webhooks-absent"),
        pytest.param(
            {"webhooks": {"enabled": False, "host": "127.0.0.1", "port": 8081}},
            False,
            id="webhooks-disabled",
        ),
        pytest.param(
            {"webhooks": {"enabled": True, "host": "127.0.0.1", "port": 8081}},
            True,
            id="webhooks-enabled",
        ),
    ],
)
async def test_maybe_start_webhooks_catalog(monkeypatch, config, expect_started):
    refresh = RefreshSignal()
    started: dict = {}

    async def fake_start_server(signal, secrets, host, port):
        started["signal"] = signal
        started["secrets"] = secrets
        started["host"] = host
        started["port"] = port
        return MagicMock(name="webhook-runner")

    monkeypatch.setattr("monitor.app.start_server", fake_start_server)
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "gh-secret")
    monkeypatch.setenv("CIRCLE_CI_WEBHOOK_SECRET", "cci-secret")

    runner = await _maybe_start_webhooks(config, refresh)

    if expect_started:
        assert runner is not None
        assert started["signal"] is refresh
        assert started["host"] == "127.0.0.1"
        assert started["port"] == 8081
        assert started["secrets"]["github"] == "gh-secret"
        assert started["secrets"]["circleci"] == "cci-secret"
    else:
        assert runner is None
        assert started == {}

