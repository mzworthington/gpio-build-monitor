# Agent Handshake

Standards and lifecycle agents live in `~/.agents` ([Waykit](https://github.com/mzworthington/waykit)).

Start from `~/.agents/AGENTS.md` (thin index). **Do not** bulk-read philosophy, SOPs, or skills up front.

| Situation | Load |
|-----------|------|
| Any task | `~/.agents/AGENTS.md` invariants + phase table |
| Architecture / new structure | `CODING_PHILOSOPHY.md` (or kit-knowledge `get_philosophy_section`) |
| Feature lifecycle | `skills/agent-orchestrator` |
| Bug / CI / live symptom | `skills/agent-debug` |
| Cloudflare Worker / DNS / RUM | `skills/agent-cloudflare-ops` (`wk mcp cloudflare-ops --project`) |
| Infra under `infra/` | `skills/profile-iac` then `skills/framework-pulumi` |
| Handshake / kit bootstrap | `wk align .`. Community files: `wk doctor .` |
| SOP / handover lookup | kit-knowledge MCP |
| Durable project facts | memory MCP (glossary, SLOs, prefs — never secrets) |

Phase handovers: `~/.agents/handover/gpio-build-monitor/`.

For bugs and failed jobs, use `agent-debug`. Do not open the full feature lifecycle unless RCA needs a new capability.

## Project notes

- Raspberry Pi GPIO follower lives in `monitor/device/pi` (`gpio_pi`). It follows `https://monitor.mzworthington.co.uk/api` and does not poll CI.
- Hosted status API + UI is a Cloudflare Worker (`monitor/device/web/`) on `monitor.mzworthington.co.uk` (`infra/cloudflare` Pulumi). Pages still exists for `*.pages.dev`. The Python package `monitor/api` is a local hub for development.
- Xteink X3 runs CrossPoint plus a Build monitor overlay (`monitor/device/eink/`). Do not run the Pi poller on the ESP32.
- Conventional commit-msg: `.githooks/commit-msg` (`git config core.hooksPath .githooks` once per clone).

## Toolchain

Declared in `mise.toml` (Python). Cloudflare infra uses Node/pnpm under `infra/cloudflare` and `monitor/device/web/`.

MCP: kit `default` in `.cursor/mcp.json`. Do not stack Cloudflare onto that file. For live CF work, `wk mcp cloudflare-ops --project`, then restore `wk mcp default --project`.

Before handover of infra changes: `cd infra/cloudflare && pnpm install && pnpm typecheck` (and `pulumi preview` with stack selected when credentials are available).
