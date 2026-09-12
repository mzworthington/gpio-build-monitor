#!/usr/bin/env python3
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import TypedDict

from aiohttp import ClientSession

OpenPullRequests = tuple[int | None, str | None]


class SecurityFinding(TypedDict):
    """One alert. Counts ship first; ``items`` is reserved for later detail."""

    number: int
    title: str
    severity: str | None
    url: str
    state: str


class SecuritySource(TypedDict):
    count: int
    url: str
    items: list[SecurityFinding]


class SecurityFindings(TypedDict):
    """Open GitHub security alerts. Non-GitHub providers return None."""

    count: int
    url: str
    vulnerabilities: SecuritySource
    codeql: SecuritySource



class CiResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    APPROVAL = "APPROVAL"
    UNKNOWN = "UNKNOWN"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    NONE = "NONE"

    def __eq__(self, other):
        return self.value == other.value


# In-progress statuses: excluded from settled rollup; drive the yellow "run" light.
IN_PROGRESS_VALUES = frozenset({
    CiResult.RUNNING.value,
    CiResult.WAITING.value,
})


class IntegrationType(Enum):
    GITHUB = "GITHUB"
    CIRCLECI = "CIRCLECI"


class BuildStatus(TypedDict):
    type: IntegrationType
    vcs: str
    id: str | int
    name: str
    start: str
    status: CiResult


class IntegrationAdapter(ABC):
    username: str
    repo: str

    @abstractmethod
    def get_type(self) -> IntegrationType:
        pass

    @abstractmethod
    async def get_latest(self, session: ClientSession) -> list[BuildStatus]:
        logging.info(f'Initiating integration {self.get_type()}')

    async def open_pull_requests(self, session: ClientSession) -> OpenPullRequests:
        return None, None

    async def security_findings(self, session: ClientSession) -> SecurityFindings | None:
        """Dependabot + CodeQL counts. GitHub only; GitLab/CircleCI stay None."""
        return None


class APIError(Exception):
    """An API Error Exception"""

    def __init__(self, verb, url, status, **kwargs):
        self.verb = verb
        self.url = url
        self.status = status
        self.text = kwargs.get("text") or ""

    def __str__(self):
        return f'APIError: {self.verb} {self.url} {self.status}{self.text}'
