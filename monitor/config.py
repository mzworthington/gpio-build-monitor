#!/usr/bin/env python3

import json
import os
from pathlib import Path
from typing import Any, NotRequired, TypedDict

from monitor.ci_gateway.constants import IntegrationType
from monitor.gpio.constants import Lights, configure_pins


class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""


class IntegrationConfig(TypedDict):
    type: str
    username: str
    repo: str
    excluded_workflows: NotRequired[list[str]]


class Config(TypedDict):
    poll_in_seconds: int
    integrations: list[IntegrationConfig]
    pins: NotRequired[dict[str, int]]
    log_dir: NotRequired[str]


TOKEN_ENV_VARS: dict[IntegrationType, str] = {
    IntegrationType.GITHUB: "GITHUB_TOKEN",
    IntegrationType.CIRCLECI: "CIRCLE_CI_TOKEN",
}


def load_config(conf_file: str | Path) -> Config:
    path = Path(conf_file)
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")

    with path.open(encoding="utf-8") as handle:
        raw = json.load(handle)

    return validate_config(raw)


def validate_config(raw: dict[str, Any]) -> Config:
    if not isinstance(raw, dict):
        raise ConfigError("Config must be a JSON object")

    poll_in_seconds = raw.get("poll_in_seconds", 30)
    if not isinstance(poll_in_seconds, int) or poll_in_seconds <= 0:
        raise ConfigError("poll_in_seconds must be a positive integer")

    integrations = raw.get("integrations")
    if not isinstance(integrations, list) or not integrations:
        raise ConfigError("integrations must be a non-empty list")

    validated_integrations: list[IntegrationConfig] = []
    for index, integration in enumerate(integrations):
        validated_integrations.append(_validate_integration(integration, index))

    pins = _validate_pins(raw.get("pins"))
    log_dir = _validate_log_dir(raw.get("log_dir"))

    validate_tokens(validated_integrations)
    configure_pins(pins)

    config = Config(
        poll_in_seconds=poll_in_seconds,
        integrations=validated_integrations,
    )
    if pins is not None:
        config["pins"] = pins
    if log_dir is not None:
        config["log_dir"] = log_dir
    return config


def _validate_pins(raw: Any) -> dict[str, int] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ConfigError("pins must be an object mapping light names to pin numbers")

    validated: dict[str, int] = {}
    for name, pin in raw.items():
        if name not in Lights.__members__:
            supported = ", ".join(sorted(Lights.__members__))
            raise ConfigError(
                f"pins.{name} is unknown (expected one of: {supported})"
            )
        if not isinstance(pin, int) or pin < 0:
            raise ConfigError(f"pins.{name} must be a non-negative integer")
        validated[name] = pin

    return validated


def _validate_log_dir(raw: Any) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise ConfigError("log_dir must be a non-empty string")
    return raw


def _validate_integration(raw: Any, index: int) -> IntegrationConfig:
    prefix = f"integrations[{index}]"

    if not isinstance(raw, dict):
        raise ConfigError(f"{prefix} must be an object")

    integration_type = raw.get("type")
    username = raw.get("username")
    repo = raw.get("repo")

    if not integration_type or not isinstance(integration_type, str):
        raise ConfigError(f"{prefix}.type is required")
    if integration_type not in IntegrationType.__members__:
        supported = ", ".join(sorted(IntegrationType.__members__))
        raise ConfigError(
            f"{prefix}.type '{integration_type}' is unsupported "
            f"(expected one of: {supported})"
        )
    if not username or not isinstance(username, str):
        raise ConfigError(f"{prefix}.username is required")
    if not repo or not isinstance(repo, str):
        raise ConfigError(f"{prefix}.repo is required")

    excluded_workflows = raw.get("excluded_workflows", [])
    if excluded_workflows is None:
        excluded_workflows = []
    if not isinstance(excluded_workflows, list) or not all(
        isinstance(workflow, str) for workflow in excluded_workflows
    ):
        raise ConfigError(f"{prefix}.excluded_workflows must be a list of strings")

    return IntegrationConfig(
        type=integration_type,
        username=username,
        repo=repo,
        excluded_workflows=excluded_workflows,
    )


def validate_tokens(integrations: list[IntegrationConfig]) -> None:
    required_types = {IntegrationType[integration["type"]] for integration in integrations}
    missing = [
        env_var
        for integration_type in required_types
        if not os.getenv(env_var := TOKEN_ENV_VARS[integration_type])
    ]
    if missing:
        raise ConfigError(
            "Missing required environment variable(s): "
            + ", ".join(sorted(set(missing)))
        )
