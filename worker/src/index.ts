import {
  aggregate,
  emptyPayload,
  fetchAllBuilds,
  parseMonitorConfig,
  type AggregateStatus,
  type StatusPayload,
} from './ci';
import {
  failureNotificationMessage,
  hashedPushSubscriptionKey,
  isPushSubscription,
  parsePushSubscription,
  recoveryNotificationMessage,
  sendWebPush,
  shouldNotifyFailure,
  shouldNotifyRecovery,
  statusToRemember,
  SUB_KEY_PREFIX,
  vapidFromEnv,
  type StoredPushSubscription,
} from './push';
import type { PushMessage } from '@block65/webcrypto-web-push';
import { handleWebhook } from './webhooks';

export interface Env {
  ASSETS: Fetcher;
  STATUS: DurableObjectNamespace;
  MONITOR_CONFIG?: string;
  GITHUB_TOKEN?: string;
  CIRCLE_CI_TOKEN?: string;
  GITHUB_WEBHOOK_SECRET?: string;
  CIRCLE_CI_WEBHOOK_SECRET?: string;
  VAPID_PUBLIC_KEY?: string;
  VAPID_PRIVATE_KEY?: string;
  VAPID_SUBJECT?: string;
}

const LAST_STATUS_KEY = 'last_status';
const PUBLIC_ORIGIN_KEY = 'public_origin';
const DEFAULT_PUBLIC_ORIGIN = 'https://monitor.mzworthington.co.uk';

/** Single DO that polls CI and fans out status over WebSockets (+ optional Web Push). */
export class StatusHub implements DurableObject {
  private readonly state: DurableObjectState;
  private readonly env: Env;
  private payload: StatusPayload;

  constructor(state: DurableObjectState, env: Env) {
    this.state = state;
    this.env = env;
    const config = parseMonitorConfig(env.MONITOR_CONFIG);
    this.payload = emptyPayload(config.poll_in_seconds);
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    await this.rememberPublicOrigin(url.origin);

    if (url.pathname === '/ws') {
      if (request.headers.get('Upgrade') !== 'websocket') {
        return new Response('Expected WebSocket', { status: 426 });
      }
      const pair = new WebSocketPair();
      const [client, server] = Object.values(pair);
      this.state.acceptWebSocket(server);
      server.send(JSON.stringify(this.payload));
      // Avoid a fetch flash on every connect/reconnect; alarm owns the cadence.
      if (this.isStale()) {
        void this.refresh();
      }
      return new Response(null, { status: 101, webSocket: client });
    }

    if (url.pathname === '/refresh' && request.method === 'POST') {
      await this.refresh();
      return Response.json(this.payload);
    }

    if (url.pathname === '/push/subscribe' && request.method === 'POST') {
      return this.subscribe(request);
    }

    if (url.pathname === '/push/subscribe' && request.method === 'DELETE') {
      return this.unsubscribe(request);
    }

    return new Response('Not found', { status: 404 });
  }

  async webSocketMessage(): Promise<void> {
    // Clients are receive-only.
  }

  async webSocketClose(): Promise<void> {
    // Hibernation API tracks sockets; nothing to clear.
  }

  async webSocketError(): Promise<void> {
    // Hibernation API tracks sockets; nothing to clear.
  }

  async alarm(): Promise<void> {
    await this.refresh();
  }

  /** True when we have never checked, or the reconcile window has elapsed. */
  private isStale(): boolean {
    if (this.payload.last_checked_at == null) return true;
    if (this.payload.next_check_at == null) return true;
    return Date.now() / 1000 >= this.payload.next_check_at;
  }

  private async rememberPublicOrigin(origin: string): Promise<void> {
    // Internal stub fetches use placeholder hosts; ignore those.
    let hostname: string;
    try {
      hostname = new URL(origin).hostname;
    } catch {
      return;
    }
    if (hostname === 'monitor') return;
    await this.state.storage.put(PUBLIC_ORIGIN_KEY, origin);
  }

  private async publicOrigin(): Promise<string> {
    return (
      (await this.state.storage.get<string>(PUBLIC_ORIGIN_KEY)) || DEFAULT_PUBLIC_ORIGIN
    );
  }

