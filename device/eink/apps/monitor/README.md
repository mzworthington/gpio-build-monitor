# CrossPoint Build monitor activity

A `UiListActivity` that fetches `GET /status?view=eink`, parses it with the
shared `device/eink` library, and lists jobs plus open PRs.

Keep the CrossPoint submodule on upstream. Overlay lives here:
`patches/home-build-monitor.patch` plus `MonitorActivity`. `pio run` applies the
patch, compiles, then restores CrossPoint sources after `firmware.bin` is
linked (not at extra_script import).

## Wire-up

1. Copy the local overlay into the submodule (gitignored as `*.local*`):

```shell
cp device/eink/apps/monitor/platformio.local.ini.example \
   device/eink/crosspoint/platformio.local.ini
```

Do not let the PlatformIO IDE rewrite `platformio.ini`.

2. Connect Wi-Fi from CrossPoint **Settings → System → Wi-Fi Networks**.
3. Edit `MONITOR_STATUS_URL` in `platformio.local.ini` if you are not using
   `https://monitor.mzworthington.co.uk/status?view=eink`.
4. Flash from the repo root (CDC on the X3 vanishes if PlatformIO hunts for
   a port for ~12s):

```shell
device/eink/apps/monitor/flash.sh
```

Hold **Boot/Select**, tap Reset or power, keep Boot held until you see
`flashing`. Or copy `.pio/build/default/firmware.bin` to the SD card as
`update.bin` and boot with **Power + top-left**.

5. From the home menu, open **Build monitor** (first row). Confirm (footer
   **Retry**) fetches `/status` again. Back returns to home.

USB serial (115200, after the device enumerates CDC):

```shell
device/eink/apps/monitor/debug.sh
```

Quit with Ctrl-]. Look for `HOME` / `MONITOR` lines. Do not use
`pio device monitor`; that port hunt drops CDC the same way upload does.

After a CrossPoint bump:

```shell
git -C device/eink/crosspoint checkout -- .
git -C device/eink/crosspoint submodule update --init --recursive
```

`pio run` reapplies the patch. If it fails, refresh
`patches/home-build-monitor.patch` against the new CrossPoint sources.

Keep a stock CrossPoint `update.bin` on the SD card before the first overlay
flash.
