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
    assert 'href="/manifest.webmanifest"' in html
    assert 'src="/logo.svg"' in html
    assert 'property="og:image"' in html
    assert "social-share.png" in html
    assert 'name="twitter:card"' in html
    assert 'content="summary_large_image"' in html
    assert 'name="theme-color"' in html
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

    assert "All builds passed · fetching" in html
    assert 'http-equiv="refresh"' not in html
    assert 'class="light on" data-light="blue"' in html
    assert 'class="light on pulse" data-light="yellow"' in html
    assert "Needs attention" in html
    assert 'id="repos"' in html
    assert "1 watched" in html
    assert "org/" in html
    assert "1 workflow" in html
    assert "app.js" in html


def test_renderer_elevates_waiting_for_pipeline():
    html = StatusPageRenderer().render(
        status="PASS",
        fetching=False,
        is_running=True,
        connected=True,
        builds=[{
            "repo": "mzworthington/edge-dns",
            "workflow": "Pulumi",
            "status": "WAITING",
            "url": "",
        }],
    )

    assert 'data-status="WAITING"' in html
    assert ">Waiting<" in html
    assert "Waiting for another pipeline" in html
    assert "Passing" not in html


def test_renderer_elevates_approval():
    html = StatusPageRenderer().render(
        status="APPROVAL",
        fetching=False,
        is_running=False,
        connected=True,
        builds=[{
            "repo": "org/repo",
            "workflow": "Deploy",
            "status": "APPROVAL",
            "url": "",
        }],
    )

    assert 'data-status="APPROVAL"' in html
    assert ">Approval<" in html
    assert "Waiting for human approval" in html
    assert "Needs attention" in html
    assert "APPROVAL" in html


def test_renderer_elevates_running_as_primary():
    html = StatusPageRenderer().render(
        status="PASS",
        fetching=False,
        is_running=True,
        connected=True,
        builds=[{
            "repo": "org/repo",
            "workflow": "CI",
            "status": "RUNNING",
            "url": "",
        }],
    )

    assert 'data-status="RUNNING"' in html
    assert ">Running<" in html
    assert "Build in progress" in html
    assert "Passing" not in html
    assert "· build running" not in html
    assert 'data-light="green"' in html
    assert 'class="light on" data-light="green"' not in html
    assert 'class="light on pulse" data-light="yellow"' in html


def test_renderer_keeps_fail_over_running():
    html = StatusPageRenderer().render(
        status="FAIL",
        fetching=False,
        is_running=True,
        connected=True,
        builds=[{
            "repo": "org/repo",
            "workflow": "CI",
            "status": "FAIL",
            "url": "",
        }],
    )

    assert 'data-status="FAIL"' in html
    assert ">Failing<" in html
    assert "· build running" in html
    assert ">Running<" not in html
    assert "Build in progress" not in html

def test_renderer_lists_watched_repos():
    html = StatusPageRenderer().render(
        status="PASS",
        connected=True,
        builds=[
            {
                "repo": "mzworthington/edge-dns",
                "workflow": "Pulumi",
                "status": "PASS",
                "url": "https://github.com/mzworthington/edge-dns/actions",
            },
            {
                "repo": "mzworthington/archlens",
                "workflow": "CI",
                "status": "PASS",
                "url": "https://github.com/mzworthington/archlens/actions",
            },
            {
                "repo": "mzworthington/archlens",
                "workflow": "Deploy",
                "status": "RUNNING",
                "url": "https://github.com/mzworthington/archlens/actions/2",
            },
        ],
    )

    assert "2 watched" in html
    assert "edge-dns" in html
    assert "archlens" in html
    assert "2 workflows" in html
    assert "· running" in html
    assert 'class="repo-row repo-pass is-running"' in html
    assert "repo-workflows" in html
    assert "workflow-name" in html
    assert "Deploy" in html
    assert "CI" in html


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
