#!/usr/bin/env python3

import asyncio

from gpio_pi.app import run


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
