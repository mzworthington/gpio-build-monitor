# Xteink X4 firmware

Battery client for the hosted (or local) status snapshot. Architecture:
[docs/xteink-x4.md](../../docs/xteink-x4.md).

This sketch is a duty-cycle reference, not a pixel-perfect UI. It compiles with
PlatformIO against GxEPD2; it has not been soak-tested on hardware in this
change.

## One-time

1. Back up the 16 MB factory flash (see the
   [open-x4-epaper sample](https://github.com/open-x4-epaper/sample-firmware)).
2. Copy `include/secrets.h.example` to `include/secrets.h` and set Wi-Fi plus
   the snapshot URL.
3. Build and upload:

```shell
cd device/x4
pio run -t upload
pio device monitor
```

Use HTTP against `bin/serve` (`http://<lan-ip>:8080/status?view=eink`) for the
first bring-up so you can skip TLS. Production is
`https://monitor.mzworthington.co.uk/status?view=eink`.

Send a `User-Agent`. Cloudflare 403s clients that look like default Python or
empty UA strings.

## Pins (from the open-x4-epaper sample)

| Function | GPIO |
|----------|------|
| EPD SCLK / MOSI / CS / DC / RST / BUSY | 8 / 10 / 21 / 4 / 5 / 6 |
| Battery divider | 0 |
| USB detect | 20 (HIGH = charging) |
| Power button (deep-sleep wakeup) | 3 (LOW = pressed) |

Do not hold non-RTC GPIOs across deep sleep; that leaks milliamps on ESP32-C3.

## What it does

Each boot: connect Wi-Fi, `GET` the snapshot with `If-None-Match`, redraw only
on `200`, then `esp_wifi_stop()` and deep-sleep for `Retry-After` seconds.
GPIO3 and the RTC timer are the wakeup sources.
