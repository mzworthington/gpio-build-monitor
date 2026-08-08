#!/usr/bin/env python3

import os
from pathlib import Path
from typing import Any, NotRequired, TypedDict

import yaml

from monitor.ci_gateway.constants import IntegrationType
from monitor.gpio.constants import Lights, configure_pins


class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""


class IntegrationConfig(TypedDict):
    type: str
    username: str
    repo: str
    excluded_workflows: NotRequired[list[str]]
    excluded_workflow_patterns: NotRequired[list[str]]
    branch: NotRequired[str]


class WebSocketOutputConfig(TypedDict):
    enabled: bool
    host: str
    port: int


class OutputsConfig(TypedDict):
    gpio: bool
    websocket: NotRequired[WebSocketOutputConfig]


class WebhookConfig(TypedDict):
    enabled: bool
    host: str
    port: int


class Config(TypedDict):
    poll_in_seconds: int
    integrations: list[IntegrationConfig]
    outputs: OutputsConfig
    pins: NotRequired[dict[str, int]]
    log_dir: NotRequired[str]
    webhooks: NotRequired[WebhookConfig]


TOKEN_ENV_VARS: dict[IntegrationType, str] = {
    IntegrationType.GITHUB: "GITHUB_TOKEN",
    IntegrationType.CIRCLECI: "CIRCLE_CI_TOKEN",
}

WEBHOOK_SECRET_ENV_VARS: dict[IntegrationType, str] = {
    IntegrationType.GITHUB: "GITHUB_WEBHOOK_SECRET",
    IntegrationType.CIRCLECI: "CIRCLE_CI_WEBHOOK_SECRET",
}

DEFAULT_WEBHOOK_HOST = "0.0.0.0"
DEFAULT_WEBHOOK_PORT = 8080
_DEFAULT_OUTPUTS: OutputsConfig = {"gpio": True}


def load_config(conf_file: str | Path) -> Config:
    path = Path(conf_file)
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")

    with path.open(encoding="utf-8") as handle:
        try:
            raw = yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc

    return validate_config(raw)


def validate_config(raw: dict[str, Any]) -> Config:
    if not isinstance(raw, dict):
        raise ConfigError("Config must be a YAML mapping")

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
    webhooks = _validate_webhooks(raw.get("webhooks"))
    outputs = _validate_outputs(raw.get("outputs"))

    validate_tokens(validated_integrations)
    if webhooks is not None and webhooks["enabled"]:
        validate_webhook_secrets(validated_integrations)
    configure_pins(pins)

    config = Config(
        poll_in_seconds=poll_in_seconds,
        integrations=validated_integrations,
        outputs=outputs,
    )
    if pins is not None:
        config["pins"] = pins
    if log_dir is not None:
        config["log_dir"] = log_dir
    if webhooks is not None:
        config["webhooks"] = webhooks
    return config


def _validate_outputs(raw: Any) -> OutputsConfig:
    if raw is None:
        return dict(_DEFAULT_OUTPUTS)

    if not isinstance(raw, dict):
        raise ConfigError("outputs must be an object")

    gpio = raw.get("gpio", True)
    if not isinstance(gpio, bool):
        raise ConfigError("outputs.gpio must be a boolean")

    outputs: OutputsConfig = {"gpio": gpio}

    if "websocket" in raw:
        outputs["websocket"] = _validate_websocket(raw.get("websocket"))

    if not outputs["gpio"] and not outputs.get("websocket", {}).get("enabled", False):
        raise ConfigError("At least one output must be enabled (gpio or websocket)")

    return outputs


def _validate_websocket(raw: Any) -> WebSocketOutputConfig:
    if not isinstance(raw, dict):
        raise ConfigError("outputs.websocket must be an object")

    enabled = raw.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ConfigError("outputs.websocket.enabled must be a boolean")

    host = raw.get("host", "0.0.0.0")
    if not isinstance(host, str) or not host.strip():
        raise ConfigError("outputs.websocket.host must be a non-empty string")

    port = raw.get("port", 8080)
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise ConfigError("outputs.websocket.port must be an integer between 1 and 65535")

    return WebSocketOutputConfig(enabled=enabled, host=host, port=port)


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

    excluded_workflow_patterns = raw.get("excluded_workflow_patterns", [])
    if excluded_workflow_patterns is None:
        excluded_workflow_patterns = []
    if not isinstance(excluded_workflow_patterns, list) or not all(
        isinstance(pattern, str) and pattern for pattern in excluded_workflow_patterns
    ):
        raise ConfigError(
            f"{prefix}.excluded_workflow_patterns must be a list of non-empty strings"
        )

    branch = raw.get("branch")
    if branch is None:
        branch = "main" if integration_type == "GITHUB" else None
    elif not isinstance(branch, str) or not branch.strip():
        raise ConfigError(
            f"{prefix}.branch must be a non-empty string "
            "(use '*' to include all branches)"
        )

    config = IntegrationConfig(
        type=integration_type,
        username=username,
        repo=repo,
        excluded_workflows=excluded_workflows,
        excluded_workflow_patterns=excluded_workflow_patterns,
    )
    if branch is not None:
        config["branch"] = branch
    return config


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


def validate_webhook_secrets(integrations: list[IntegrationConfig]) -> None:
    required_types = {IntegrationType[integration["type"]] for integration in integrations}
    missing = [
        env_var
        for integration_type in required_types
        if not os.getenv(env_var := WEBHOOK_SECRET_ENV_VARS[integration_type])
    ]
    if missing:
        raise ConfigError(
            "webhooks.enabled requires environment variable(s): "
            + ", ".join(sorted(set(missing)))
        )


def webhook_secrets_from_env() -> dict[str, str | None]:
    return {
        "github": os.getenv(WEBHOOK_SECRET_ENV_VARS[IntegrationType.GITHUB]),
        "circleci": os.getenv(WEBHOOK_SECRET_ENV_VARS[IntegrationType.CIRCLECI]),
    }


def _validate_webhooks(raw: Any) -> WebhookConfig | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ConfigError("webhooks must be an object")

    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ConfigError("webhooks.enabled must be a boolean")

    host = raw.get("host", DEFAULT_WEBHOOK_HOST)
    if not isinstance(host, str) or not host.strip():
        raise ConfigError("webhooks.host must be a non-empty string")

    port = raw.get("port", DEFAULT_WEBHOOK_PORT)
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise ConfigError("webhooks.port must be an integer between 1 and 65535")

    return WebhookConfig(enabled=enabled, host=host, port=port)
