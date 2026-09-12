#!/usr/bin/env python3

import asyncio
import logging


class RefreshSignal:
    """Coalescing wake-up used by the monitor loop.

    Callers (webhook ingress, tests) notify without knowing about CI adapters
    or GPIO. The run loop waits for a notify or a reconcile timeout.
    """

    def __init__(self) -> None:
        self._event = asyncio.Event()

    def notify(self, reason: str = "manual") -> None:
        logging.info("Refresh requested (%s)", reason)
        self._event.set()

    async def wait(self, timeout: float) -> bool:
        """Wait until notified or ``timeout`` seconds elapse.

        Returns True when woken by ``notify``, False on timeout.
        Notifications that arrive while a refresh is already running remain
        set so the next wait returns immediately.
        """
        if self._event.is_set():
            self._event.clear()
            return True

        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
        except TimeoutError:
            return False

        self._event.clear()
        return True
