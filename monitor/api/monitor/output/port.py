#!/usr/bin/env python3

from collections.abc import Sequence
from typing import Protocol

from monitor.service.aggregator_service import BuildDetail, Result


class StatusOutput(Protocol):
    """Outbound port for presenting aggregated CI status."""

    async def begin_fetch(self) -> None:
        """Indicate that a poll cycle has started."""

    async def end_fetch(self) -> None:
        """Indicate that fetching has finished (success or failure)."""

    async def publish(
        self,
        status: Result,
        *,
        is_running: bool,
        builds: Sequence[BuildDetail] | None = None,
    ) -> None:
        """Present the latest aggregated build status."""
