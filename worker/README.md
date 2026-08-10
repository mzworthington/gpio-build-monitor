# Hosted Worker (Cloudflare)

Public status UI + live WebSocket. Same CI aggregation behaviour as the Pi,
without GPIO. Hostname: `monitor.mzworthington.co.uk` (Pulumi custom domain).

```bash
pnpm install

# Prefer syncing from the Pi/laptop integrations file (GitHub-only is fine):
#   bin/sync-worker-monitor-config.sh
#
# Or manually:
echo -n "$GITHUB_TOKEN" | pnpm exec wrangler secret put GITHUB_TOKEN --name gpio-build-monitor
# only if you have CircleCI integrations:
# echo -n "$CIRCLE_CI_TOKEN" | pnpm exec wrangler secret put CIRCLE_CI_TOKEN --name gpio-build-monitor

pnpm deploy
```

On `main`, the CI/CD workflow deploys automatically after tests
(`.github/workflows/ci.yml` `deploy-worker` job). Manual `pnpm deploy` is still
fine for hotfixes; secrets on the Worker persist across deploys.

Empty `integrations` (or only placeholders) shows **Idle**, not an error. Omit CircleCI
entries entirely when you have none.

Webhooks (immediate refresh): [docs/webhooks.md](../docs/webhooks.md).

Failure push notifications (Chrome desktop / Android): [docs/push.md](../docs/push.md).

```bash
# after generate-vapid-keys — see docs/push.md
pnpm exec wrangler secret put VAPID_PUBLIC_KEY --name gpio-build-monitor
pnpm exec wrangler secret put VAPID_PRIVATE_KEY --name gpio-build-monitor
```

Local:

```bash
pnpm dev
pnpm test
pnpm typecheck
```

Infra (custom domain): [../infra/cloudflare/README.md](../infra/cloudflare/README.md).
