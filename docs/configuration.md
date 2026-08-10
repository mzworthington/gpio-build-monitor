# Configuration

`monitor/integrations.yaml` is local to your machine and gitignored. Start from the example:

```shell
cp monitor/integrations.example.yaml monitor/integrations.yaml
```

## Example

```yaml
poll_in_seconds: 60
log_dir: logs
outputs:
  gpio: true
  websocket:
    enabled: true
    host: "0.0.0.0"
    port: 8080
webhooks:
  enabled: true
  host: "0.0.0.0"
  port: 8081
pins:
  GREEN: 17
  YELLOW: 18
  BLUE: 22
  RED: 27
  PURPLE: 23
integrations:
  - type: GITHUB
    username: mzworthington
    repo: steerlens
    branch: main
  - type: CIRCLECI
    username: your-circle-org
    repo: your-repo
    excluded_workflows:
      - nightly-scan
```

## Fields

| Field | Description |
|-------|-------------|
| `poll_in_seconds` | Seconds between reconcile polls (default: 30). With webhooks enabled this is the fallback cadence; events wake an immediate refresh. |
| `log_dir` | Directory for `monitor.log` (default: `logs/`) |
| `outputs` | Optional status adapters (default: GPIO only) |
| `outputs.gpio` | Drive Raspberry Pi LEDs (default: `true`) |
| `outputs.websocket` | Optional browser UI over WebSockets |
| `outputs.websocket.enabled` | Serve the status page (default: `true` when the object is present) |
| `outputs.websocket.host` | Bind address (default: `0.0.0.0`) |
| `outputs.websocket.port` | HTTP/WebSocket port (default: `8080`) |
| `pins` | Optional BCM pin overrides per light name |
| `webhooks` | Optional webhook ingress settings |
| `webhooks.enabled` | Listen for provider webhooks that wake an immediate refresh (default: `false`) |
| `webhooks.host` | Bind address (default: `0.0.0.0`) |
| `webhooks.port` | Bind port (default: `8080`; use a different port from `outputs.websocket` if both are enabled) |
| `integrations` | List of repos to monitor |
| `integrations[].type` | `GITHUB` or `CIRCLECI` |
| `integrations[].excluded_workflows` | Exact workflow names to ignore (optional) |
| `integrations[].excluded_workflow_patterns` | fnmatch patterns for workflow names (optional) |
| `integrations[].branch` | GitHub only: branch to monitor (default: `main`; use `*` for all branches) |

### Dependabot Update runs

GitHub Dependabot names each version check uniquely (`npm_and_yarn in /. - Update #123`). The monitor collapses those into one bucket per ecosystem and directory (stripping the Update ID and optional package list), then keeps the newest by `created_at`. A fixed Dependabot config shows green once a newer Update succeeds; a broken config still fails the radiator. Prefer that over excluding `* - Update #*` unless you truly do not want Dependabot on the desk light.

With WebSocket enabled, open `http://<host>:8080/` for the live JS status page, or run the Python HTML client:

```shell
monitor client --server http://127.0.0.1:8080
# then open http://127.0.0.1:8090/
```

The client renders Jinja2 HTML for the first paint, then updates live over WebSocket (no full-page reload). You can run GPIO only, WebSocket only, or both.

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
| `CONF_FILE` | Config path for `bin/serve` (default: `monitor/integrations.yaml`) |
| `UI_HOST` / `UI_PORT` | Bind address/port for the HTML client started by `bin/serve` (defaults: `127.0.0.1` / `8090`) |
| `SERVE_CLIENT` | Set to `0` to skip the HTML client (`bin/serve` still starts the WebSocket UI when enabled) |
| - | `bin/serve` also loads a gitignored `.env` from the repo root when present |
| `MONITOR_HOME` | Pi install directory (default: `/home/pi/gpio-build-monitor`) |
| `MONITOR_VENV` | Virtualenv used on the Pi (default: `$MONITOR_HOME/.venv`) |
| `MONITOR_SERVICE` | systemd unit name (default: `gpio-build-monitor`) |
| `GITHUB_REPO` | Repository checked for releases (default: `mzworthington/gpio-build-monitor`) |
| `MONITOR_UPDATE_LOG` | Auto-update log file (default: `/var/log/gpio-build-monitor/update.log`) |

Logs are written to `<log_dir>/monitor.log` and stdout.
