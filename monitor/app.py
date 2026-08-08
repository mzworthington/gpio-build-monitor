#!/usr/bin/env python3

import logging
import pprint
from pathlib import Path

import aiohttp
from aiohttp import web

from monitor.build_monitor import BuildMonitor
from monitor.ci_gateway import integration_actions as available_integrations
from monitor.config import Config, load_config, webhook_secrets_from_env
from monitor.gpio.board import Board
from monitor.log_handler import setup_logger
from monitor.service.aggregator_service import AggregatorService
from monitor.service.integration_mapper import IntegrationMapper
from monitor.service.refresh_signal import RefreshSignal
from monitor.webhooks.server import start_server


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
        refresh = RefreshSignal()
        timeout = aiohttp.ClientTimeout(total=30)

        webhook_runner = await _maybe_start_webhooks(config, refresh)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                await _run_loop(monitor, session, refresh, poll_in_seconds)
        finally:
            if webhook_runner is not None:
                await webhook_runner.cleanup()


async def _run_loop(
    monitor: BuildMonitor,
    session: aiohttp.ClientSession,
    refresh: RefreshSignal,
    poll_in_seconds: int,
) -> None:
    """Refresh on webhook wake-ups, with timed reconcile polls as fallback."""
    while True:
        await monitor.run(session)
        woken = await refresh.wait(timeout=poll_in_seconds)
        if woken:
            logging.info('Woken by webhook; refreshing immediately')
        else:
            logging.info(
                'Reconcile poll after %s seconds without a webhook',
                poll_in_seconds,
            )


async def _maybe_start_webhooks(
    config: Config,
    refresh: RefreshSignal,
) -> web.AppRunner | None:
    webhooks = config.get("webhooks")
    if webhooks is None or not webhooks["enabled"]:
        logging.info('Webhook ingress disabled; using timed polling only')
        return None

    secrets = webhook_secrets_from_env()
    return await start_server(
        refresh,
        {
            "github": secrets["github"],
            "circleci": secrets["circleci"],
        },
        host=webhooks["host"],
        port=webhooks["port"],
    )
