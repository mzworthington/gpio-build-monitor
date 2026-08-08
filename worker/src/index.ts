export interface Env {
  ASSETS: Fetcher;
}

/**
 * Edge entry for monitor.mzworthington.co.uk.
 *
 * Static UI ships via Workers Assets (copied from monitor/web). Live WebSocket
 * status still requires the Pi process (or a future cloud aggregator).
 */
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === '/ws') {
      return new Response(
        JSON.stringify({
          error: 'websocket_unavailable',
          message:
            'Live status WebSocket is served by the Pi monitor process. GPIO and polling stay on-device; this Worker hosts the public UI shell.',
        }),
        {
          status: 503,
          headers: {
            'content-type': 'application/json; charset=utf-8',
            'cache-control': 'no-store',
          },
        },
      );
    }

    return env.ASSETS.fetch(request);
  },
} satisfies ExportedHandler<Env>;
