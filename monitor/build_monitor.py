#!/usr/bin/env python3

import logging

from aiohttp import ClientSession

from monitor.output.port import StatusOutput
from monitor.service.aggregator_service import AggregatorService


class BuildMonitor:
    def __init__(self, output: StatusOutput, aggregator: AggregatorService):
        self.output = output
        self.aggregator = aggregator

    async def run(self, session: ClientSession) -> None:
        await self.output.begin_fetch()
        logging.info("Getting build results")
        try:
            result = await self.aggregator.run(session)
        finally:
            await self.output.end_fetch()

        logging.info("Setting output %s", result)
        await self.output.publish(
            result["status"],
            is_running=result["is_running"],
            builds=result["builds"],
        )
        logging.info("Finished build run")
