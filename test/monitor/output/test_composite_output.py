#!/usr/bin/env python3
from unittest.mock import AsyncMock

import pytest

from monitor.output.composite_output import CompositeStatusOutput
from monitor.service.aggregator_service import Result


@pytest.mark.asyncio
async def test_composite_fans_out_to_all_outputs():
    first = AsyncMock()
    second = AsyncMock()
    composite = CompositeStatusOutput([first, second])

    await composite.begin_fetch()
    await composite.end_fetch()
    await composite.publish(Result.PASS, is_running=True)

    first.begin_fetch.assert_awaited_once()
    second.begin_fetch.assert_awaited_once()
    first.end_fetch.assert_awaited_once()
    second.end_fetch.assert_awaited_once()
    first.publish.assert_awaited_once_with(Result.PASS, is_running=True, builds=None)
    second.publish.assert_awaited_once_with(Result.PASS, is_running=True, builds=None)


@pytest.mark.asyncio
async def test_composite_continues_when_one_output_fails():
    failing = AsyncMock()
    failing.publish.side_effect = RuntimeError("boom")
    healthy = AsyncMock()
    composite = CompositeStatusOutput([failing, healthy])

    await composite.publish(Result.FAIL, is_running=False)

    healthy.publish.assert_awaited_once_with(Result.FAIL, is_running=False, builds=None)


def test_composite_requires_outputs():
    with pytest.raises(ValueError, match="at least one"):
        CompositeStatusOutput([])
