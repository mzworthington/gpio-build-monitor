#!/usr/bin/env python3

from collections.abc import Sequence

from monitor.webhooks.circleci import CircleCIWebhook
from monitor.webhooks.constants import WebhookProvider
from monitor.webhooks.github import GitHubWebhook


def get_all() -> Sequence[WebhookProvider]:
    return (
        GitHubWebhook(),
        CircleCIWebhook(),
    )
