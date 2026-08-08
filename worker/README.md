# Cloudflare Worker

Serves the status UI assets from `monitor/web` at the custom domain owned by
Pulumi (`infra/cloudflare`). GPIO + CI polling remain on the Raspberry Pi.

```bash
pnpm install
pnpm dev      # local
pnpm deploy   # production (requires CLOUDFLARE_API_TOKEN)
```

Custom domains are **not** declared here — Pulumi attaches
`monitor.mzworthington.co.uk` so Wrangler and Pulumi do not fight over DNS.
