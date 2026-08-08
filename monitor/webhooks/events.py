#!/usr/bin/env python3

"""Decide whether a provider webhook should wake a CI refresh.

Keeps provider event vocabulary out of the HTTP server and out of the
monitor loop. Status mapping stays in ``ci_gateway`` adapters.
"""

from enum import Enum


class RefreshDecision(Enum):
    REFRESH = "refresh"
    IGNORE = "ignore"
    ACK = "ack"  # accepted but no refresh (e.g. GitHub ping)


GITHUB_REFRESH_EVENTS = frozenset({"workflow_run"})
CIRCLECI_REFRESH_EVENTS = frozenset({"workflow-completed", "job-completed"})


def decide_github(event_name: str | None) -> RefreshDecision:
    if not event_name:
        return RefreshDecision.IGNORE
    if event_name == "ping":
        return RefreshDecision.ACK
    if event_name in GITHUB_REFRESH_EVENTS:
        return RefreshDecision.REFRESH
    return RefreshDecision.IGNORE


def decide_circleci(event_name: str | None) -> RefreshDecision:
    if not event_name:
        return RefreshDecision.IGNORE
    if event_name in CIRCLECI_REFRESH_EVENTS:
        return RefreshDecision.REFRESH
    return RefreshDecision.IGNORE
