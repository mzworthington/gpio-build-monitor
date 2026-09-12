import { apiOrigin, statusHttpUrl, statusWsUrl } from './apiOrigin';
import { startLiveStatus, type LiveDocument } from './liveStatus';
import { registerMonitor, type AlpineHost, type MonitorPage, type MonitorSnapshot } from './monitor';

export type AlpineRuntime = AlpineHost & { start: () => void };

function monitorPage(alpine: AlpineRuntime, root: object): MonitorPage | undefined {
  return (
    alpine.$data?.(root as never) ??
    (root as { _x_dataStack?: MonitorPage[] })._x_dataStack?.[0]
  );
}

export type MonitorApiHost = {
  MonitorApi?: {
    apiOrigin: typeof apiOrigin;
    statusHttpUrl: typeof statusHttpUrl;
    statusWsUrl: typeof statusWsUrl;
  };
  WebSocket?: typeof WebSocket;
  document?: LiveDocument;
  location?: { origin: string };
};

export function bootMonitor(
  alpine: AlpineRuntime,
  host: MonitorApiHost = globalThis as MonitorApiHost,
): void {
  host.MonitorApi = { apiOrigin, statusHttpUrl, statusWsUrl };
  registerMonitor(alpine);
  alpine.start();
  if (!host.WebSocket || !host.document || !host.location) return;
  startLiveStatus({
    WebSocket: host.WebSocket,
    document: host.document,
    locationOrigin: host.location.origin,
    MonitorApi: host.MonitorApi,
    applySnapshot: (snapshot) => {
      const root = host.document?.querySelector('[x-data="monitor"]');
      if (!root) return;
      monitorPage(alpine, root)?.applySnapshot(snapshot as MonitorSnapshot);
    },
    setConnection: (state, label) => {
      const root = host.document?.querySelector('[x-data="monitor"]');
      if (!root) return;
      monitorPage(alpine, root)?.setConnection(state, label);
    },
  });
}
