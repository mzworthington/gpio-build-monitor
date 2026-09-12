from collections.abc import Sequence

from gpio_pi.gpio.constants import Lights
from gpio_pi.status import Result


class GpioStatusOutput:
    def __init__(self, board):
        self._board = board

    async def begin_fetch(self) -> None:
        self._board.on(Lights.BLUE)

    async def end_fetch(self) -> None:
        self._board.off(Lights.BLUE)

    async def publish(
        self,
        status: Result,
        *,
        is_running: bool,
        builds: Sequence[object] | None = None,
    ) -> None:
        match status:
            case Result.PASS:
                self._board.off(Lights.PURPLE)
                self._board.on(Lights.GREEN)
                self._board.off(Lights.RED)
            case Result.FAIL | Result.UNKNOWN:
                self._board.off(Lights.PURPLE)
                self._board.off(Lights.GREEN)
                self._board.on(Lights.RED)
            case Result.CONNECTION_ERROR:
                self._board.on(Lights.PURPLE)
                self._board.off(Lights.GREEN)
                self._board.off(Lights.RED)
            case _:
                self._board.off(Lights.PURPLE)
                self._board.off(Lights.GREEN)
                self._board.off(Lights.RED)

        if is_running or status == Result.APPROVAL:
            await self._board.pulse(Lights.YELLOW)
        else:
            self._board.off(Lights.YELLOW)
