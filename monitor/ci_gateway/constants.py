#!/usr/bin/env python3
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import TypedDict

from aiohttp import ClientSession


class CiResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    RUNNING = "RUNNING"
    UNKNOWN = "UNKNOWN"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    NONE = "NONE"

    def __eq__(self, other):
        return self.value == other.value


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


class APIError(Exception):
    """An API Error Exception"""

    def __init__(self, verb, url, status, **kwargs):
        self.verb = verb
        self.url = url
        self.status = status
        self.text = kwargs.get("text") or ""

    def __str__(self):
        return f'APIError: {self.verb} {self.url} {self.status}{self.text}'
