#!/usr/bin/env python3

import hashlib
import hmac

from monitor.webhooks.signatures import (
    verify_circleci_signature,
    verify_github_signature,
)


def test_verify_github_signature_accepts_valid():
    body = b'{"action":"completed"}'
    secret = "topsecret"
    signature = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    assert verify_github_signature(body, secret, signature) is True


def test_verify_github_signature_rejects_invalid():
    assert verify_github_signature(b"{}", "secret", "sha256=deadbeef") is False
    assert verify_github_signature(b"{}", "secret", None) is False
    assert verify_github_signature(b"{}", "", "sha256=abc") is False


def test_verify_circleci_signature_accepts_valid():
    # Documented CircleCI example: secret=secret, body=foo
    assert verify_circleci_signature(
        b"foo",
        "secret",
        "v1=773ba44693c7553d6ee20f61ea5d2757a9a4f4a44d2841ae4e95b52e4cd62db4",
    ) is True


def test_verify_circleci_signature_rejects_invalid_and_missing_v1():
    assert verify_circleci_signature(b"foo", "secret", "v1=not-a-valid-signature") is False
    assert verify_circleci_signature(b"foo", "secret", "v0=abc") is False
    assert verify_circleci_signature(b"foo", "secret", None) is False
