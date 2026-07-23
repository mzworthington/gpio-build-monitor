# Raspberry Pi

## Setup

1. Clone the repo and bootstrap on the Pi:

   ```shell
   bin/bootstrap
   ```

2. Install the GPIO library:

   ```shell
   pip install RPi.GPIO
   ```

3. Create your config and set tokens in the shell or an env file - see [Configuration](configuration.md).

4. Validate and run (note `-O` for real GPIO):

   ```shell
   monitor check-config --conf monitor/integrations.json
   python -O -m monitor run --conf monitor/integrations.json --log-level info
   ```

## systemd service

For a persistent service, use the unit file in `deploy/`:

```shell
sudo mkdir -p /etc/gpio-build-monitor
sudo cp deploy/env.example /etc/gpio-build-monitor/env
sudo cp monitor/integrations.json /etc/gpio-build-monitor/integrations.json
# edit /etc/gpio-build-monitor/env with your tokens
sudo cp deploy/gpio-build-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gpio-build-monitor
```

The unit file assumes the repo lives at `/home/pi/gpio-build-monitor`. Adjust `WorkingDirectory`, `ExecStart`, and `User` in `deploy/gpio-build-monitor.service` if your paths differ.

## Auto-updates

The Pi can poll GitHub Releases for a newer version, install the release wheel, and restart the monitor service. Handled by `bin/update` and an optional systemd timer.

### How it works

1. Query the GitHub Releases API for the latest tag.
2. Compare it with the installed `monitor` package version in `.venv`.
3. If a newer release exists, download the `monitor-*.whl` asset from that release.
4. `systemctl stop gpio-build-monitor`
5. `pip install --upgrade` the wheel into `.venv`
6. `systemctl start gpio-build-monitor`

Polling continues even when CI APIs fail - only the monitor package is restarted during an upgrade.

### One-time setup

Keep a git clone on the Pi so `bin/update` and the systemd unit files are present. The updater script itself is not installed via the wheel.

```shell
# allow the pi user to stop/start the service without a password
sudo cp deploy/sudoers-gpio-build-monitor /etc/sudoers.d/gpio-build-monitor
sudo chmod 0440 /etc/sudoers.d/gpio-build-monitor

# install the daily update timer (runs at 03:15, see deploy/gpio-build-monitor-update.timer)
sudo cp deploy/gpio-build-monitor-update.service /etc/systemd/system/
sudo cp deploy/gpio-build-monitor-update.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gpio-build-monitor-update.timer
```

Ensure `/etc/gpio-build-monitor/env` includes the auto-update variables from `deploy/env.example` (`MONITOR_HOME`, `MONITOR_VENV`, etc.).

### Manual update check

```shell
bin/update --check    # exit 0 if up to date, 10 if an update is available
bin/update            # install now if a newer release exists
```

### Logs and requirements

Update activity is appended to `/var/log/gpio-build-monitor/update.log` by default.

Requirements:

- A published GitHub Release whose tag matches `vX.Y.Z` in `pyproject.toml`
- A `monitor-*.whl` asset attached to that release (created automatically by CI)
- Outbound HTTPS access to `api.github.com` and `github.com`

To change the schedule, edit `OnCalendar` in `deploy/gpio-build-monitor-update.timer` and run `sudo systemctl daemon-reload`.
