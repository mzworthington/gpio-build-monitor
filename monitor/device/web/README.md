# Frontend (Cloudflare Worker)

Public status UI and StatusHub on one Worker. Live origin:
`https://monitor.mzworthington.co.uk` (`GET /api/status`, `wss://…/api/ws`;
`/status` and `/ws` still work).

Production leaves `PYTHON_API_ORIGIN` empty so the Worker is the hub. If you
set it, `/api/status`, `/api/ws`, `/api/health`, and `/api/webhooks/*` proxy to
that Python origin.

```bash
pnpm install
pnpm test
pnpm typecheck
pnpm build:web   # TypeScript Alpine → ./public/monitor.js

pnpm deploy:api  # Worker + assets (public hostname)
pnpm deploy      # Pages project on *.pages.dev only
```

On `main`, CI deploys Pages (`deploy-pages`, `*.pages.dev`) and the Worker
(`deploy-api`). `deploy:api` must run `pnpm build:web` first so `/monitor.js` is
the bundle, not HTML.

Local:

```bash
# from repo root (Python hub including /api/*):
bin/serve
# Worker locally:
cd monitor/device/web && pnpm install && pnpm dev:worker
```

Infra (Worker custom domain): [../../../infra/cloudflare/README.md](../../../infra/cloudflare/README.md).
