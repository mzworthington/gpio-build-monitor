# Configuration

`monitor/integrations.json` is local to your machine and gitignored. Start from the example:

```shell
cp monitor/integrations.example.json monitor/integrations.json
```

## Example

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

## Fields

| Field | Description |
|-------|-------------|
| `poll_in_seconds` | Seconds between poll cycles (default: 30) |
| `log_dir` | Directory for `monitor.log` (default: `logs/`) |
| `pins` | Optional BCM pin overrides per light name |
| `integrations` | List of repos to monitor |
| `integrations[].type` | `GITHUB` or `CIRCLECI` |
| `integrations[].excluded_workflows` | Workflow names to ignore (optional) |

## Environment variables

Tokens are read from the environment, not stored in the config file:

```shell
export GITHUB_TOKEN=...
export CIRCLE_CI_TOKEN=...
```

Only set the variables for providers present in your config. `monitor check-config` fails fast if any are missing.

### Optional

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
