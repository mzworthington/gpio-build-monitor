#!/usr/bin/env python3

import enum

_DEFAULT_PINS: dict[str, int] = {
    "GREEN": 17,
    "YELLOW": 18,
    "BLUE": 22,
    "RED": 27,
    "PURPLE": 23,
}

_pins: dict[str, int] = dict(_DEFAULT_PINS)


class Lights(enum.Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    BLUE = "BLUE"
    RED = "RED"
    PURPLE = "PURPLE"

    @property
    def pin(self) -> int:
        return _pins[self.name]

    def __str__(self):
        return f"{{ Colour: {self.name}, Pin: {self.pin} }}"


def configure_pins(overrides: dict[str, int] | None) -> None:
    global _pins
    _pins = dict(_DEFAULT_PINS)
    if not overrides:
        return
    for name, pin in overrides.items():
        if name not in _pins:
            raise ValueError(f"Unknown light '{name}' in pin configuration")
        if not isinstance(pin, int) or pin < 0:
            raise ValueError(f"Pin for {name} must be a non-negative integer")
        _pins[name] = pin


def reset_pins() -> None:
    global _pins
    _pins = dict(_DEFAULT_PINS)
