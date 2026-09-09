# Xteink X3 firmware

Battery client for the hosted (or local) status snapshot. Architecture:
[docs/xteink-x4.md](../../docs/xteink-x4.md) (same duty cycle as the X4).

This sketch targets the **X3 only**: 3.68" 792×528 UC81xx (UC8253), pogo charging,
BQ27220 on I²C. Do not flash it onto an X4. The X4 sketch lives in
[`device/x4/`](../x4/). Newer X3 panels with a **UC8279d** controller are not
supported.

## One-time

1. Keep a stock/CrossPoint `update.bin` on a FAT32 microSD card before the first
   flash. There is no public full stock image.
2. Copy `include/secrets.h.example` to `include/secrets.h` and set Wi-Fi plus
   the snapshot URL.
3. Build and upload:

```shell
cd device/x3
pio device list
pio run -t upload
pio device monitor
```

`pio run -t upload` must use a `/dev/cu.usbmodem*` port. Do **not** choose
`/dev/cu.Bluetooth-Incoming-Port` (Mac Bluetooth serial). If `pio device list` still has no `usbmodem` port, USB is asleep, the cable is
charge-only, or CDC is locked. Copy the image to a FAT32 card and boot it:

```shell
cd device/x3
pio run
make copy-sd SD=/Volumes/YOUR_CARD   # card must already be mounted
```

Or copy `.pio/build/xteink-x3/firmware.bin` to the card root as `update.bin`.
Eject, insert in the X3, hold **Power + top-left** at boot. Keep a stock
`update.bin` backup first.

Apple Silicon: this sketch uses the pioarduino Espressif 32 platform (Arduino
3.1.3) so GCC 13 and newlib match, and the RISC-V compiler is `darwin_arm64`.
Homebrew PlatformIO also needs `platformio/tool-esptoolpy` instead of
pioarduino’s esptool zip (that zip’s postinstall script fails on 6.2).
Do not pin `espressif32@6.10` plus a standalone GCC 13 — that mix fails to
link `_cleanup_r`. First download of the Arduino core can take a few minutes.

Wake the X3 with the **power** button. After a USB or SD flash, that boots
this sketch from flash — not CrossPoint — every time. You should see
**Build monitor / Connecting**, then the status page.

Leave `update.bin` off the card once the image is installed. Power + top-left
only when you intend to flash; that combo rewrites flash from the card.

## Buttons

| Action | What happens |
|--------|----------------|
| Power (short) | Wakes the unit from off |
| Power (hold ~1.2s) | Draws **Off**, waits for release, then GPIO 13 LOW (battery latch) |

Unplug the pogo cable to test off. Magnetic USB keeps the 3.3 V rail up, so
GPIO 13 LOW cannot look like a shutdown while charging. On battery the MCU
loses power (RTC included); power is a hard-wired pulse back onto the rail.
| Next page (or any page key) | Draws **Refreshing**, then fetches `/status` again |

Page keys are an ADC ladder on GPIO 1 (and GPIO 2). They cannot wake a fully
powered-off chip; press **power** first.

USB-locked units: copy `.pio/build/xteink-x3/firmware.bin` to the card root as
`update.bin` and hold **Power + top-left** at boot.

Use HTTP against `bin/serve` (`http://<lan-ip>:8080/status?view=eink`) for the
first bring-up so you can skip TLS. Production is
`https://monitor.mzworthington.co.uk/status?view=eink`.

Send a `User-Agent`. Cloudflare 403s clients that look like default Python or
empty UA strings.

## Pins

| Function | GPIO |
|----------|------|
| EPD SCLK / MOSI / CS / DC / RST / BUSY | 8 / 10 / 21 / 4 / 5 / 6 |
| I²C SCL / SDA | 0 / 20 (BQ27220 at 0x55) |
| Power button (deep-sleep wakeup) | 3 (LOW = pressed) |
| Page keys (refresh) | ADC GPIO 1 and 2 (resistor ladders) |
| Power latch | 13 HIGH = on; hold LOW to shut down |

SPI is 10 MHz. GPIO 0/20 are **not** the X4 battery/USB pins. Newer X3 panels
with a UC8279d controller are not in this sketch.

Do not hold non-RTC GPIOs across deep sleep; that leaks milliamps on ESP32-C3.

Shared sleep / ETag logic lives in [`device/eink/`](../eink/) (`make test-x4`
from the repo root).
