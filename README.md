# GPIO build monitor

A Raspberry Pi build monitor that polls CI providers and drives coloured LEDs to show build status. Run it on a Pi with real GPIO hardware, or on your laptop with a mock GPIO layer for development.

Supported CI providers:

- GitHub Actions
- CircleCI (API v2)

## How it works

1. Load `integrations.json` and validate required API tokens.
2. Poll each configured repo on a fixed interval (`poll_in_seconds`).
3. Aggregate results across all integrations.
4. Update LEDs:
   - **Blue** — fetching status
   - **Green** — all non-running builds passed
   - **Red** — at least one build failed
   - **Yellow (pulse)** — at least one build is running
   - **Purple** — connection or API error (polling continues)

On your development machine, Python runs without `-O`, so the mock GPIO module is used. On the Pi, run with `python -O` so the real `RPi.GPIO` library is loaded.

## Prerequisites

- Python 3.10+ ([mise](https://mise.jdx.dev/) is recommended and pins 3.12 in this repo)
- API tokens for the providers you configure (see [Environment variables](#environment-variables))

## Local development

```shell
bin/bootstrap
cp monitor/integrations.example.json monitor/integrations.json   # skipped if bootstrap already created it
# edit monitor/integrations.json and export tokens (see below)
monitor check-config
bin/serve
```

`bin/bootstrap` installs Python via mise (if available), creates `.venv`, installs the package in editable mode with dev dependencies, and copies `monitor/integrations.example.json` to `monitor/integrations.json` when that file does not exist.

`bin/serve` runs `monitor run` with:

- `--conf monitor/integrations.json` (override with `CONF_FILE`)
- `--log-level debug` (override with `LOG_LEVEL`)

Equivalent commands:

```shell
make bootstrap
make serve          # same as bin/serve
make test           # ruff + pytest
make publish        # lint, test, then build sdist/wheel
```

With mise:

```shell
mise run bootstrap
mise run serve
mise run test
```

## CLI

The `monitor` command is provided by [Typer](https://typer.tiangolo.com/):

```shell
monitor --help
monitor run --conf monitor/integrations.json --log-level debug
monitor check-config --conf monitor/integrations.json
```

`monitor run` starts the polling loop. `monitor check-config` validates the config file and required environment variables without touching GPIO.

You can also use the module directly:

```shell
python -m monitor run --conf monitor/integrations.json
python -m monitor check-config
```

## Configuration

`monitor/integrations.json` is local to your machine and gitignored. Start from the example:

```shell
cp monitor/integrations.example.json monitor/integrations.json
```

Example structure:

```json
{
  "poll_in_seconds": 30,
  "log_dir": "logs",
  "pins": {
    "GREEN": 17,
    "YELLOW": 18,
    "BLUE": 22,
    "RED": 27,
    "PURPLE": 23
  },
  "integrations": [
    {
      "type": "GITHUB",
      "username": "your-github-org",
      "repo": "your-repo",
      "excluded_workflows": []
    },
    {
      "type": "CIRCLECI",
      "username": "your-circle-org",
      "repo": "your-repo",
      "excluded_workflows": ["nightly-scan"]
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `poll_in_seconds` | Seconds between poll cycles (default: 30) |
| `log_dir` | Directory for `monitor.log` (default: `logs/`) |
| `pins` | Optional BCM pin overrides per light name |
| `integrations` | List of repos to monitor |
| `integrations[].type` | `GITHUB` or `CIRCLECI` |
| `integrations[].excluded_workflows` | Workflow names to ignore (optional) |

### Environment variables

Tokens are read from the environment, not stored in the config file:

```shell
export GITHUB_TOKEN=...
export CIRCLE_CI_TOKEN=...
```

Only set the variables for providers present in your config. `monitor check-config` fails fast if any are missing.

Optional:

| Variable | Purpose |
|----------|---------|
| `MONITOR_LOG_DIR` | Default log directory when `log_dir` is not set in config |
| `LOG_LEVEL` | Log level for `bin/serve` (default: `debug`) |
| `CONF_FILE` | Config path for `bin/serve` (default: `monitor/integrations.json`) |
| `MONITOR_HOME` | Pi install directory (default: `/home/pi/gpio-build-monitor`) |
| `MONITOR_VENV` | Virtualenv used on the Pi (default: `$MONITOR_HOME/.venv`) |
| `MONITOR_SERVICE` | systemd unit name (default: `gpio-build-monitor`) |
| `GITHUB_REPO` | Repository checked for releases (default: `worthington10TW/gpio-build-monitor`) |
| `MONITOR_UPDATE_LOG` | Auto-update log file (default: `/var/log/gpio-build-monitor/update.log`) |

Logs are written to `<log_dir>/monitor.log` and stdout.

## Raspberry Pi setup

1. Clone the repo and bootstrap on the Pi:

   ```shell
   bin/bootstrap
   ```

2. Install the GPIO library:

   ```shell
   pip install RPi.GPIO
   ```

3. Create your config and set tokens in the shell or an env file.

4. Validate and run (note `-O` for real GPIO):

   ```shell
   monitor check-config --conf monitor/integrations.json
   python -O -m monitor run --conf monitor/integrations.json --log-level info
   ```

### systemd service

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

### Auto-updates (Raspberry Pi)

The Pi can poll GitHub Releases for a newer version, install the release wheel, and restart the monitor service. This is handled by `bin/update` and an optional systemd timer.

**How it works**

1. Query the GitHub Releases API for the latest tag.
2. Compare it with the installed `monitor` package version in `.venv`.
3. If a newer release exists, download the `monitor-*.whl` asset from that release.
4. `systemctl stop gpio-build-monitor`
5. `pip install --upgrade` the wheel into `.venv`
6. `systemctl start gpio-build-monitor`

Polling continues even when CI APIs fail — only the monitor package is restarted during an upgrade.

**One-time setup**

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

**Manual update check**

```shell
bin/update --check    # exit 0 if up to date, 10 if an update is available
bin/update            # install now if a newer release exists
```

**Logs**

Update activity is appended to `/var/log/gpio-build-monitor/update.log` by default.

**Requirements**

- A published GitHub Release whose tag matches `vX.Y.Z` in `pyproject.toml`
- A `monitor-*.whl` asset attached to that release (created automatically by CI)
- Outbound HTTPS access to `api.github.com` and `github.com`

To change the schedule, edit `OnCalendar` in `deploy/gpio-build-monitor-update.timer` and run `sudo systemctl daemon-reload`.

## Installing from GitHub

```shell
pip install git+https://github.com/worthington10TW/gpio-build-monitor
monitor run --help
```

Dependencies are declared in `pyproject.toml`.

## Releases

CI runs on pushes and pull requests to `main`. Pushing a tag `vX.Y.Z` that matches the version in `pyproject.toml` triggers a GitHub Release with built wheel and sdist artifacts.

```shell
# bump version in pyproject.toml, commit, then:
git tag v0.2.0
git push origin main
git push origin v0.2.0
```

## Development

```shell
make lint           # ruff
make test           # ruff + pytest
pre-commit install  # optional: ruff on commit, pytest on push
```

Dependabot opens weekly update PRs for Python and GitHub Actions dependencies.

## Hardware

![my build](build_monitor.jpg)

Default BCM pins (configurable via `pins` in `integrations.json`):

| Light | Default pin |
|-------|-------------|
| Green | 17 |
| Yellow | 18 |
| Blue | 22 |
| Red | 27 |
| Purple | 23 |

### Shopping list

#### The monitor

- [Raspberry Pi Zero](https://thepihut.com/products/raspberry-pi-zero-w?src=raspberrypi)
- [SD card](https://www.amazon.co.uk/Kingston-microSD-SDCS2-Adapter-Included/dp/B07YGZ7FY7/)
- [Resistor kit](https://thepihut.com/products/ultimate-resistor-kit)
- [LED kit](https://thepihut.com/products/ultimate-5mm-led-kit)
- [Cables](https://thepihut.com/products/thepihuts-jumper-bumper-pack-120pcs-dupont-wire)
- [Breadboard](https://thepihut.com/products/raspberry-pi-breadboard-half-size)
- [Shrink cables](https://thepihut.com/products/multi-colored-heat-shrink-pack-3-32-1-8-3-16-diameters)

#### Useful kit

- [Anti-static band](https://www.amazon.co.uk/gp/product/B07TGD5CD8/)
- [Rubber mat](https://www.amazon.co.uk/gp/product/B075D9R8PZ/)
- [Soldering iron](https://www.amazon.co.uk/gp/product/B07X3CZ3FJ/)
- [Multimeter](https://www.amazon.co.uk/gp/product/B01N35ZVKY/)

#### The housing

- [Frame](https://www.ikea.com/gb/en/p/ribba-frame-white-80378423/)
