#!/usr/bin/env python3

from monitor.client.render import StatusPageRenderer


def test_renderer_marks_fail_lights():
    html = StatusPageRenderer().render(
        status="FAIL",
        fetching=False,
        is_running=False,
        connected=True,
        refresh_seconds=2,
        builds=[{
            "repo": "mzworthington/edge-dns",
            "workflow": "Pulumi",
            "status": "FAIL",
            "url": "https://example.com/run",
        }],
    )

    assert 'data-state="live"' in html
    assert 'class="light on" data-light="red"' in html
    assert "At least one build failed" in html
    assert "Failing" in html
    assert "Needs attention" in html
    assert "mzworthington/" in html
    assert "edge-dns" in html
    assert "Pulumi" in html
    assert 'id="status-dial"' in html
    assert 'id="ticker-progress"' in html
    assert 'http-equiv="refresh" content="2"' in html
    assert "countdown.js" in html
    assert "app.js" in html
    assert 'href="/favicon.svg"' in html
    assert 'src="/logo.svg"' in html
    assert "Not checked yet" in html
    assert 'id="last-checked"' in html


def test_renderer_marks_pass_and_running():
    html = StatusPageRenderer().render(
        status="PASS",
        fetching=True,
        is_running=True,
        connected=True,
        refresh_seconds=0,
        builds=[{
            "repo": "org/repo",
            "workflow": "CI",
            "status": "PASS",
            "url": "",
        }],
    )

    assert "All builds passed · build running · fetching" in html
    assert 'http-equiv="refresh"' not in html
    assert 'class="light on" data-light="blue"' in html
    assert 'class="light on pulse" data-light="yellow"' in html
    assert "Needs attention" in html
    assert "app.js" in html


def test_renderer_shows_last_checked_time():
    html = StatusPageRenderer().render(
        status="PASS",
        fetching=False,
        is_running=False,
        connected=True,
        last_checked_at=1_704_067_200.0,  # 2024-01-01 00:00:00 UTC
    )

    assert 'id="last-checked"' in html
    assert 'data-last-checked-at="1704067200.0"' in html
    assert "Checked " in html
    assert "Not checked yet" not in html
