# Xteink X4 (battery e-ink)

Glanceable CI on a pocket e-reader, without turning the device into a second Pi.

The Xteink X4 is an ESP32-C3 board (400 KB SRAM, no PSRAM, 16 MB flash) with a
4.26" 800×480 SSD1677 panel and a 650 mAh cell. The panel holds an image at
zero power. The radio and CPU do not. That is the whole architectural constraint.

## Why the Pi loop does not move onto the X4

The Raspberry Pi composition is an always-on process:

```
webhook or timer → poll GitHub/CircleCI → aggregate → GPIO / WebSocket → wait
```

That duty cycle assumes mains power, tens of MB of RAM, and a process that
survives between polls. The X4 has none of those:

| Constraint | Consequence |
|------------|-------------|
| 650 mAh, deep sleep ~ tens of µA, Wi-Fi TX ~150–300 mA | Radio must be off almost all of the time |
| Deep sleep resets the CPU | There is no `while True` run loop and no inbound webhook socket |
| 327 KB usable SRAM | No Python aggregator, no TLS session to GitHub, no 800×480 grayscale canvas plus Wi-Fi stack |
| E-ink | Pulse/yellow fetch lights do not exist; a refresh costs power and panel wear |

The hosted Worker already owns aggregation, webhooks, and `GET /status`. The Mac
menu bar is the existing pattern: a thin client of that snapshot. The X4 is the
same port, with a sleep policy.

```
GitHub / CircleCI ──► StatusHub (Worker, always on)
       webhooks ──►        │
                           │  GET /status?view=eink
                           │  If-None-Match / ETag
                           │  Retry-After = sleep_seconds
                           ▼
                     Xteink X4 firmware
                     wake → Wi-Fi → sample → maybe redraw → radio off → deep sleep
```

GPIO LEDs and the browser UI stay on their adapters. Nothing in `monitor/`
starts driving the e-ink panel.

## Duty cycle

RTC timer (and GPIO3, the power button) are the only wakeup sources. ADC
buttons cannot wake the chip.

```
timer / power button
  → restore RTC state (ETag, fail streak, full-refresh counter)
  → Wi-Fi STA on
  → GET /status?view=eink  (User-Agent required; Cloudflare 403s anonymous clients)
      If-None-Match: <last ETag>
  → 304: leave the panel alone (image is still on glass)
  → 200: render 1-bit buffer; full refresh every N updates or on FAIL, else partial
  → Wi-Fi off (esp_wifi_stop). Do not gpio_deep_sleep_hold on non-RTC pins.
  → sleep_seconds from JSON / Retry-After (local backoff if the GET failed)
  → arm timer + GPIO3 LOW wakeup
  → esp_deep_sleep_start()
```

On a failed fetch, keep the last image. E-ink already shows it; a spinner would
only cost a refresh. Double the previous interval, cap at 30 minutes.

`poll_in_seconds` on the hub (30–60 s) is the Worker’s reconcile cadence, not
the device sleep. The hub stays warm via webhooks; the X4 only samples.

### Sleep policy

Mirrored in `monitor/service/snapshot.py` and `worker/src/snapshot.ts`:

| Snapshot | Deep sleep |
|----------|------------|
| `is_running` | 2 min (catch completion) |
| `FAIL` / `UNKNOWN` / `APPROVAL` | 3 min |
| `CONNECTION_ERROR` (CI APIs, not the device radio) | 5 min |
| `PASS` / `NONE` | 15 min |

USB on GPIO20 can shorten that locally (desk mode). Do not keep the radio
associated in modem-sleep; on this cell that would drain in hours, not weeks.

Budget (order of magnitude): ~10 s awake at ~150 mA is ~0.4 mAh per wake.
Ninety-six wakes/day at 15 min is ~40 mAh, plus ~1 mAh/day sleeping. The 650 mAh
pack is then measured in weeks if Wi-Fi association stays short and 304s skip
panel updates.

## Snapshot contract

Same JSON shape as the Mac extra and the first `/ws` message, plus battery
fields:

| Field / header | Role |
|----------------|------|
| `status`, `is_running`, `builds` | Glanceable roll-up (same enum as the LEDs) |
| `sleep_seconds` | Seconds to deep-sleep after this sample |
| `Retry-After` | Same value, so a 304 still carries the interval |
| `ETag` | Weak hash of status + running + builds (not `fetching` or timestamps) |
| `If-None-Match` | Device sends last ETag; `304` means skip the panel |
| `GET /status?view=eink` | Drops passing workflows; keeps FAIL / error / approval / unknown / running / waiting |

No GitHub or CircleCI tokens on the device. Credentials are Wi-Fi SSID/PSK
only.

## Firmware

Sketch in [`device/x4/`](../device/x4/). Stack is Arduino/PlatformIO + GxEPD2
(same pins as [open-x4-epaper/sample-firmware](https://github.com/open-x4-epaper/sample-firmware)).
CircuitPython fits the board but leaves too little SRAM for HTTPS plus an
800×480 framebuffer.

Host tests (`make test-x4`) cover the sleep / ETag / snapshot parser without
flashing a device.

Flash notes, pin map, and bring-up: [`device/x4/README.md`](../device/x4/README.md).
Back up the factory image before the first upload.
