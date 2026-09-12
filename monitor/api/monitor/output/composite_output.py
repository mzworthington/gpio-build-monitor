#!/usr/bin/env python3

import logging
from collections.abc import Sequence

from monitor.output.port import StatusOutput
from monitor.service.aggregator_service import BuildDetail, Result


class CompositeStatusOutput:
    """Fans status updates out to every configured output adapter."""

    def __init__(self, outputs: list[StatusOutput]):
        if not outputs:
            raise ValueError("CompositeStatusOutput requires at least one output")
        self._outputs = outputs

    async def begin_fetch(self) -> None:
        await self._fan_out("begin_fetch")

    async def end_fetch(self) -> None:
        await self._fan_out("end_fetch")

    async def publish(
        self,
        status: Result,
        *,
        is_running: bool,
        builds: Sequence[BuildDetail] | None = None,
    ) -> None:
        for output in self._outputs:
            try:
                await output.publish(status, is_running=is_running, builds=builds)
            except Exception:
                logging.exception(
                    "Status output %s failed during publish",
                    type(output).__name__,
                )

    async def _fan_out(self, method_name: str) -> None:
        for output in self._outputs:
            try:
                await getattr(output, method_name)()
            except Exception:
                logging.exception(
                    "Status output %s failed during %s",
                    type(output).__name__,
                    method_name,
                )
