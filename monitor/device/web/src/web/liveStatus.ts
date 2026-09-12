export type LiveStatusApi = {
  apiOrigin: (configured: string, pageOrigin: string) => string;
  statusWsUrl: (origin: string) => string;
};

export type LiveDocument = {
  querySelector: (selector: string) => {
    getAttribute?: (name: string) => string | null;
  } | null;
};

export type LiveStatusHost = {
  WebSocket: typeof WebSocket;
  document: LiveDocument;
  locationOrigin: string;
  MonitorApi: LiveStatusApi;
  applySnapshot?: (snapshot: unknown) => void;
  setConnection?: (state: string, label: string) => void;
  setTimeout?: (fn: () => void, ms: number) => number;
};

export function startLiveStatus(host: LiveStatusHost): WebSocket {
  const meta = host.document.querySelector('meta[name="monitor-api-origin"]');
  const configured = meta?.getAttribute?.('content') || '';
  const origin = host.MonitorApi.apiOrigin(configured, host.locationOrigin);
  const url = host.MonitorApi.statusWsUrl(origin);
  const schedule = host.setTimeout ?? ((fn: () => void, ms: number) => globalThis.setTimeout(fn, ms));
  let retryMs = 1000;
  let socket: WebSocket;

  const connect = (): WebSocket => {
    socket = new host.WebSocket(url);
    socket.addEventListener('open', () => {
      retryMs = 1000;
      host.setConnection?.('live', 'Live');
    });
    socket.addEventListener('message', (event: MessageEvent) => {
      try {
        host.applySnapshot?.(JSON.parse(String(event.data)));
      } catch {
        // Invalid payloads leave the last good snapshot on screen.
      }
    });
    socket.addEventListener('close', () => {
      host.setConnection?.('offline', 'Reconnecting…');
      schedule(connect, retryMs);
      retryMs = Math.min(retryMs * 2, 15000);
    });
    socket.addEventListener('error', () => {
      socket.close();
    });
    return socket;
  };

  return connect();
}
