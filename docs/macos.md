# Mac menu bar (SwiftBar)

Glanceable CI status in the macOS menu bar — same colours as the desk LEDs,
without running the Pi poller on your laptop.

The plugin reads the public snapshot at
`https://monitor.mzworthington.co.uk/status` (or your local monitor). It does
not need GitHub tokens.

## Install

1. Install [SwiftBar](https://github.com/swiftbar/SwiftBar).
2. Point SwiftBar at a plugins folder (or use the default).
3. Symlink **both** files from this repo so the plugin can import `menu_bar.py`:

```shell
PLUGINS="$HOME/Documents/swiftbar"
mkdir -p "$PLUGINS"
ln -sf "$(pwd)/macos/gpio-build-monitor.30s.py" "$PLUGINS/"
ln -sf "$(pwd)/macos/menu_bar.py" "$PLUGINS/"
chmod +x macos/gpio-build-monitor.30s.py
```

Use the plugins folder SwiftBar is actually configured to watch (SwiftBar → Preferences). The `.30s` suffix tells SwiftBar to refresh every 30 seconds.

## Local monitor

If you are running `bin/serve` instead of the hosted Worker:

```shell
# SwiftBar → Preferences → Environment
GPIO_MONITOR_STATUS_URL=http://127.0.0.1:8080/status
GPIO_MONITOR_DASHBOARD_URL=http://127.0.0.1:8080
```

## How the title maps

| Menu bar | Meaning |
|----------|---------|
| Green `PASS` | All settled builds passed |
| Red `FAIL` / `UNK` | A build failed (red wins over a running rebuild) |
| Yellow `RUN` / `WAIT` | Something is running or waiting for approval |
| Purple `ERR` | Snapshot fetch failed, or CI connection error |
| Blue `…` | First fetch, nothing cached yet |
| Gray `IDLE` | No builds yet |

Click the extra for per-build links and **Open monitor**.
