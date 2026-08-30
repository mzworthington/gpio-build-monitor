# Web Push (status alerts)

Optional Chrome desktop / Android alerts when the hosted monitor transitions
into **FAIL**, and again when it recovers from **FAIL** to all **PASS**.
Subscriptions live in the existing `StatusHub` Durable Object (no KV
namespace, no extra Cloudflare product).

## Behaviour

- Edge-triggered: one notification when status newly becomes `FAIL`
- Edge-triggered: one notification when status recovers `FAIL` → `PASS`
  after in-progress rebuilds have settled (not when a failed job merely
  starts running again)
- No repeat while status stays red (or stays green)
- Opt-in from the status page (“Notify on failure”)
- Hidden automatically when VAPID secrets are not configured (local Pi UI
  included)

## Setup

Generate a VAPID key pair once:

```bash
cd worker
pnpm exec wrangler deploy   # ensure the Worker exists
npx --yes web-push generate-vapid-keys
```

Upload secrets (private key never goes in git):

```bash
cd worker
echo -n 'mailto:you@example.com' | pnpm exec wrangler secret put VAPID_SUBJECT --name gpio-build-monitor
# paste the public key:
pnpm exec wrangler secret put VAPID_PUBLIC_KEY --name gpio-build-monitor
# paste the private key:
pnpm exec wrangler secret put VAPID_PRIVATE_KEY --name gpio-build-monitor
```

`VAPID_SUBJECT` should be a `mailto:` or `https://` contact URL. Redeploy if
you just added the push code:

```bash
pnpm deploy
```

## Try it

1. Open [monitor.mzworthington.co.uk](https://monitor.mzworthington.co.uk) in
   Chrome (desktop or Android).
2. Click **Notify on failure** and allow notifications.
3. When aggregate status next moves into FAIL, you should get a system
   notification. When it later recovers to all PASS (and nothing is still
   building), you get another.
   Clicking either focuses/opens the status page.

## API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/push/vapid-public-key` | Public VAPID key for `PushManager.subscribe` |
| `POST` | `/api/push/subscribe` | Store a browser push subscription |
| `DELETE` | `/api/push/subscribe` | Remove a subscription (`{ "endpoint": "..." }`) |

## Cost / free-tier notes

Subscriptions are stored in Durable Object storage already used by the status
hub. Fan-out is tiny (personal devices). No Workers KV reads/writes, so no KV
quota exposure.

## Out of scope (for later)

- iOS Safari (Home Screen PWA requirements)
- Auth / shared-secret gate on subscribe (page is already public)
- Quiet hours / per-repo mutes
