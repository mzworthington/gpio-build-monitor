#!/usr/bin/env python3

"""Shared webhook types and the provider interface.

Provider-specific signature verification and event vocabulary live in
GitHub / CircleCI implementations, not in the HTTP server.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from enum import Enum

from aiohttp.web import Request


class RefreshDecision(Enum):
    REFRESH = "refresh"
    IGNORE = "ignore"
    ACK = "ack"  # accepted but no refresh (e.g. GitHub ping)


class WebhookProvider(ABC):
    """CI provider webhook adapter: verify → decide → (optionally) refresh."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short id used in secrets maps and log reasons (e.g. ``github``)."""

    @property
    @abstractmethod
    def path(self) -> str:
        """HTTP path for this provider's webhook endpoint."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable provider name for error responses."""

    @property
    @abstractmethod
    def signature_header(self) -> str:
        """Request header that carries the HMAC signature."""

    @property
    @abstractmethod
    def event_header(self) -> str:
        """Request header that carries the event type name."""

    @abstractmethod
    def verify_signature(
        self,
        body: bytes,
        secret: str,
        signature_header: str | None,
    ) -> bool:
        """Return True when ``signature_header`` matches ``body`` for ``secret``."""

    @abstractmethod
    def decide(self, event_name: str | None) -> RefreshDecision:
        """Decide whether this event should wake a CI refresh."""

    def event_name(self, request: Request) -> str | None:
        return request.headers.get(self.event_header)

    def signature_value(self, request: Request) -> str | None:
        return request.headers.get(self.signature_header)


WebhookSecrets = Mapping[str, str | None]
