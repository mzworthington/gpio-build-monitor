#!/usr/bin/env python3

from macos.menu_bar import plugin_output, snapshot_headers, title_for


def test_title_maps_like_gpio_lights():
    assert title_for({"status": "PASS", "is_running": False, "fetching": False}) == (
        "PASS",
        "green",
        "checkmark.circle.fill",
    )
    assert title_for({"status": "FAIL", "is_running": False, "fetching": False}) == (
        "FAIL",
        "red",
        "xmark.octagon.fill",
    )
    assert title_for({"status": "FAIL", "is_running": True, "fetching": False}) == (
        "FAIL",
        "red",
        "xmark.octagon.fill",
    )
    assert title_for({"status": "PASS", "is_running": True, "fetching": False}) == (
        "RUN",
        "yellow",
        "arrow.triangle.2.circlepath",
    )
    assert title_for({"status": "CONNECTION_ERROR", "is_running": False, "fetching": False}) == (
        "ERR",
        "purple",
        "exclamationmark.triangle.fill",
    )
    assert title_for({"status": "APPROVAL", "is_running": False, "fetching": False}) == (
        "WAIT",
        "yellow",
        "hand.raised.fill",
    )
    assert title_for({"status": "NONE", "is_running": False, "fetching": True}) == (
        "…",
        "blue",
        "ellipsis.circle.fill",
    )
    assert title_for({"status": "NONE", "is_running": False, "fetching": False}) == (
        "IDLE",
        "gray",
        "circle",
    )
    assert title_for({"status": "UNKNOWN", "is_running": False, "fetching": False}) == (
        "UNK",
        "red",
        "questionmark.diamond.fill",
    )


def test_plugin_title_is_an_sf_symbol_not_run_text():
    text = plugin_output(
        {"status": "PASS", "is_running": True, "fetching": False, "builds": []},
        dashboard_url="https://monitor.mzworthington.co.uk",
    )
    title = text.splitlines()[0]
    assert "RUN" not in title.split("|")[0]
    assert title.startswith("\u200b | ")
    assert "sfimage=arrow.triangle.2.circlepath" in title
    assert "sfcolor=yellow" in title
    assert "tooltip=RUN" in title


def test_plugin_output_groups_attention_and_repos():
    text = plugin_output(
        {
            "status": "FAIL",
            "is_running": True,
            "fetching": False,
            "builds": [
                {
                    "repo": "mzworthington/edge-dns",
                    "workflow": "Pulumi",
                    "status": "PASS",
                    "url": "https://github.com/mzworthington/edge-dns/actions/1",
                },
                {
                    "repo": "mzworthington/archlens",
                    "workflow": "CI",
                    "status": "FAIL",
                    "url": "https://github.com/mzworthington/archlens/actions/2",
                },
                {
                    "repo": "mzworthington/archlens",
                    "workflow": "CodeQL Analysis",
                    "status": "RUNNING",
                    "url": "https://github.com/mzworthington/archlens/actions/3",
                },
            ],
        },
        dashboard_url="https://monitor.mzworthington.co.uk",
    )
    lines = text.splitlines()
    assert lines[0].startswith("\u200b | ")
    assert "sfimage=xmark.octagon.fill" in lines[0]
    assert "Needs attention" in text
    assert "archlens · CI" in text
    assert "sfimage=xmark.octagon.fill" in [line for line in lines if "archlens · CI" in line][0]
    assert "Watched" in text
    assert any(
        line.startswith("archlens") and "sfimage=" in line and not line.startswith("--") for line in lines
    )
    assert any(
        line.startswith("-- CI") and "href=https://github.com/mzworthington/archlens/actions/2" in line
        for line in lines
    )
    assert any(line.startswith("-- CodeQL Analysis") for line in lines)
    assert any(line.startswith("edge-dns") for line in lines)
    assert any(line.startswith("-- Pulumi") for line in lines)
    assert any(
        line.startswith("-- Open on GitHub") and "href=https://github.com/mzworthington/archlens" in line
        for line in lines
    )
    assert "mzworthington/archlens CI FAIL |" not in text
    assert any(
        line.startswith("Open monitor") and "href=https://monitor.mzworthington.co.uk" in line for line in lines
    )
    assert any(line.startswith("Refresh") and "refresh=true" in line for line in lines)


def test_plugin_output_empty_builds():
    text = plugin_output(
        {"status": "NONE", "is_running": False, "fetching": False, "builds": []},
        dashboard_url="https://monitor.example",
    )
    assert "No builds yet" in text
    assert "Needs attention" not in text
    assert "Watched" not in text


def test_snapshot_headers_identify_the_client():
    headers = snapshot_headers()
    assert headers["Accept"] == "application/json"
    assert "gpio-build-monitor" in headers["User-Agent"]