  async refresh(): Promise<void> {
    const config = parseMonitorConfig(this.env.MONITOR_CONFIG);
    // Signal fetch without resetting countdown / wiping status payload fields.
    this.payload = {
      ...this.payload,
      fetching: true,
      poll_in_seconds: config.poll_in_seconds,
    };
    this.broadcast();

    const builds = await fetchAllBuilds(config, {
      githubToken: this.env.GITHUB_TOKEN,
      circleToken: this.env.CIRCLE_CI_TOKEN,
    });
    const { status, is_running } = aggregate(builds);
    const previous = await this.state.storage.get<AggregateStatus>(LAST_STATUS_KEY);
    const now = Date.now() / 1000;
    this.payload = {
      type: 'status',
      fetching: false,
      status,
      is_running,
      builds,
      poll_in_seconds: config.poll_in_seconds,
      last_checked_at: now,
      next_check_at: now + config.poll_in_seconds,
    };
    this.broadcast();
    await this.state.storage.put(
      LAST_STATUS_KEY,
      statusToRemember(previous, status, is_running),
    );
    await this.state.storage.setAlarm(Date.now() + config.poll_in_seconds * 1000);

    if (shouldNotifyFailure(previous, status)) {
      this.state.waitUntil(this.notifyFailure());
    } else if (shouldNotifyRecovery(previous, status, is_running)) {
      this.state.waitUntil(this.notifyRecovery());
    }
  }

  private async subscribe(request: Request): Promise<Response> {
    if (!vapidFromEnv(this.env)) {
      return Response.json({ error: 'push not configured' }, { status: 503 });
    }
    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return Response.json({ error: 'invalid json' }, { status: 400 });
    }
    const sub = parsePushSubscription(body);
    if (!sub) {
      return Response.json({ error: 'invalid subscription' }, { status: 400 });
    }
    const key = await hashedPushSubscriptionKey(sub.endpoint);
    await this.state.storage.put(key, sub);
    return Response.json({ status: 'subscribed' });
  }

  private async unsubscribe(request: Request): Promise<Response> {
    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return Response.json({ error: 'invalid json' }, { status: 400 });
    }
    const endpoint =
      body && typeof body === 'object' && typeof (body as { endpoint?: unknown }).endpoint === 'string'
        ? (body as { endpoint: string }).endpoint
        : null;
    if (!endpoint) {
      return Response.json({ error: 'endpoint required' }, { status: 400 });
    }
    const key = await hashedPushSubscriptionKey(endpoint);
    await this.state.storage.delete(key);
    return Response.json({ status: 'unsubscribed' });
  }

  private async notifyFailure(): Promise<void> {
    await this.notifySubscribers(
      failureNotificationMessage(this.payload.builds, await this.publicOrigin()),
    );
  }

  private async notifyRecovery(): Promise<void> {
    await this.notifySubscribers(recoveryNotificationMessage(await this.publicOrigin()));
  }

  private async notifySubscribers(message: PushMessage): Promise<void> {
    const vapid = vapidFromEnv(this.env);
    if (!vapid) return;

    const listed = await this.state.storage.list<StoredPushSubscription>({
      prefix: SUB_KEY_PREFIX,
    });

    for (const [key, value] of listed) {
      if (!isPushSubscription(value)) {
        await this.state.storage.delete(key);
        continue;
      }
      try {
        const result = await sendWebPush(value, message, vapid);
        if (result.gone) {
          await this.state.storage.delete(key);
        }
      } catch {
        // Best-effort: a single bad subscription must not block others.
      }
    }
  }

  private broadcast(): void {
    const message = JSON.stringify(this.payload);
    for (const ws of this.state.getWebSockets()) {
      try {
        ws.send(message);
      } catch {
        // Closed sockets are dropped by the runtime.
      }
    }
  }
}

function statusStub(env: Env) {
  return env.STATUS.get(env.STATUS.idFromName('monitor'));
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === '/ws' || url.pathname === '/refresh') {
      return statusStub(env).fetch(request);
    }

    if (url.pathname === '/api/push/vapid-public-key') {
      const vapid = vapidFromEnv(env);
      if (!vapid) {
        return Response.json({ error: 'push not configured' }, { status: 503 });
      }
      return Response.json({ publicKey: vapid.publicKey });
    }

    if (url.pathname === '/api/push/subscribe') {
      // Forward to the DO so subscriptions sit with the FAIL edge trigger.
      const method = request.method;
      if (method !== 'POST' && method !== 'DELETE') {
        return new Response('Method not allowed', { status: 405 });
      }
      return statusStub(env).fetch(
        new Request(new URL('/push/subscribe', request.url), {
          method,
          headers: request.headers,
          body: request.body,
        }),
      );
    }

    if (url.pathname === '/health') {
      return Response.json({ status: 'ok' });
    }

    if (url.pathname === '/webhooks/github' && request.method === 'POST') {
      const { response, decision } = await handleWebhook(request, 'github', env);
      if (decision === 'refresh') {
        ctx.waitUntil(statusStub(env).fetch(new Request('https://monitor/refresh', { method: 'POST' })));
      }
      return response;
    }

    if (url.pathname === '/webhooks/circleci' && request.method === 'POST') {
      const { response, decision } = await handleWebhook(request, 'circleci', env);
      if (decision === 'refresh') {
        ctx.waitUntil(statusStub(env).fetch(new Request('https://monitor/refresh', { method: 'POST' })));
      }
      return response;
    }

    return env.ASSETS.fetch(request);
  },
} satisfies ExportedHandler<Env>;
