# Cloudflare infrastructure (Pulumi)

Two deployments share this product:

| Deployment | Where | Role |
|------------|--------|------|
| **Hosted hub** | Cloudflare Worker custom domain | Alpine UI + StatusHub at `monitor.mzworthington.co.uk` |
| **Pages (optional)** | Cloudflare Pages | Same static files on `*.pages.dev` only |
| **Local hub** | Python (`monitor/api`) | `bin/serve` on a laptop (`:8080`) |
| **Headless** | Raspberry Pi | GPIO follower of the hosted `/api` |

This stack owns the **Worker custom domain**. Zone lifecycle stays in
[edge-dns](https://github.com/mzworthington/edge-dns). Do not bind Pages to
`monitor.mzworthington.co.uk`.

| Resource | Purpose |
|----------|---------|
| `Worker` + `WorkersCustomDomain` | Hostname → StatusHub Worker |
| `PagesProject` | Direct-upload Pages project (`*.pages.dev`) |
| `ObservatoryScheduledTest` | Synthetic Speed test per hostname |

The public UI ships with `wrangler deploy` from [`monitor/device/web/`](../../monitor/device/web/) (`pnpm deploy:api`, or the `deploy-api` job in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) on `main`). Put `MONITOR_CONFIG` and `GITHUB_TOKEN` on the Worker. Leave `PYTHON_API_ORIGIN` empty in production so StatusHub is the hub.

Config accepts `workerName` / `workerHostnames` or the older
`pagesProjectName` / `pagesHostnames` keys (same values).

## Quick setup

```bash
# From repo root
bin/setup-cloudflare-hosting.sh

cd monitor/device/web && pnpm install && pnpm deploy:api

cd ../../../infra/cloudflare && pulumi up
```

## Related

| Path | Purpose |
|------|---------|
| [`monitor/device/web/`](../../monitor/device/web/) | Alpine UI + Worker (StatusHub) |
| [`monitor/api/`](../../monitor/api/) | Python hub for local `bin/serve` |
| [`docs/pi-setup.md`](../../docs/pi-setup.md) | Headless Pi / GPIO |
