#!/usr/bin/env python3

import asyncio
import enum
import logging
from typing import TypedDict

from aiohttp import ClientSession

import monitor.ci_gateway.constants as ci_constants
from monitor.ci_gateway.constants import BuildStatus, CiResult, IntegrationAdapter


class Result(enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    NONE = "NONE"

    def __eq__(self, other):
        return self.value == other.value


def get_status(results: list[BuildStatus]) -> Result:
    if len(results) == 0:
        return Result.NONE
    if any(r['status'] == CiResult.CONNECTION_ERROR for r in results):
        return Result.CONNECTION_ERROR
    if any(r['status'] == CiResult.FAIL for r in results):
        return Result.FAIL
    if all(r['status'] == CiResult.PASS for r in results):
        return Result.PASS
    return Result.UNKNOWN


class OverallStatus(TypedDict):
    type: str
    is_running: bool
    status: Result


class AggregatorService:
    def __init__(self, integrations: list[IntegrationAdapter]):
        self.integrations = integrations

    async def run(self, session: ClientSession) -> OverallStatus:
        tasks = [
            asyncio.create_task(self._fetch(session, integration))
            for integration in self.integrations
        ]
        completed = await asyncio.gather(*tasks)

        result: list[BuildStatus] = []
        for integration_results in completed:
            result.extend(integration_results)

        return OverallStatus(
            type="AGGREGATED",
            is_running=any(
                r['status'] == ci_constants.CiResult.RUNNING for r in result),
            status=get_status(
                [
                    build
                    for build in result
                    if build['status'] != ci_constants.CiResult.RUNNING
                ]))

    async def _fetch(
        self,
        session: ClientSession,
        integration: IntegrationAdapter,
    ) -> list[BuildStatus]:
        label = (
            f"{integration.get_type().name}:"
            f"{integration.username}/{integration.repo}"
        )
        try:
            return await integration.get_latest(session)
        except Exception:
            logging.exception('Failed to fetch build status for %s', label)
            return [self._connection_error_status(integration)]

    @staticmethod
    def _connection_error_status(
        integration: IntegrationAdapter,
    ) -> BuildStatus:
        return BuildStatus(
            type=integration.get_type(),
            vcs="",
            id="",
            name=f"{integration.username}/{integration.repo}",
            start="",
            status=CiResult.CONNECTION_ERROR,
        )
