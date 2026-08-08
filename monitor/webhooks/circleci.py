#!/usr/bin/env python3

import hashlib
import hmac

from monitor.webhooks.constants import RefreshDecision, WebhookProvider

REFRESH_EVENTS = frozenset({"workflow-completed", "job-completed"})


class CircleCIWebhook(WebhookProvider):
    @property
    def name(self) -> str:
        return "circleci"

    @property
    def path(self) -> str:
        return "/webhooks/circleci"

    @property
    def display_name(self) -> str:
        return "CircleCI"

    @property
    def signature_header(self) -> str:
        return "circleci-signature"

    @property
    def event_header(self) -> str:
        return "circleci-event-type"

    def verify_signature(
        self,
        body: bytes,
        secret: str,
        signature_header: str | None,
    ) -> bool:
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

    def decide(self, event_name: str | None) -> RefreshDecision:
        if not event_name:
            return RefreshDecision.IGNORE
        if event_name in REFRESH_EVENTS:
            return RefreshDecision.REFRESH
        return RefreshDecision.IGNORE
