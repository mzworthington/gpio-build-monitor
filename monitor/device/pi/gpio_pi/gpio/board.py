#!/usr/bin/env python3

if __debug__:
    from gpio_pi.gpio.Mock import GPIO
else:
    from RPi import GPIO

import asyncio
import logging

from .constants import Lights, configure_pins


class Board:
    def __init__(self, pin_overrides: dict[str, int] | None = None) -> None:
        self._pin_overrides = None if pin_overrides is None else dict(pin_overrides)

    def __enter__(self):
        logging.info("Setting up GPIO")
        configure_pins(self._pin_overrides)
        self.GPIO = GPIO

        self.GPIO.setmode(GPIO.BCM)
        self.GPIO.setwarnings(False)

        self.pwm = {}
        for light in Lights:
            pin = light.pin
            self.GPIO.setup(
                pin,
                self.GPIO.OUT,
                initial=self.GPIO.LOW)

            self.pwm[pin] = self.GPIO.PWM(
                pin,
                100)

        self.tasks = {}

        return self

    def on(self, light: Lights):
        logging.debug("Light %s turning on...", light)
        self.GPIO.output(light.pin, self.GPIO.HIGH)

    async def pulse(self, light: Lights):
        pin = light.pin
        if pin in self.tasks:
            logging.debug("Light %s is already pulsing.", light)
            return

        dc = 0
        pwm = self.pwm.get(pin)
        if pwm is None:
            logging.error("Failed to pulse light %s", light)
            return

        pwm.start(dc)

        self.tasks[pin] = asyncio.create_task(pulse(pwm))
        await asyncio.sleep(0.001)

    def off(self, light: Lights):
        pin = light.pin
        pwm = self.pwm.get(pin)
        if pwm is not None:
            pwm.stop()

        task = self.tasks.get(pin)
        if task is not None:
            task.cancel()
            self.tasks.pop(pin)

        logging.debug("Light %s turning off...", light)
        self.GPIO.output(pin, self.GPIO.LOW)

    def __exit__(self, type, value, traceback):
        logging.info("Cleaning up GPIO")
        self.GPIO.cleanup()


async def pulse(pwm):
    while True:
        for dc in range(0, 101, 5):
            pwm.ChangeDutyCycle(dc)
            await asyncio.sleep(0.05)
        for dc in range(95, 0, -5):
            pwm.ChangeDutyCycle(dc)
            await asyncio.sleep(0.05)
