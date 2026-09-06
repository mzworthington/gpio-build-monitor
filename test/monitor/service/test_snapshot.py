#!/usr/bin/env python3

from monitor.service.snapshot import (
    eink_payload,
    sleep_seconds,
    snapshot_etag,
    snapshot_headers,
)


def test_sleep_seconds_favours_running_over_green():
    assert sleep_seconds("PASS", is_running=True) == 120
    assert sleep_seconds("PASS", is_running=False) == 900


def test_sleep_seconds_shortens_when_attention_is_needed():
    assert sleep_seconds("FAIL", is_running=False) == 180
    assert sleep_seconds("UNKNOWN", is_running=False) == 180
    assert sleep_seconds("APPROVAL", is_running=False) == 180
    assert sleep_seconds("CONNECTION_ERROR", is_running=False) == 300
    assert sleep_seconds("NONE", is_running=False) == 900


def test_snapshot_etag_ignores_poll_timestamps():
    builds = [
        {
            "repo": "acme/web",
            "workflow": "CI",
            "status": "FAIL",
            "url": "https://example.com/1",
        }
    ]
    first = snapshot_etag("FAIL", is_running=True, builds=builds)
    second = snapshot_etag("FAIL", is_running=True, builds=builds)
    assert first == second
    assert first.startswith('W/"')
    assert snapshot_etag("PASS", is_running=True, builds=builds) != first


def test_eink_payload_keeps_only_glanceable_builds():
    payload = eink_payload(
        {
            "type": "status",
            "fetching": True,
            "status": "FAIL",
            "is_running": True,
            "builds": [
                {
                    "repo": "acme/web",
                    "workflow": "CI",
                    "status": "FAIL",
                    "url": "https://example.com/1",
                },
                {
                    "repo": "acme/web",
                    "workflow": "Deploy",
                    "status": "PASS",
                    "url": "https://example.com/2",
                },
                {
                    "repo": "acme/api",
                    "workflow": "CI",
                    "status": "RUNNING",
                    "url": "https://example.com/3",
                },
            ],
            "poll_in_seconds": 30,
            "last_checked_at": 100.0,
            "next_check_at": 130.0,
        }
    )
    assert payload["sleep_seconds"] == 120
    assert payload["fetching"] is False
    assert [build["workflow"] for build in payload["builds"]] == ["CI", "CI"]
    assert payload["builds"][0]["status"] == "FAIL"
    assert payload["builds"][1]["status"] == "RUNNING"


def test_snapshot_headers_include_retry_after_and_etag():
    headers = snapshot_headers(
        "PASS",
        is_running=False,
        builds=[],
    )
    assert headers["ETag"] == snapshot_etag("PASS", is_running=False, builds=[])
    assert headers["Retry-After"] == "900"
    assert headers["Cache-Control"] == "no-store"
