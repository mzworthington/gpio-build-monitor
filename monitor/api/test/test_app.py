#!/usr/bin/env python3

from monitor.app import build_status_outputs


def test_build_status_outputs_is_websocket_only():
    adapters, websocket = build_status_outputs({
        "poll_in_seconds": 30,
        "integrations": [],
        "outputs": {
            "websocket": {"enabled": True, "host": "127.0.0.1", "port": 8080},
        },
    })
    assert [type(adapter).__name__ for adapter in adapters] == ["WebSocketStatusOutput"]
    assert websocket is adapters[0]


def test_build_status_outputs_passes_cors_origins():
    _adapters, websocket = build_status_outputs({
        "poll_in_seconds": 30,
        "integrations": [],
        "outputs": {
            "websocket": {
                "enabled": True,
                "host": "127.0.0.1",
                "port": 8080,
                "cors_origins": ["https://monitor.mzworthington.co.uk"],
            },
        },
    })
    assert websocket is not None
    assert websocket._cors_origins == ("https://monitor.mzworthington.co.uk",)
