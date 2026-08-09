# Webhooks (hosted Worker)

Provider webhooks wake an immediate CI refresh on the Cloudflare Worker.
Polling remains the reconcile fallback (and is still required for “running”
status on CircleCI, which only sends terminal events).

## Endpoints

| Provider | URL | Events |
|----------|-----|--------|
| GitHub | `https://monitor.mzworthington.co.uk/webhooks/github` | `workflow_run` (`ping` ACK only) |
| CircleCI | `https://monitor.mzworthington.co.uk/webhooks/circleci` | `workflow-completed`, `job-completed` |
| Health | `https://monitor.mzworthington.co.uk/health` | - |

## 1. (Optional) Shared secrets

Webhook signature verification is optional on the Worker. If you omit
`GITHUB_WEBHOOK_SECRET`, deliveries are accepted without HMAC checks.

To enforce signatures, pick a random secret (do not reuse the GitHub API PAT):

```bash
openssl rand -hex 32   # → GITHUB_WEBHOOK_SECRET
# optional CircleCI:
openssl rand -hex 32   # → CIRCLE_CI_WEBHOOK_SECRET
```

Upload to the Worker:

```bash
cd worker
pnpm exec wrangler secret put GITHUB_WEBHOOK_SECRET --name gpio-build-monitor
# paste secret, Enter

# only if using CircleCI webhooks:
pnpm exec wrangler secret put CIRCLE_CI_WEBHOOK_SECRET --name gpio-build-monitor
```

Redeploy if you just added webhook code:

```bash
pnpm deploy
```

## 2. Register GitHub webhook

For each repo (or once on the org):

1. **Settings → Webhooks → Add webhook**
2. Payload URL: `https://monitor.mzworthington.co.uk/webhooks/github`
3. Content type: `application/json`
4. Secret: optional — only if you set `GITHUB_WEBHOOK_SECRET` on the Worker
5. Events: **Let me select…** → enable **Workflow runs**
6. Active: checked → Add webhook

GitHub sends a `ping`; the Worker returns ACK. A `workflow_run` triggers refresh.

## 3. Register CircleCI (optional)

Only if you have CircleCI integrations in `MONITOR_CONFIG`:

1. Project **Project Settings → Webhooks**
2. URL: `https://monitor.mzworthington.co.uk/webhooks/circleci`
3. Secret: same as `CIRCLE_CI_WEBHOOK_SECRET`
4. Events: workflow / job completed

## Headless Pi

The Pi can still run its own webhook listener on LAN/tunnel for GPIO wake-ups
(`docs/configuration.md`). That is separate from the hosted Worker URLs above -
use the Worker URLs for the public website.

## Verify

```bash
curl -sS https://monitor.mzworthington.co.uk/health
# {"status":"ok"}
```

In GitHub → webhook → Recent Deliveries, `ping` / `workflow_run` should be `200`.
On the site, status should update shortly after a workflow finishes (without
waiting for the full poll interval).
