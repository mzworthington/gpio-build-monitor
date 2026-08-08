#!/usr/bin/env python3

import hashlib
import hmac


def verify_github_signature(body: bytes, secret: str, signature_header: str | None) -> bool:
    """Verify GitHub's ``X-Hub-Signature-256`` header (HMAC-SHA256)."""
    if not signature_header or not secret:
        return False

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def verify_circleci_signature(body: bytes, secret: str, signature_header: str | None) -> bool:
    """Verify CircleCI's ``circleci-signature`` header (``v1`` HMAC-SHA256)."""
    if not signature_header or not secret:
        return False

    versions: dict[str, str] = {}
    for pair in signature_header.split(","):
        if "=" not in pair:
            continue
        version, value = pair.split("=", 1)
        versions[version.strip()] = value.strip()

    provided = versions.get("v1")
    if not provided:
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, provided)
