# Xteink X3 (CrossPoint Build monitor)

Glanceable CI on a pocket e-reader. The device of record is the **X3**
(ESP32-C3, 3.68" 792×528 UC8253). Aggregation stays on the Worker. The reader
firmware is CrossPoint plus a Build monitor overlay in this repo. Do not run
the Pi poller on the ESP32.

```
GitHub / CircleCI ──► StatusHub (Worker, always on)
                           │  GET /status?view=eink
                           ▼
                     CrossPoint on X3
                     home → Build monitor
```

GPIO LEDs stay on the Pi. Nothing in `monitor/` drives the e-ink panel.

## Firmware

Overlay: [`monitor/device/eink/apps/monitor/`](../monitor/device/eink/apps/monitor/). Shared
parser tests: `make test-eink`. Flash:

```shell
monitor/device/eink/apps/monitor/flash.sh
```

Do not use `pio run -t upload`. PlatformIO's port hunt drops native USB CDC
on this chip. The script builds first, then calls esptool as soon as
`/dev/cu.usbmodem*` appears. For serial logs:

```shell
monitor/device/eink/apps/monitor/debug.sh
```

Wi-Fi is CrossPoint **Settings → System → Wi-Fi Networks** (up to 8 saved
SSIDs on the SD card). Send a User-Agent on `GET /status`; Cloudflare 403s
empty UA strings.

Idle sleep is CrossPoint **Settings → System → Time to sleep**. Wake is a
full reset; the activity stack does not survive. Set **Never** while flashing.

## Pins

| Function | GPIO |
|----------|------|
| EPD SCLK / MOSI / MISO / CS / DC / RST / BUSY | 8 / 10 / 7 / 21 / 4 / 5 / 6 |
| I²C SCL / SDA | 0 / 20 (BQ27220 at 0x55) |
| Power button | 3 (LOW = pressed) |
| Page keys | ADC GPIO 1 and 2 |
| Power latch | 13 HIGH = on |

USB is native CDC (`/dev/cu.usbmodem*`). Never `/dev/cu.Bluetooth-Incoming-Port`.
