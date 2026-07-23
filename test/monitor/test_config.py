#!/usr/bin/env python3


import pytest

from monitor.config import ConfigError, load_config, validate_config


def test_validate_config_accepts_valid_config(tmp_path):
    config = validate_config({
        "poll_in_seconds": 30,
        "integrations": [
            {"type": "GITHUB", "username": "org", "repo": "repo"},
        ],
    })

    assert config["poll_in_seconds"] == 30
    assert len(config["integrations"]) == 1


def test_validate_config_rejects_unknown_integration_type():
    with pytest.raises(ConfigError, match="unsupported"):
        validate_config({
            "poll_in_seconds": 30,
            "integrations": [
                {"type": "BLURGH", "username": "org", "repo": "repo"},
            ],
        })


def test_validate_config_rejects_missing_integrations():
    with pytest.raises(ConfigError, match="integrations"):
        validate_config({"poll_in_seconds": 30})


def test_validate_tokens_requires_github_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(ConfigError, match="GITHUB_TOKEN"):
        validate_config({
            "poll_in_seconds": 30,
            "integrations": [
                {"type": "GITHUB", "username": "org", "repo": "repo"},
            ],
        })


def test_validate_tokens_requires_circleci_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    monkeypatch.delenv("CIRCLE_CI_TOKEN", raising=False)
    with pytest.raises(ConfigError, match="CIRCLE_CI_TOKEN"):
        validate_config({
            "poll_in_seconds": 30,
            "integrations": [
                {"type": "GITHUB", "username": "org", "repo": "repo"},
                {"type": "CIRCLECI", "username": "org", "repo": "repo"},
            ],
        })


def test_load_config_reads_file(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    config_path = tmp_path / "integrations.json"
    config_path.write_text(
        '{"poll_in_seconds": 45, "integrations": ['
        '{"type": "GITHUB", "username": "org", "repo": "repo"}'
        ']}',
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config["poll_in_seconds"] == 45


def test_load_config_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "missing.json")


def test_validate_pins_accepts_overrides():
    config = validate_config({
        "poll_in_seconds": 30,
        "pins": {"GREEN": 5, "RED": 6},
        "integrations": [
            {"type": "GITHUB", "username": "org", "repo": "repo"},
        ],
    })
    assert config["pins"] == {"GREEN": 5, "RED": 6}


def test_validate_pins_rejects_unknown_light():
    with pytest.raises(ConfigError, match="pins.NOT_A_LIGHT"):
        validate_config({
            "poll_in_seconds": 30,
            "pins": {"NOT_A_LIGHT": 1},
            "integrations": [
                {"type": "GITHUB", "username": "org", "repo": "repo"},
            ],
        })
