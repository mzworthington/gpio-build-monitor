# Frontend (Cloudflare Pages)

Static status UI. Live data comes from the **Python API** at `https://monitor.mzworthington.co.uk/api` (`/api/status`, `/api/ws`).

A Worker route `monitor.mzworthington.co.uk/api*` forwards those paths to `PYTHON_API_ORIGIN` (the Python process). Leave `MONITOR_API_ORIGIN` empty so the SPA uses the page origin.

```bash
pnpm install
pnpm test
pnpm typecheck
pnpm build:web   # TypeScript Alpine → ./public/monitor.js

pnpm deploy      # Pages UI
PYTHON_API_ORIGIN=https://your-python-host pnpm deploy:api
```

On `main`, CI deploys Pages (`deploy-pages`) and the `/api` Worker (`deploy-api`).
Set Actions variable `PYTHON_API_ORIGIN` to the public Python origin (scheme + host, no `/api` suffix).

Python CORS: `outputs.websocket.cors_origins` must include
`https://monitor.mzworthington.co.uk` if the API is not same-origin behind the Worker.

Local:

```bash
# from repo root (Python API including /api/*):
bin/serve
cd monitor/device/web && pnpm install && pnpm dev
```

Infra (Pages hostname): [../../../infra/cloudflare/README.md](../../../infra/cloudflare/README.md).
