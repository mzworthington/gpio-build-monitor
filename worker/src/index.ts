import {
  aggregate,
  emptyPayload,
  fetchAllBuilds,
  parseMonitorConfig,
  type StatusPayload,
} from './ci';
import { handleWebhook } from './webhooks';

export interface Env {
  ASSETS: Fetcher;
  STATUS: DurableObjectNamespace;
  MONITOR_CONFIG?: string;
  GITHUB_TOKEN?: string;
  CIRCLE_CI_TOKEN?: string;
  GITHUB_WEBHOOK_SECRET?: string;
  CIRCLE_CI_WEBHOOK_SECRET?: string;
}

/** Single DO that polls CI and fans out status over WebSockets. */
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
    await this.state.storage.setAlarm(Date.now() + config.poll_in_seconds * 1000);
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
