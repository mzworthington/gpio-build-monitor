#!/usr/bin/env python3

from collections.abc import Sequence

from monitor.gpio.board import Board
from monitor.gpio.constants import Lights
from monitor.service.aggregator_service import BuildDetail, Result


class GpioStatusOutput:
    """Maps aggregated CI status onto GPIO LEDs."""

    def __init__(self, board: Board):
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
        builds: Sequence[BuildDetail] | None = None,
    ) -> None:
        match status:
            case Result.PASS:
                self._board.off(Lights.PURPLE)
                self._board.on(Lights.GREEN)
                self._board.off(Lights.RED)
            case Result.FAIL:
                self._board.off(Lights.PURPLE)
                self._board.off(Lights.GREEN)
                self._board.on(Lights.RED)
            case Result.UNKNOWN:
                self._board.off(Lights.PURPLE)
                self._board.on(Lights.GREEN)
                self._board.on(Lights.RED)
            case Result.CONNECTION_ERROR:
                self._board.on(Lights.PURPLE)
                self._board.off(Lights.GREEN)
                self._board.off(Lights.RED)
            case _:
                self._board.off(Lights.PURPLE)
                self._board.off(Lights.GREEN)
                self._board.off(Lights.RED)

        if is_running:
            await self._board.pulse(Lights.YELLOW)
        else:
            self._board.off(Lights.YELLOW)
