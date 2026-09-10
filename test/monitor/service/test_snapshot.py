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


def test_eink_payload_lists_every_checked_repo_with_action_and_pr_counts():
    payload = eink_payload(
        {
            "type": "status",
            "fetching": False,
            "status": "FAIL",
            "is_running": False,
            "builds": [
                {
                    "repo": "acme/web",
                    "workflow": "CI",
                    "status": "FAIL",
                    "url": "https://example.com/1",
                    "pr_count": 0,
                    "pr_url": "https://github.com/acme/web/pulls",
                },
                {
                    "repo": "acme/web",
                    "workflow": "Deploy",
                    "status": "PASS",
                    "url": "https://example.com/2",
                    "pr_count": 0,
                    "pr_url": "https://github.com/acme/web/pulls",
                },
                {
                    "repo": "acme/api",
                    "workflow": "CI",
                    "status": "PASS",
                    "url": "https://example.com/3",
                    "pr_count": 2,
                    "pr_url": "https://github.com/acme/api/pulls",
                },
            ],
            "poll_in_seconds": 30,
            "last_checked_at": 100.0,
            "next_check_at": 130.0,
        }
    )
    assert payload["repos"] == [
        {
            "repo": "acme/api",
            "status": "PASS",
            "workflow_count": 1,
            "pr_count": 2,
            "is_running": False,
        },
        {
            "repo": "acme/web",
            "status": "FAIL",
            "workflow_count": 2,
            "pr_count": 0,
            "is_running": False,
        },
    ]


def test_eink_payload_keeps_open_prs_when_workflows_are_green():
    payload = eink_payload(
        {
            "type": "status",
            "fetching": False,
            "status": "PASS",
            "is_running": False,
            "builds": [
                {
                    "repo": "acme/web",
                    "workflow": "CI",
                    "status": "PASS",
                    "url": "https://example.com/1",
                    "pr_count": 4,
                    "pr_url": "https://github.com/acme/web/pulls",
                },
            ],
            "poll_in_seconds": 30,
            "last_checked_at": 100.0,
            "next_check_at": 130.0,
        }
    )
    assert payload["builds"] == []
    assert payload["open_prs"] == [
        {
            "repo": "acme/web",
            "pr_count": 4,
            "pr_url": "https://github.com/acme/web/pulls",
        }
    ]


def test_snapshot_etag_changes_when_only_pr_count_changes():
    builds = [
        {
            "repo": "acme/web",
            "workflow": "CI",
            "status": "PASS",
            "url": "https://example.com/1",
            "pr_count": 0,
            "pr_url": "https://github.com/acme/web/pulls",
        }
    ]
    first = snapshot_etag("PASS", is_running=False, builds=builds)
    second = snapshot_etag(
        "PASS",
        is_running=False,
        builds=[{**builds[0], "pr_count": 2}],
    )
    assert first != second


def test_snapshot_headers_include_retry_after_and_etag():
    headers = snapshot_headers(
        "PASS",
        is_running=False,
        builds=[],
    )
    assert headers["ETag"] == snapshot_etag("PASS", is_running=False, builds=[])
    assert headers["Retry-After"] == "900"
    assert headers["Cache-Control"] == "no-store"
