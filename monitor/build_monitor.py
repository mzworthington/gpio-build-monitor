#!/usr/bin/env python3

import logging

from aiohttp import ClientSession

from monitor.gpio.board import Board
from monitor.gpio.constants import Lights
from monitor.service.aggregator_service import AggregatorService, Result


class BuildMonitor:
    def __init__(self,
                 board: Board,
                 aggregator: AggregatorService):
        self.board = board
        self.aggregator = aggregator

    async def run(self, session: ClientSession) -> None:
        self.board.on(Lights.BLUE)
        logging.info("Getting build results")
        try:
            result = await self.aggregator.run(session)
        finally:
            self.board.off(Lights.BLUE)

        status = result['status']
        is_running = result['is_running']

        logging.info(f'Setting output {result}')

        match status:
            case Result.PASS:
                self.board.off(Lights.PURPLE)
                self.board.on(Lights.GREEN)
                self.board.off(Lights.RED)
            case Result.FAIL:
                self.board.off(Lights.PURPLE)
                self.board.off(Lights.GREEN)
                self.board.on(Lights.RED)
            case Result.UNKNOWN:
                self.board.off(Lights.PURPLE)
                self.board.on(Lights.GREEN)
                self.board.on(Lights.RED)
            case Result.CONNECTION_ERROR:
                self.board.on(Lights.PURPLE)
                self.board.off(Lights.GREEN)
                self.board.off(Lights.RED)
            case _:
                self.board.off(Lights.PURPLE)
                self.board.off(Lights.GREEN)
                self.board.off(Lights.RED)

        if is_running:
            await self.board.pulse(Lights.YELLOW)
        else:
            self.board.off(Lights.YELLOW)

        logging.info("Finished build run")
