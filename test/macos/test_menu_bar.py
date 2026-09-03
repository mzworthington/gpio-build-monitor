#!/usr/bin/env python3

from macos.menu_bar import plugin_output, title_for


def test_title_maps_like_gpio_lights():
    assert title_for({"status": "PASS", "is_running": False, "fetching": False}) == (
        "PASS",
        "green",
    )
    assert title_for({"status": "FAIL", "is_running": False, "fetching": False}) == (
        "FAIL",
        "red",
    )
    assert title_for({"status": "FAIL", "is_running": True, "fetching": False}) == (
        "FAIL",
        "red",
    )
    assert title_for({"status": "PASS", "is_running": True, "fetching": False}) == (
        "RUN",
        "yellow",
    )
    assert title_for({"status": "CONNECTION_ERROR", "is_running": False, "fetching": False}) == (
        "ERR",
        "purple",
    )
    assert title_for({"status": "APPROVAL", "is_running": False, "fetching": False}) == (
        "WAIT",
        "yellow",
    )
    assert title_for({"status": "NONE", "is_running": False, "fetching": True}) == (
        "…",
        "blue",
    )
    assert title_for({"status": "NONE", "is_running": False, "fetching": False}) == (
        "IDLE",
        "gray",
    )
    assert title_for({"status": "UNKNOWN", "is_running": False, "fetching": False}) == (
        "UNK",
        "red",
    )


def test_plugin_output_lists_builds_and_dashboard():
    text = plugin_output(
        {
            "status": "FAIL",
            "is_running": False,
            "fetching": False,
            "builds": [
                {
                    "repo": "org/app",
                    "workflow": "CI",
                    "status": "FAIL",
                    "url": "https://github.com/org/app/actions/1",
                }
            ],
        },
        dashboard_url="https://monitor.mzworthington.co.uk",
    )
    lines = text.splitlines()
    assert lines[0] == "FAIL | color=red"
    assert "---" in lines
    assert "org/app CI FAIL | href=https://github.com/org/app/actions/1 color=red" in lines
    assert "Open monitor | href=https://monitor.mzworthington.co.uk" in lines
    assert "Refresh | refresh=true" in lines
