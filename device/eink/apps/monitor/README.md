# CrossPoint Build monitor activity

A `UiListActivity` that fetches `GET /status?view=eink`, parses it with the
shared `device/eink` duty-cycle library, and lists jobs plus open PRs.

The pasted CrossPoint “desktop simulator / SDL2 / UiActivity / UiManager”
guide does not match this tree (CrossPoint 1.6.0). There is no
`[env:simulator]`. SDL2 is unused. Iterate on the X3 with PlatformIO
`default` (ESP32-C3, X3+X4 flags already on).

## Wire-up

1. Copy the local overlay into the submodule (gitignored as `*.local*`):

```shell
cp device/eink/apps/monitor/platformio.local.ini.example \
   device/eink/crosspoint/platformio.local.ini
```

2. Connect Wi-Fi from CrossPoint **Settings → System → Wi-Fi Networks**
   (this activity does not store an SSID).
3. Edit `MONITOR_STATUS_URL` in `platformio.local.ini` if you are not using
   `https://monitor.mzworthington.co.uk/status?view=eink`.
4. Build and flash the **reader** image (this replaces the standalone
   `device/x3` sketch):

```shell
cd device/eink/crosspoint
pio run -e default -t upload --upload-port /dev/cu.usbmodem*
pio device monitor -b 115200
```

5. Open **Settings → System → Build monitor**. Confirm/Select refreshes.
   Back returns to Settings.

Keep a stock CrossPoint `update.bin` on the SD card before the first overlay
flash.

The CrossPoint submodule is patched (`SettingAction::BuildMonitor`,
`STR_BUILD_MONITOR`) behind `-DGPIO_BUILD_MONITOR` so a stock build without
the local ini stays a reader.
