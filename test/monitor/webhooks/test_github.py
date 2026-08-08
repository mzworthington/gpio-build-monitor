#!/usr/bin/env python3

import hashlib
import hmac

from monitor.webhooks.constants import RefreshDecision
from monitor.webhooks.github import GitHubWebhook


def test_github_provider_metadata():
    provider = GitHubWebhook()
    assert provider.name == "github"
    assert provider.path == "/webhooks/github"
    assert provider.signature_header == "X-Hub-Signature-256"
    assert provider.event_header == "X-GitHub-Event"


def test_github_verify_signature_accepts_valid():
    provider = GitHubWebhook()
    body = b'{"action":"completed"}'
    secret = "topsecret"
    signature = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    assert provider.verify_signature(body, secret, signature) is True


def test_github_verify_signature_rejects_invalid():
    provider = GitHubWebhook()
    assert provider.verify_signature(b"{}", "secret", "sha256=deadbeef") is False
    assert provider.verify_signature(b"{}", "secret", None) is False
    assert provider.verify_signature(b"{}", "", "sha256=abc") is False


def test_github_decide_workflow_run_refreshes():
    assert GitHubWebhook().decide("workflow_run") is RefreshDecision.REFRESH


def test_github_decide_ping_acks():
    assert GitHubWebhook().decide("ping") is RefreshDecision.ACK


def test_github_decide_ignores_other_events():
    provider = GitHubWebhook()
    assert provider.decide("push") is RefreshDecision.IGNORE
    assert provider.decide(None) is RefreshDecision.IGNORE
