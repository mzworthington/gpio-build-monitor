#!/usr/bin/env python3

if __debug__:
    from monitor.gpio.Mock import GPIO
else:
    from RPi import GPIO

import asyncio
import logging

from .constants import Lights


class Board:
    def __enter__(self):
        logging.info('Setting up GPIO')
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
        logging.debug(f'Light {light} turning on...')
        self.GPIO.output(light.pin, self.GPIO.HIGH)
        logging.debug(f'Light {light} on')

    async def pulse(self, light: Lights):
        pin = light.pin
        if pin in self.tasks:
            logging.debug(f'Light {light} is already pulsing.')
            return

        dc = 0
        pwm = self.pwm.get(pin)
        if pwm is None:
            logging.error(f'Failed to pulse light {light}')
            return

        pwm.start(dc)

        self.tasks[pin] = asyncio.create_task(pulse(pwm))
        logging.debug(f'Light {light} pulsing...')
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

        logging.debug(f'Light {light} turning off...')
        self.GPIO.output(pin, self.GPIO.LOW)
        logging.debug(f'Light {light} off')

    def __exit__(self, type, value, traceback):
        logging.info('Cleaning up GPIO')
        self.GPIO.cleanup()


async def pulse(pwm):
    while True:
        for dc in range(0, 101, 5):
            pwm.ChangeDutyCycle(dc)
            await asyncio.sleep(0.05)
        for dc in range(95, 0, -5):
            pwm.ChangeDutyCycle(dc)
            await asyncio.sleep(0.05)
