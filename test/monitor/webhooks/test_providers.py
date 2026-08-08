#!/usr/bin/env python3

from monitor.webhooks.circleci import CircleCIWebhook
from monitor.webhooks.github import GitHubWebhook
from monitor.webhooks.providers import get_all


def test_get_all_registers_github_and_circleci():
    providers = get_all()
    assert [provider.name for provider in providers] == ["github", "circleci"]
    assert isinstance(providers[0], GitHubWebhook)
    assert isinstance(providers[1], CircleCIWebhook)
