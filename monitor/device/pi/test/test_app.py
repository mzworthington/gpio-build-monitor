#!/usr/bin/env python3

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from gpio_pi.app import DEFAULT_ORIGIN, run


@pytest.mark.asyncio
async def test_run_follows_hosted_monitor_api():
    follow = AsyncMock()
    board = MagicMock()
    with (
        patch("gpio_pi.app.follow_api", follow),
        patch("gpio_pi.app.Board") as board_cls,
        patch("gpio_pi.app.ClientSession") as session_cls,
    ):
        board_cls.return_value.__enter__.return_value = board
        session = MagicMock()
        session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
        session_cls.return_value.__aexit__ = AsyncMock(return_value=None)
        await run()

    assert follow.await_args.args[0] == DEFAULT_ORIGIN
    assert DEFAULT_ORIGIN == "https://monitor.mzworthington.co.uk"
    assert follow.await_args.args[1]._board is board
