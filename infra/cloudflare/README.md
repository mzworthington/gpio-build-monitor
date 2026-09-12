# Cloudflare infrastructure (Pulumi)

Two deployments share this product:

| Deployment | Where | Role |
|------------|--------|------|
| **Frontend** | Cloudflare Pages | Static status UI at `monitor.mzworthington.co.uk` |
| **API** | Python (`monitor/`) | CI poll, `/status`, `/ws`, webhooks, GPIO on the Pi |
| **Headless** | Raspberry Pi | Same Python process drives desk LEDs |

This stack owns the **Pages** hostname. Zone lifecycle stays in
[edge-dns](https://github.com/mzworthington/edge-dns).

| Resource | Purpose |
|----------|---------|
| `PagesProject` | Direct-upload Pages project |
| `DnsRecord` + `PagesDomain` | Hostname → Pages |
| `ObservatoryScheduledTest` | Synthetic Speed test per hostname |

The UI ships via `wrangler pages deploy` from [`monitor/device/web/`](../../monitor/device/web/) — locally or through the
`deploy-pages` job in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
on every push to `main`. Set GitHub Actions variable `MONITOR_API_ORIGIN` to the
public Python API origin (for example `https://api.monitor.mzworthington.co.uk`)
so the page opens `/ws` on Python, not on Pages.

Config accepts `pagesProjectName` / `pagesHostnames` or the older
`workerName` / `workerHostnames` keys.

## Quick setup

```bash
# From repo root
bin/setup-cloudflare-hosting.sh

cd monitor/device/web && pnpm install && MONITOR_API_ORIGIN=https://api.example.example pnpm deploy

cd ../../../infra/cloudflare && pulumi up
```

## Related

| Path | Purpose |
|------|---------|
| [`monitor/device/web/`](../../monitor/device/web/) | TypeScript frontend (Alpine) + Pages deploy |
| [`monitor/api/`](../../monitor/api/) | Python API |
| [`docs/pi-setup.md`](../../docs/pi-setup.md) | Headless Pi / GPIO |
