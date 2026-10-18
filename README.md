# GPIO build monitor

[![CI](https://img.shields.io/github/actions/workflow/status/mzworthington/gpio-build-monitor/ci.yml?branch=main&style=for-the-badge&logo=github-actions&label=CI)](https://github.com/mzworthington/gpio-build-monitor/actions/workflows/ci.yml)
[![Quality gate](https://img.shields.io/sonar/alert_status/mzworthington_gpio-build-monitor?server=https%3A%2F%2Fsonarcloud.io&style=for-the-badge&logo=sonarqube)](https://sonarcloud.io/summary/new_code?id=mzworthington_gpio-build-monitor)

Glanceable CI status - on the web, glowing on your desk, or in an agent's tools.

**Live status:** [monitor.mzworthington.co.uk](https://monitor.mzworthington.co.uk)

![Finished build monitor](build_monitor.jpg)

Inspired by office information radiators. [Read the story →](https://mzworthington.co.uk/guides/i-built-a-build-monitor)

## Ways to run it

Same aggregation; pick the outputs you want.

| | **On the web** | **On a Pi** | **On a Mac** | **On an X3** | **For agents** |
|---|---|---|---|---|---|
| **What you get** | Public status UI | Desk LEDs | Menu bar extra | Pocket e-ink (CrossPoint) | Read-only MCP tools |
| **Where it runs** | Cloudflare Worker | Raspberry Pi GPIO | [SwiftBar](docs/macos.md) plugin | ESP32-C3 firmware | Any MCP client |
| **See it** | [monitor.mzworthington.co.uk](https://monitor.mzworthington.co.uk) | Hardware on your desk | Top toolbar (polls `/api/status`) | E-ink panel (`/api/status?view=eink`) | [`/mcp`](https://monitor.mzworthington.co.uk/mcp) |
| **Setup** | [Web UI](monitor/device/web/README.md) · [infra/cloudflare](infra/cloudflare/README.md) | [Pi setup](docs/pi-setup.md) · [Hardware](docs/hardware.md) | [Mac menu bar](docs/macos.md) | [Xteink e-ink](docs/xteink-x3.md) | [Agents](docs/agents.md) |

Every client reads the hosted Worker on `https://monitor.mzworthington.co.uk`. People use `GET /api/status` and `/api/ws`. Agents use `/mcp` (`get_build_status`, `get_repo_status`, `list_attention`). StatusHub polls GitHub Actions and CircleCI. Desk lights subscribe to `/api/ws`.

```mermaid
flowchart TB
  subgraph see [What you see]
    WebUI[Status page]
    Mac[Menu bar]
    X3[Pocket e-ink X3]
    LEDs[Desk lights]
    Agent[Agent tools]
  end

  subgraph hosted [Hosted]
    Worker[Cloudflare Worker StatusHub]
  end

  subgraph ci [CI]
    GH[GitHub Actions]
    CCI[CircleCI]
  end

  WebUI --> Worker
  Mac --> Worker
  X3 --> Worker
  LEDs --> Worker
  Agent --> Worker
  Worker --> GH
  Worker --> CCI
```

The public hostname is a Worker custom domain. Alpine loads from that origin and opens `wss://monitor.mzworthington.co.uk/api/ws`. Point the Mac extra and e-ink at the same `/api`. Agents connect to `/mcp` on that origin ([Agents](docs/agents.md)). Optional `PYTHON_API_ORIGIN` on the Worker can proxy `/api*` to a Python process; production leaves that empty so StatusHub is the hub.

```mermaid
sequenceDiagram
  actor You
  participant Browser as Status page
  participant Worker as Worker StatusHub
  participant Mac as Menu bar
  participant X3 as Pocket e-ink
  participant Pi as Pi GPIO follower
  participant Agent as Agent
  participant GH as GitHub / CircleCI

  alt Open the status page
    You->>Browser: load the site
    Browser->>Worker: Alpine UI
    Browser->>Worker: WebSocket /api/ws
    opt Webhook already arrived
      GH->>Worker: workflow / job event
    end
    Worker->>GH: poll when due
    Worker-->>Browser: live status
  else Glance at the desk
    You->>Pi: look at the lights
    Pi->>Worker: WebSocket /api/ws
    Worker-->>Pi: live status
    Pi-->>You: green / red / yellow / purple
  else Check the menu bar
    You->>Mac: look at the toolbar
    Mac->>Worker: GET /api/status
    Worker-->>Mac: snapshot JSON
  else Glance at the X3
    You->>X3: open Build monitor
    X3->>Worker: GET /api/status?view=eink
    Worker-->>X3: compact JSON
    X3-->>You: list jobs and PRs
  else Ask an agent
    You->>Agent: what failed?
    Agent->>Worker: MCP /mcp
    Worker-->>Agent: status, failures, pull requests
    Agent-->>You: the runs that need a look
  end
```

### Web (Worker)

The Worker serves the Alpine UI and StatusHub. `pnpm deploy:api` builds `public/monitor.js` then deploys. CI does the same on `main`. Put `MONITOR_CONFIG` and `GITHUB_TOKEN` on the Worker (`bin/sync-worker-monitor-config.sh`, `bin/sync-worker-github-token.sh`).

```shell
cd monitor/device/web && pnpm install && pnpm deploy:api
# hostname: infra/cloudflare/README.md
```

`pnpm deploy` still publishes a Pages project on `*.pages.dev`. That is not the public hostname.

### Pi (headless)

A Raspberry Pi drives LEDs by following the hosted `/api/ws` - green / red / yellow / blue / purple at a glance, even when your laptop is closed.

```shell
git clone https://github.com/mzworthington/gpio-build-monitor.git
cd gpio-build-monitor
bin/bootstrap
# then follow docs/pi-setup.md
```

## Why

- **Glanceable** - lights and a dial instead of inbox noise or another tab.
- **Always on** - hosted Worker stays up; Pi stays lit when your machine is shut.
- **Multi-provider** - GitHub Actions and CircleCI, aggregated across repos.
- **Agent-ready** - [three MCP tools](docs/agents.md) on that same snapshot, so an agent can see what failed and open the run.
- **Low cost** - Pi Zero and a handful of LEDs; the [full build came in around £20](docs/hardware.md#shopping-list).

## How status maps

| Light / UI | Meaning |
|------------|---------|
| Blue | Fetching status |
| Green | All non-running builds passed |
| Red | At least one build failed |
| Yellow (pulse) | At least one build is running |
| Purple | Connection or API error (polling continues) |

```mermaid
flowchart LR
  leds[Desk lights] --> agg[Aggregate]
  ui[Status page] --> agg
  snapshot[Menu bar and e-ink] --> agg
  agents[Agent tools] --> agg
  agg --> poll[CI poll and webhooks]
```

On a dev machine, GPIO is mocked automatically. On the Pi, the follower uses real hardware.

## Local development

```shell
git clone https://github.com/mzworthington/gpio-build-monitor.git
cd gpio-build-monitor
bin/bootstrap
cp monitor/api/monitor/integrations.example.yaml monitor/api/monitor/integrations.yaml
# edit integrations.yaml, export GITHUB_TOKEN / CIRCLE_CI_TOKEN (or put them in .env)
monitor check-config
bin/serve
# Python hub + Alpine: http://127.0.0.1:8080/
# Worker locally: cd monitor/device/web && pnpm dev:worker
```

See [Getting started](docs/getting-started.md) for mise, Make, and CLI details.

## Documentation

| Guide | Contents |
|-------|----------|
| [Getting started](docs/getting-started.md) | Local setup, CLI, development workflow |
| [Agents](docs/agents.md) | MCP tools: status, one repo, and what needs attention |
| [Pi setup](docs/pi-setup.md) | Headless Raspberry Pi + systemd |
| [Webhooks](docs/webhooks.md) | GitHub/CircleCI webhooks on the hosted Worker |
| [Push notifications](docs/push.md) | Chrome/Android fail + recovery alerts (hosted Worker) |
| [Mac menu bar](docs/macos.md) | SwiftBar extra from `GET /api/status` |
| [Xteink e-ink](docs/xteink-x3.md) | X3 CrossPoint overlay: Build monitor from `/api/status?view=eink` |
| [Configuration](docs/configuration.md) | `integrations.yaml`, tokens, pins, logging |
| [Raspberry Pi](docs/raspberry-pi.md) | GPIO follower, systemd, auto-updates |
| [Hardware](docs/hardware.md) | Pin map, shopping list, build photos |
| [Development](docs/development.md) | Tests, releases, CI, security scanning |
| [Hosted web UI](monitor/device/web/README.md) | Deploy the public UI |
| [Cloudflare infra](infra/cloudflare/README.md) | Worker custom domain (Pulumi) |

## Install from GitHub

```shell
pip install git+https://github.com/mzworthington/gpio-build-monitor
monitor run --help
```

## License

[MIT](LICENSE)
