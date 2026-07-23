#!/usr/bin/env python3

import asyncio
import logging
import pprint
from pathlib import Path

import aiohttp

from monitor.build_monitor import BuildMonitor
from monitor.ci_gateway import integration_actions as available_integrations
from monitor.config import load_config
from monitor.gpio.board import Board
from monitor.log_handler import setup_logger
from monitor.service.aggregator_service import AggregatorService
from monitor.service.integration_mapper import IntegrationMapper


async def main(conf_file: str | Path, level, log_dir: str | None = None):
    config = load_config(conf_file)
    setup_logger(level, log_dir or config.get("log_dir"))
    logging.info('Hello build monitor!')

    with Board() as board:
        logging.info('Board initialised')
        poll_in_seconds = config['poll_in_seconds']
        integrations = config['integrations']
        logging.info(f'Polling increment (in seconds): {poll_in_seconds}')
        logging.info(f'Integrations: {pprint.pformat(integrations)}')

        aggregator = AggregatorService(
            IntegrationMapper(
                available_integrations.get_all()).get(
                integrations))
        monitor = BuildMonitor(board, aggregator)
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            while True:
                await monitor.run(session)
                logging.info(f'Sleeping for {poll_in_seconds} seconds')
                await asyncio.sleep(poll_in_seconds)
