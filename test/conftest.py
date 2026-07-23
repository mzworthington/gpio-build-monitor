"""Test configuration and shared fixtures."""

import inspect
from unittest.mock import Mock

import pytest
from aiohttp.client_reqrep import ClientResponse

from monitor.gpio.constants import reset_pins

# aioresponses 0.7.x constructs ClientResponse without stream_writer, which
# aiohttp 3.14+ requires. Remove once aioresponses ships a fix (pnuckowski/aioresponses#288).
if "stream_writer" in inspect.signature(ClientResponse.__init__).parameters:
    _original_client_response_init = ClientResponse.__init__

    def _client_response_init(self, *args, **kwargs):
        kwargs.setdefault("stream_writer", Mock(output_size=0))
        return _original_client_response_init(self, *args, **kwargs)

    ClientResponse.__init__ = _client_response_init  # type: ignore[method-assign]


@pytest.fixture(autouse=True)
def _set_integration_tokens(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    monkeypatch.setenv("CIRCLE_CI_TOKEN", "secret")


@pytest.fixture(autouse=True)
def _reset_gpio_pins():
    reset_pins()
    yield
    reset_pins()
