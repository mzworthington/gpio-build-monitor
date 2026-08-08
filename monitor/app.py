#!/usr/bin/env python3

import logging
import pprint
from contextlib import AsyncExitStack
from pathlib import Path

import aiohttp
from aiohttp import web

from monitor.build_monitor import BuildMonitor
from monitor.ci_gateway import integration_actions as available_integrations
from monitor.config import Config, load_config, webhook_secrets_from_env
from monitor.gpio.board import Board
from monitor.log_handler import setup_logger
from monitor.output import CompositeStatusOutput, GpioStatusOutput, WebSocketStatusOutput
from monitor.output.port import StatusOutput
from monitor.service.aggregator_service import AggregatorService
from monitor.service.integration_mapper import IntegrationMapper
from monitor.service.refresh_signal import RefreshSignal
from monitor.webhooks.server import start_server


def build_status_outputs(config: Config) -> tuple[list[StatusOutput], Board | None, WebSocketStatusOutput | None]:
    """Create configured status adapters. Caller owns Board / WebSocket lifecycles."""
    outputs_cfg = config["outputs"]
    adapters: list[StatusOutput] = []
    board: Board | None = None
    websocket: WebSocketStatusOutput | None = None

    if outputs_cfg.get("gpio", True):
        board = Board()
        adapters.append(GpioStatusOutput(board))

    websocket_cfg = outputs_cfg.get("websocket")
    if websocket_cfg and websocket_cfg.get("enabled", False):
        websocket = WebSocketStatusOutput(
            host=websocket_cfg["host"],
            port=websocket_cfg["port"],
            poll_in_seconds=config["poll_in_seconds"],
        )
        adapters.append(websocket)

    return adapters, board, websocket


async def main(conf_file: str | Path, level, log_dir: str | None = None):
    config = load_config(conf_file)
    setup_logger(level, log_dir or config.get("log_dir"))
    logging.info("Hello build monitor!")

    poll_in_seconds = config["poll_in_seconds"]
    integrations = config["integrations"]
    logging.info("Polling increment (in seconds): %s", poll_in_seconds)
    logging.info("Integrations: %s", pprint.pformat(integrations))
    logging.info("Outputs: %s", pprint.pformat(config["outputs"]))

    aggregator = AggregatorService(
        IntegrationMapper(available_integrations.get_all()).get(integrations)
    )

    adapters, board, websocket = build_status_outputs(config)
    async with AsyncExitStack() as stack:
        if board is not None:
            stack.enter_context(board)
            logging.info("GPIO board initialised")
        if websocket is not None:
            await stack.enter_async_context(websocket)

        output: StatusOutput = (
            adapters[0] if len(adapters) == 1 else CompositeStatusOutput(adapters)
        )
        monitor = BuildMonitor(output, aggregator)
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
            logging.info("Woken by webhook; refreshing immediately")
        else:
            logging.info(
                "Reconcile poll after %s seconds without a webhook",
                poll_in_seconds,
            )


async def _maybe_start_webhooks(
    config: Config,
    refresh: RefreshSignal,
) -> web.AppRunner | None:
    webhooks = config.get("webhooks")
    if webhooks is None or not webhooks["enabled"]:
        logging.info("Webhook ingress disabled; using timed polling only")
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
