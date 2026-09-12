#!/usr/bin/env python3

from unittest.mock import patch

from gpio_pi.__main__ import main


def test_main_runs_the_gpio_follower():
    with patch("gpio_pi.__main__.asyncio.run") as run:
        main()
    run.assert_called_once()
