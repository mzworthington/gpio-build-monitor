# Agent Handshake

Standards and lifecycle agents live in `~/.agents` ([Waykit](https://github.com/mzworthington/waykit)).

Before starting work, read:

- `~/.agents/AGENTS.md` - bootstrap and lifecycle routing
- `~/.agents/CODING_PHILOSOPHY.md` - hexagonal architecture, DDD, vertical slices, clean code
- `~/.agents/skills/profile-iac/SKILL.md` - secure IaC (when touching `infra/`)
- `~/.agents/skills/framework-pulumi/SKILL.md` - Pulumi patterns (when touching `infra/`)

## Toolchain

- Declared in `mise.toml` (Python). Cloudflare infra uses Node/pnpm under `infra/cloudflare` and `worker/`.

## Project notes

- Raspberry Pi owns headless GPIO + CI polling (`monitor/` Python package).
- Hosted status UI is a Cloudflare Worker (`worker/`) on `monitor.mzworthington.co.uk` (`infra/cloudflare` Pulumi).
- Before handover of infra changes: `cd infra/cloudflare && pnpm install && pnpm typecheck` (and `pulumi preview` with stack selected when credentials are available).
