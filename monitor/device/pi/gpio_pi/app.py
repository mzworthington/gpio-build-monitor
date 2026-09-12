import os

from aiohttp import ClientSession

from gpio_pi.follower import follow_api
from gpio_pi.gpio.board import Board
from gpio_pi.output import GpioStatusOutput

DEFAULT_ORIGIN = "https://monitor.mzworthington.co.uk"


async def run(origin: str | None = None) -> None:
    origin = origin or os.environ.get("MONITOR_API_ORIGIN") or DEFAULT_ORIGIN
    with Board() as board:
        output = GpioStatusOutput(board)
        async with ClientSession() as session:
            await follow_api(origin, output, session)
