#!/usr/bin/env python3

from unittest.mock import MagicMock

import pytest

from monitor.app import build_status_outputs, main
from monitor.gpio.board import Board
from monitor.output.composite_output import CompositeStatusOutput
from monitor.output.gpio_output import GpioStatusOutput
from monitor.output.websocket_output import WebSocketStatusOutput


def _config(outputs: dict) -> dict:
    return {
        "poll_in_seconds": 45,
        "outputs": outputs,
        "integrations": [],
    }


OUTPUT_SHAPES = (
    pytest.param(
        {"gpio": True},
        (GpioStatusOutput,),
        True,
        False,
        id="gpio-only",
    ),
    pytest.param(
        {
            "gpio": False,
            "websocket": {"enabled": True, "host": "127.0.0.1", "port": 9090},
        },
        (WebSocketStatusOutput,),
        False,
        True,
        id="websocket-only",
    ),
    pytest.param(
        {
            "gpio": True,
            "websocket": {"enabled": True, "host": "127.0.0.1", "port": 9090},
        },
        (GpioStatusOutput, WebSocketStatusOutput),
        True,
        True,
        id="both",
    ),
)


@pytest.mark.parametrize(
    "outputs_cfg, expected_types, expect_board, expect_websocket",
    OUTPUT_SHAPES,
)
def test_build_status_outputs_catalog(
    outputs_cfg, expected_types, expect_board, expect_websocket
):
    adapters, board, websocket = build_status_outputs(_config(outputs_cfg))

    assert tuple(type(adapter) for adapter in adapters) == expected_types
    assert isinstance(board, Board) is expect_board
    assert (websocket is not None) is expect_websocket
    if expect_websocket:
        assert websocket is adapters[-1]
        assert websocket._host == outputs_cfg["websocket"]["host"]
        assert websocket._port == outputs_cfg["websocket"]["port"]
        assert websocket._poll_in_seconds == 45


def _write_config(path, outputs_yaml: str, webhooks_yaml: str = "") -> None:
    path.write_text(
        "poll_in_seconds: 30\n"
        f"{outputs_yaml}"
        f"{webhooks_yaml}"
        "integrations:\n"
        "  - type: GITHUB\n"
        "    username: org\n"
        "    repo: repo\n",
        encoding="utf-8",
    )


class _ImmediateWebSocket:
    def __init__(self, host, port, poll_in_seconds):
        self.host = host
        self.port = port
        self.poll_in_seconds = poll_in_seconds
        self.entered = False

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, *_exc):
        return False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "outputs_yaml, expected_output, expect_websocket",
    [
        pytest.param("outputs:\n  gpio: true\n", GpioStatusOutput, False, id="gpio-only"),
        pytest.param(
            "outputs:\n"
            "  gpio: false\n"
            "  websocket:\n"
            "    enabled: true\n"
            "    host: 127.0.0.1\n"
            "    port: 19090\n",
            _ImmediateWebSocket,
            True,
            id="websocket-only",
        ),
        pytest.param(
            "outputs:\n"
            "  gpio: true\n"
            "  websocket:\n"
            "    enabled: true\n"
            "    host: 127.0.0.1\n"
            "    port: 19090\n",
            CompositeStatusOutput,
            True,
            id="both",
        ),
    ],
)
async def test_composition_root_catalog(
    tmp_path,
    monkeypatch,
    outputs_yaml,
    expected_output,
    expect_websocket,
):
    monkeypatch.setattr("monitor.gpio.Mock.GPIO.setmode", lambda _mode: None)
    monkeypatch.setattr("monitor.app.WebSocketStatusOutput", _ImmediateWebSocket)

    composed: dict = {}

    class _CaptureMonitor:
        def __init__(self, output, aggregator):
            composed["output"] = output
            composed["aggregator"] = aggregator

    async def _return_immediately(*_args, **_kwargs):
        return None

    monkeypatch.setattr("monitor.app.BuildMonitor", _CaptureMonitor)
    monkeypatch.setattr("monitor.app._run_loop", _return_immediately)

    conf = tmp_path / "integrations.yaml"
    _write_config(conf, outputs_yaml)

    await main(conf, level=20, log_dir=tmp_path)

    output = composed["output"]
    assert isinstance(output, expected_output)
    if expect_websocket and expected_output is _ImmediateWebSocket:
        assert output.entered is True
    if expected_output is CompositeStatusOutput:
        inner = output._outputs
        assert isinstance(inner[0], GpioStatusOutput)
        assert isinstance(inner[1], _ImmediateWebSocket)
        assert inner[1].entered is True


@pytest.mark.asyncio
async def test_main_cleans_up_webhook_runner(tmp_path, monkeypatch):
    monkeypatch.setattr("monitor.gpio.Mock.GPIO.setmode", lambda _mode: None)
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "hook-secret")

    runner = MagicMock()
    runner.cleaned = False

    async def _fake_cleanup():
        runner.cleaned = True

    runner.cleanup = _fake_cleanup

    async def _fake_start_server(*_args, **_kwargs):
        return runner

    async def _return_immediately(*_args, **_kwargs):
        return None

    monkeypatch.setattr("monitor.app.start_server", _fake_start_server)
    monkeypatch.setattr("monitor.app._run_loop", _return_immediately)
    monkeypatch.setattr("monitor.app.BuildMonitor", lambda output, aggregator: object())

    conf = tmp_path / "integrations.yaml"
    _write_config(
        conf,
        "outputs:\n  gpio: true\n",
        "webhooks:\n  enabled: true\n  host: 127.0.0.1\n  port: 18081\n",
    )

    await main(conf, level=20, log_dir=tmp_path)

    assert runner.cleaned is True
