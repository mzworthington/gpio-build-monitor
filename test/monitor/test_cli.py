#!/usr/bin/env python3


from typer.testing import CliRunner

from monitor.__main__ import cli_app as app

runner = CliRunner()


def test_check_config_success(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    config_path = tmp_path / "integrations.json"
    config_path.write_text(
        '{"poll_in_seconds": 30, "integrations": ['
        '{"type": "GITHUB", "username": "org", "repo": "repo"}'
        ']}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["check-config", "--conf", str(config_path)])

    assert result.exit_code == 0
    assert "Config OK" in result.stdout


def test_check_config_mentions_webhooks(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "hook")
    config_path = tmp_path / "integrations.json"
    config_path.write_text(
        '{"poll_in_seconds": 300, "webhooks": {"enabled": true, "port": 8080},'
        ' "integrations": [{"type": "GITHUB", "username": "org", "repo": "repo"}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["check-config", "--conf", str(config_path)])

    assert result.exit_code == 0
    assert "webhooks on 0.0.0.0:8080" in result.stdout


def test_check_config_failure(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    config_path = tmp_path / "integrations.json"
    config_path.write_text(
        '{"poll_in_seconds": 30, "integrations": ['
        '{"type": "GITHUB", "username": "org", "repo": "repo"}'
        ']}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["check-config", "--conf", str(config_path)])

    assert result.exit_code == 1
    assert "GITHUB_TOKEN" in result.stderr
