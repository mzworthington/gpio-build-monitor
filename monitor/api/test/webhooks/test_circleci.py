#!/usr/bin/env python3

from monitor.webhooks.circleci import CircleCIWebhook
from monitor.webhooks.constants import RefreshDecision


def test_circleci_provider_metadata():
    provider = CircleCIWebhook()
    assert provider.name == "circleci"
    assert provider.path == "/webhooks/circleci"
    assert provider.signature_header == "circleci-signature"
    assert provider.event_header == "circleci-event-type"


def test_circleci_verify_signature_accepts_valid():
    provider = CircleCIWebhook()
    # Documented CircleCI example: secret=secret, body=foo
    assert provider.verify_signature(
        b"foo",
        "secret",
        "v1=773ba44693c7553d6ee20f61ea5d2757a9a4f4a44d2841ae4e95b52e4cd62db4",
    ) is True


def test_circleci_verify_signature_rejects_invalid_and_missing_v1():
    provider = CircleCIWebhook()
    assert provider.verify_signature(b"foo", "secret", "v1=not-a-valid-signature") is False
    assert provider.verify_signature(b"foo", "secret", "v0=abc") is False
    assert provider.verify_signature(b"foo", "secret", None) is False


def test_circleci_decide_terminal_events_refresh():
    provider = CircleCIWebhook()
    assert provider.decide("workflow-completed") is RefreshDecision.REFRESH
    assert provider.decide("job-completed") is RefreshDecision.REFRESH


def test_circleci_decide_ignores_unknown():
    provider = CircleCIWebhook()
    assert provider.decide("something-else") is RefreshDecision.IGNORE
    assert provider.decide(None) is RefreshDecision.IGNORE
