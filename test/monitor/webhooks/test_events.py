#!/usr/bin/env python3

from monitor.webhooks.events import RefreshDecision, decide_circleci, decide_github


def test_decide_github_workflow_run_refreshes():
    assert decide_github("workflow_run") is RefreshDecision.REFRESH


def test_decide_github_ping_acks():
    assert decide_github("ping") is RefreshDecision.ACK


def test_decide_github_ignores_other_events():
    assert decide_github("push") is RefreshDecision.IGNORE
    assert decide_github(None) is RefreshDecision.IGNORE


def test_decide_circleci_terminal_events_refresh():
    assert decide_circleci("workflow-completed") is RefreshDecision.REFRESH
    assert decide_circleci("job-completed") is RefreshDecision.REFRESH


def test_decide_circleci_ignores_unknown():
    assert decide_circleci("something-else") is RefreshDecision.IGNORE
    assert decide_circleci(None) is RefreshDecision.IGNORE
