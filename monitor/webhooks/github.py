#!/usr/bin/env python3

import hashlib
import hmac

from monitor.webhooks.constants import RefreshDecision, WebhookProvider

REFRESH_EVENTS = frozenset({"workflow_run"})


class GitHubWebhook(WebhookProvider):
    @property
    def name(self) -> str:
        return "github"

    @property
    def path(self) -> str:
        return "/webhooks/github"

    @property
    def display_name(self) -> str:
        return "GitHub"

    @property
    def signature_header(self) -> str:
        return "X-Hub-Signature-256"

    @property
    def event_header(self) -> str:
        return "X-GitHub-Event"

    def verify_signature(
        self,
        body: bytes,
        secret: str,
        signature_header: str | None,
    ) -> bool:
        """Verify GitHub's ``X-Hub-Signature-256`` header (HMAC-SHA256)."""
        if not signature_header or not secret:
            return False

        expected = "sha256=" + hmac.new(
            secret.encode("utf-8"),
            msg=body,
            digestmod=hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature_header)

    def decide(self, event_name: str | None) -> RefreshDecision:
        if not event_name:
            return RefreshDecision.IGNORE
        if event_name == "ping":
            return RefreshDecision.ACK
        if event_name in REFRESH_EVENTS:
            return RefreshDecision.REFRESH
        return RefreshDecision.IGNORE
