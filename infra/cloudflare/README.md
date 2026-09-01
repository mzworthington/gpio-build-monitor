# Cloudflare infrastructure (Pulumi)

Two deployments share this product:

| Deployment | Where | Role |
|------------|--------|------|
| **Hosted** | Cloudflare Worker + custom domain | Public status UI + live WebSocket at `monitor.mzworthington.co.uk` |
| **Headless** | Raspberry Pi | GPIO LEDs only (see [docs/pi-setup.md](../../docs/pi-setup.md)) - no tunnel required for the website |

This stack owns the **hosted** path only. Zone lifecycle stays in
[edge-dns](https://github.com/mzworthington/edge-dns).

| Resource | Purpose |
|----------|---------|
| `Worker` | Account Worker identity (script via Wrangler) |
| `WorkersCustomDomain` | Hostname → Worker (Cloudflare creates DNS + cert) |
| `ObservatoryScheduledTest` | Synthetic Speed test per hostname |

Script + static UI assets are **not** updated by Pulumi. They ship via
`wrangler deploy` from [`worker/`](../../worker/) — locally or through the
`deploy-worker` job in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
on every push to `main`. That job injects the shared `mzworthington.co.uk` RUM
beacon into `monitor/web/index.html` before deploy.

Config accepts either `workerName` / `workerHostnames` or the Pages-shaped
aliases (`pagesProjectName` / `pagesHostnames`) so the shared edge-dns bootstrap
and CI action work without changes.

## Quick setup

```bash
# From repo root - see .env.example
bin/setup-cloudflare-hosting.sh

# Custom domains require an existing Worker deployment first:
cd worker && pnpm install && pnpm deploy

cd ../infra/cloudflare && pulumi up
```

If you previously pointed the hostname at a Tunnel CNAME, destroy that DNS
record (or `pulumi up` after this program removes it) **before** attaching the
Worker custom domain, or Cloudflare will reject the domain attach.

## Related

| Path | Purpose |
|------|---------|
| [`worker/`](../../worker/) | Hosted Worker (UI + CI poll + `/ws`) |
| [`docs/pi-setup.md`](../../docs/pi-setup.md) | Headless Pi / GPIO |
| [`.github/workflows/pulumi-cloudflare.yml`](../../.github/workflows/pulumi-cloudflare.yml) | Thin caller of edge-dns reusable workflow |
