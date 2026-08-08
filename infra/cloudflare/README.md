# Cloudflare infrastructure (Pulumi)

Worker + custom domain(s) on an existing active zone (zone lifecycle stays in
[edge-dns](https://github.com/mzworthington/edge-dns)). The Python GPIO process
still runs on the Pi; this stack publishes the edge hostname
(`monitor.mzworthington.co.uk` by default).

| Resource | Purpose |
|----------|---------|
| `Worker` | Account Worker identity (script via Wrangler) |
| `WorkersCustomDomain` | Hostname → Worker (Cloudflare creates DNS + cert) |
| `ObservatoryScheduledTest` | Synthetic Speed test per hostname |

Zone Web Analytics stays on the mzworthington site stack (same zone); do not duplicate it here.

Config accepts either `workerName` / `workerHostnames` or the Pages-shaped
aliases (`pagesProjectName` / `pagesHostnames`) so the shared edge-dns bootstrap
and CI action work without changes.

## Quick setup

```bash
# From repo root — see .env.example
export DOMAIN=mzworthington.co.uk
export PAGES_HOSTNAMES=monitor.mzworthington.co.uk
export PAGES_PROJECT_NAME=gpio-build-monitor
export PULUMI_STACK=prod
../../bin/setup-cloudflare-hosting.sh

# Custom domains require an existing Worker deployment — deploy script first:
cd ../../worker && pnpm install && pnpm deploy

# Then attach hostname(s) + Observatory:
cd ../infra/cloudflare && pulumi up
```

If `WorkersCustomDomain` fails with “has no deployments”, run `pnpm deploy` in `worker/` and `pulumi up` again.

## Related

| Path | Purpose |
|------|---------|
| [`worker/`](../../worker/) | Worker source + Wrangler |
| [`.github/workflows/pulumi-cloudflare.yml`](../../.github/workflows/pulumi-cloudflare.yml) | Thin caller of edge-dns reusable workflow |
| [edge-dns reusable CI](https://github.com/mzworthington/edge-dns/blob/main/docs/reusable-cloudflare-ci.md) | Secrets, bootstrap, apply gate |
