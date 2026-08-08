#!/usr/bin/env python3

import asyncio
import logging
from pathlib import Path

import typer

import monitor.app as app
from monitor.config import ConfigError, load_config

cli_app = typer.Typer(
    add_completion=False,
    help="Build monitor for CI status (GPIO LEDs and/or WebSocket UI)",
    no_args_is_help=True,
)

LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warn": logging.WARNING,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}


def _resolve_log_level(log_level: str) -> int:
    level = LOG_LEVELS.get(log_level.lower())
    if level is None:
        supported = ", ".join(sorted(LOG_LEVELS))
        raise typer.BadParameter(
            f"log level '{log_level}' is invalid (expected one of: {supported})"
        )
    return level


@cli_app.command()
def run(
    conf: Path = typer.Option(
        Path("monitor/integrations.yaml"),
        "--conf",
        "-c",
        help="Integration configuration file",
        exists=True,
        readable=True,
    ),
    log_level: str = typer.Option(
        "info",
        "--log-level",
        "-l",
        help="Logging level",
    ),
) -> None:
    """Refresh CI status onto configured outputs (poll and optional webhooks)."""
    try:
        asyncio.run(app.main(conf, _resolve_log_level(log_level)))
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except KeyboardInterrupt:
        raise typer.Exit(0) from None


@cli_app.command("check-config")
def check_config(
    conf: Path = typer.Option(
        Path("monitor/integrations.yaml"),
        "--conf",
        "-c",
        help="Integration configuration file",
        exists=True,
        readable=True,
    ),
) -> None:
    """Validate configuration and required environment variables."""
    try:
        config = load_config(conf)
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    outputs = config["outputs"]
    enabled = []
    if outputs.get("gpio", True):
        enabled.append("gpio")
    websocket = outputs.get("websocket")
    if websocket and websocket.get("enabled"):
        enabled.append(f"websocket:{websocket['host']}:{websocket['port']}")

    webhooks = config.get("webhooks")
    webhook_note = ""
    if webhooks is not None and webhooks["enabled"]:
        webhook_note = f", webhooks on {webhooks['host']}:{webhooks['port']}"

    typer.echo(
        f"Config OK: {len(config['integrations'])} integration(s), "
        f"poll every {config['poll_in_seconds']}s, "
        f"outputs={','.join(enabled)}{webhook_note}"
    )


@cli_app.command("client")
def client(
    server: str = typer.Option(
        "http://127.0.0.1:8080",
        "--server",
        "-s",
        help="Monitor base URL or WebSocket URL (e.g. http://127.0.0.1:8080)",
    ),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="Bind address for the HTML client",
    ),
    port: int = typer.Option(
        8090,
        "--port",
        "-p",
        help="Port for the HTML client",
        min=1,
        max=65535,
    ),
    refresh: int = typer.Option(
        0,
        "--refresh",
        "-r",
        help="Optional HTML meta-refresh interval in seconds (0 = live WebSocket updates only)",
        min=0,
    ),
    log_level: str = typer.Option(
        "info",
        "--log-level",
        "-l",
        help="Logging level",
    ),
) -> None:
    """Render the status page in Python (Jinja2) from the monitor WebSocket feed."""
    from monitor.client import app as client_app
    from monitor.log_handler import setup_logger

    setup_logger(_resolve_log_level(log_level), None)
    try:
        asyncio.run(
            client_app.main(
                server,
                host=host,
                port=port,
                refresh_seconds=refresh,
            )
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except KeyboardInterrupt:
        raise typer.Exit(0) from None


def cli() -> None:
    cli_app()


if __name__ == "__main__":
    cli()
