#!/usr/bin/env python3

from unittest.mock import AsyncMock, MagicMock

import pytest

from monitor.app import _run_loop
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
