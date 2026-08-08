#!/usr/bin/env python3

import asyncio

import pytest

from monitor.service.refresh_signal import RefreshSignal


@pytest.mark.asyncio
async def test_wait_returns_false_on_timeout():
    signal = RefreshSignal()
    woken = await signal.wait(timeout=0.01)
    assert woken is False


@pytest.mark.asyncio
async def test_wait_returns_true_when_notified():
    signal = RefreshSignal()

    async def notify_soon():
        await asyncio.sleep(0.01)
        signal.notify("test")

    task = asyncio.create_task(notify_soon())
    woken = await signal.wait(timeout=1)
    await task
    assert woken is True


@pytest.mark.asyncio
async def test_notify_during_refresh_coalesces_for_next_wait():
    signal = RefreshSignal()
    signal.notify("during-run")
    woken = await signal.wait(timeout=1)
    assert woken is True
    woken_again = await signal.wait(timeout=0.01)
    assert woken_again is False
