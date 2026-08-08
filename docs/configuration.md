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
  "webhooks": {
    "enabled": false,
    "host": "0.0.0.0",
    "port": 8080
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
| `poll_in_seconds` | Seconds between reconcile polls (default: 30). With webhooks enabled, raise this (for example `300`) so polling is a fallback, not the primary cadence. |
| `log_dir` | Directory for `monitor.log` (default: `logs/`) |
| `pins` | Optional BCM pin overrides per light name |
| `webhooks` | Optional webhook ingress settings |
| `webhooks.enabled` | Listen for provider webhooks that wake an immediate refresh (default: `false`) |
| `webhooks.host` | Bind address (default: `0.0.0.0`) |
| `webhooks.port` | Bind port (default: `8080`) |
| `integrations` | List of repos to monitor |
| `integrations[].type` | `GITHUB` or `CIRCLECI` |
| `integrations[].excluded_workflows` | Workflow names to ignore (optional) |

## Webhooks

When `webhooks.enabled` is `true`, the monitor listens for:

| Provider | Path | Events that refresh |
|----------|------|---------------------|
| GitHub | `POST /webhooks/github` | `workflow_run` (`ping` is acknowledged only) |
| CircleCI | `POST /webhooks/circleci` | `workflow-completed`, `job-completed` |

A valid event breaks out of the wait and calls the same CI APIs as a timed poll. Status is still loaded via `get_latest()` so adapters remain the source of truth. CircleCI outbound webhooks are terminal-only, so the reconcile poll is still needed for the yellow “running” LED.

The Pi (or tunnel in front of it) must be reachable from GitHub/CircleCI. Expose `/webhooks/*` over HTTPS with a tunnel or reverse proxy; `/health` is available for connectivity checks.

## Environment variables

Tokens and webhook secrets are read from the environment, not stored in the config file:

```shell
export GITHUB_TOKEN=...
export CIRCLE_CI_TOKEN=...
# only when webhooks.enabled is true, for each configured provider:
export GITHUB_WEBHOOK_SECRET=...
export CIRCLE_CI_WEBHOOK_SECRET=...
```

Only set the variables for providers present in your config. `monitor check-config` fails fast if any are missing.

### Optional

| Variable | Purpose |
|----------|---------|
| `GITHUB_WEBHOOK_SECRET` | Shared secret for GitHub webhook signature verification |
| `CIRCLE_CI_WEBHOOK_SECRET` | Shared secret for CircleCI webhook signature verification |
| `MONITOR_LOG_DIR` | Default log directory when `log_dir` is not set in config |
| `LOG_LEVEL` | Log level for `bin/serve` (default: `debug`) |
| `CONF_FILE` | Config path for `bin/serve` (default: `monitor/integrations.json`) |
| `MONITOR_HOME` | Pi install directory (default: `/home/pi/gpio-build-monitor`) |
| `MONITOR_VENV` | Virtualenv used on the Pi (default: `$MONITOR_HOME/.venv`) |
| `MONITOR_SERVICE` | systemd unit name (default: `gpio-build-monitor`) |
| `GITHUB_REPO` | Repository checked for releases (default: `worthington10TW/gpio-build-monitor`) |
| `MONITOR_UPDATE_LOG` | Auto-update log file (default: `/var/log/gpio-build-monitor/update.log`) |

Logs are written to `<log_dir>/monitor.log` and stdout.
