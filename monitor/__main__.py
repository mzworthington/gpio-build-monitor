#!/usr/bin/env python3

import asyncio
import logging
from pathlib import Path

import typer

import monitor.app as app
from monitor.config import ConfigError, load_config

cli_app = typer.Typer(
    add_completion=False,
    help="GPIO build monitor for CI status LEDs",
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
        Path("monitor/integrations.json"),
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
    """Poll CI providers and update GPIO LEDs."""
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
        Path("monitor/integrations.json"),
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

    typer.echo(
        f"Config OK: {len(config['integrations'])} integration(s), "
        f"poll every {config['poll_in_seconds']}s"
    )


def cli() -> None:
    cli_app()


if __name__ == "__main__":
    cli()
