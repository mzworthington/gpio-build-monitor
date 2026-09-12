# Configuration

`monitor/api/monitor/integrations.yaml` is local to your machine and gitignored. Start from the example:

```shell
cp monitor/api/monitor/integrations.example.yaml monitor/api/monitor/integrations.yaml
```

## Example

```yaml
poll_in_seconds: 60
log_dir: logs
outputs:
  websocket:
    enabled: true
    host: "0.0.0.0"
    port: 8080
webhooks:
  enabled: true
  host: "0.0.0.0"
  port: 8081
integrations:
  - type: GITHUB
    username: your-github-org
    repo: your-repo
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
| `outputs` | Optional status adapters (default: WebSocket on `0.0.0.0:8080`) |
| `outputs.websocket` | Browser UI over WebSockets (Python hub / local serve) |
| `outputs.websocket.enabled` | Serve the status page (default: `true`) |
| `outputs.websocket.host` | Bind address (default: `0.0.0.0`) |
| `outputs.websocket.port` | HTTP/WebSocket port (default: `8080`) |
| `pins` | BCM pin overrides live on the Pi GPIO follower, not in the hub YAML |
| `webhooks` | Optional webhook ingress settings |
| `webhooks.enabled` | Listen for provider webhooks that wake an immediate refresh (default: `false`) |
| `webhooks.host` | Bind address (default: `0.0.0.0`) |
| `webhooks.port` | Bind port (default: `8080`; use a different port from `outputs.websocket` if both are enabled) |
| `integrations` | List of repos to monitor |
| `integrations[].type` | `GITHUB` or `CIRCLECI` |
| `integrations[].excluded_workflows` | Exact workflow names to ignore (optional) |
| `integrations[].excluded_workflow_patterns` | fnmatch patterns for workflow names (optional) |
| `integrations[].branch` | GitHub only: branch to monitor (default: `main`; use `*` for all branches) |

### Active GitHub Actions only

For GitHub integrations, the monitor lists workflows via
`GET /repos/{owner}/{repo}/actions/workflows` and keeps only those with
`state: active` (YAML still present and enabled). Recent runs for deleted or
disabled workflows are ignored, so orphaned pipelines no longer appear on the
board. CircleCI is unchanged. Use `excluded_workflows` /
`excluded_workflow_patterns` for additional name-based filtering.

If an authenticated call returns 401 or 403 (rate limit or a PAT without
Actions read), the poller retries the same public endpoints without
credentials so public repos still light the board.

### Dependabot Update runs

GitHub Dependabot names each version check uniquely (`npm_and_yarn in /infra/cloudflare for js-yaml - Update #123`). Those runs are omitted from the board by default (Pi and hosted Worker). They are not product CI, and a failed updater job should not turn the desk light red. Use `excluded_workflows` / `excluded_workflow_patterns` for other noise. Dependabot *PRs* still count in the open-PR glance when they exist.

With WebSocket enabled, open `http://<host>:8080/` for the Alpine status page.

## Webhooks

When `webhooks.enabled` is `true`, the monitor listens for:

| Provider | Path | Events that refresh |
|----------|------|---------------------|
| GitHub | `POST /webhooks/github` | `workflow_run`, `pull_request`, `dependabot_alert`, `code_scanning_alert` (`ping` is acknowledged only) |
| CircleCI | `POST /webhooks/circleci` | `workflow-completed`, `job-completed` |

A valid event breaks out of the wait and calls the same CI APIs as a timed poll. Status is still loaded via `get_latest()` so adapters remain the source of truth. CircleCI outbound webhooks are terminal-only, so the reconcile poll is still needed for the yellow “running” LED.

This block is for a local Python hub (`bin/serve`). Production webhooks go to the Worker: [webhooks.md](webhooks.md).

## Environment variables

Tokens and webhook secrets are read from the environment, not stored in the config file:

```shell
export GITHUB_TOKEN=...
export CIRCLE_CI_TOKEN=...
# only when webhooks.enabled is true, for each configured provider:
export GITHUB_WEBHOOK_SECRET=...
export CIRCLE_CI_WEBHOOK_SECRET=...
```

`GITHUB_TOKEN` needs `security_events` (classic) or Dependabot alerts + code
scanning read (fine-grained) to populate `security` on the status API. Without
that scope GitHub returns `null`, same as CircleCI/GitLab. GitHub `security`
and `pull_requests` are `{ count, url, items }`; CircleCI/GitLab stay `null`.
Compact eink snapshots still flatten to `security_count` / `pr_count`.

Only set the variables for providers present in your config. `monitor check-config` fails fast if any are missing.

### Optional

| Variable | Purpose |
|----------|---------|
| `GITHUB_WEBHOOK_SECRET` | Shared secret for GitHub webhook signature verification |
| `CIRCLE_CI_WEBHOOK_SECRET` | Shared secret for CircleCI webhook signature verification |
| `MONITOR_LOG_DIR` | Default log directory when `log_dir` is not set in config |
| `LOG_LEVEL` | Log level for `bin/serve` (default: `debug`) |
| `CONF_FILE` | Config path for `bin/serve` (default: `monitor/api/monitor/integrations.yaml`) |
| - | `bin/serve` loads a gitignored `.env` from the repo root when present, then `pnpm install` / `pnpm build:web` as needed |
| `MONITOR_API_ORIGIN` | Origin the Pi GPIO follower (and optional local clients) use. Default `https://monitor.mzworthington.co.uk` |
| `MONITOR_HOME` | Pi install directory (default: `/home/pi/gpio-build-monitor`) |
| `MONITOR_VENV` | Virtualenv used on the Pi (default: `$MONITOR_HOME/.venv`) |
| `MONITOR_SERVICE` | systemd unit name (default: `gpio-build-monitor`) |
| `GITHUB_REPO` | Repository checked for releases (default: `mzworthington/gpio-build-monitor`) |
| `MONITOR_UPDATE_LOG` | Auto-update log file (default: `/var/log/gpio-build-monitor/update.log`) |

Logs are written to `<log_dir>/monitor.log` and stdout.
