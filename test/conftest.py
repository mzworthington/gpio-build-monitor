import pytest

from monitor.gpio.constants import reset_pins


@pytest.fixture(autouse=True)
def _set_integration_tokens(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    monkeypatch.setenv("CIRCLE_CI_TOKEN", "secret")


@pytest.fixture(autouse=True)
def _reset_gpio_pins():
    reset_pins()
    yield
    reset_pins()
