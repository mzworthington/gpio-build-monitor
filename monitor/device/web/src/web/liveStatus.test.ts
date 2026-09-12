import { describe, expect, it, vi } from 'vitest';
import { startLiveStatus, type LiveDocument } from './liveStatus';

describe('startLiveStatus', () => {
  it('opens the Python API websocket under /api/ws', () => {
    const opened: string[] = [];
    class FakeWebSocket {
      url: string;
      constructor(url: string) {
        this.url = url;
        opened.push(url);
      }
      addEventListener() {}
      close() {}
    }
    const document = {
      querySelector: () => ({ getAttribute: () => '' }),
      getElementById: () => ({ dataset: {}, textContent: '', hidden: false, replaceChildren() {}, querySelectorAll: () => [] }),
      fonts: undefined,
    };
    startLiveStatus({
      WebSocket: FakeWebSocket as unknown as typeof WebSocket,
      document: document as LiveDocument,
      locationOrigin: 'https://monitor.mzworthington.co.uk',
      MonitorApi: {
        apiOrigin: (_configured: string, pageOrigin: string) => pageOrigin,
        statusWsUrl: (origin: string) => `wss://${new URL(origin).host}/api/ws`,
      },
    });
    expect(opened).toEqual(['wss://monitor.mzworthington.co.uk/api/ws']);
  });

  it('applies parsed status snapshots from websocket messages', () => {
    const applySnapshot = vi.fn();
    const listeners: Record<string, Array<(event: { data: string }) => void>> = {};
    class FakeWebSocket {
      url: string;
      constructor(url: string) {
        this.url = url;
      }
      addEventListener(type: string, fn: (event: { data: string }) => void) {
        (listeners[type] ||= []).push(fn);
      }
      close() {}
    }
    const document = {
      querySelector: () => ({ getAttribute: () => '' }),
    };
    startLiveStatus({
      WebSocket: FakeWebSocket as unknown as typeof WebSocket,
      document: document as LiveDocument,
      locationOrigin: 'https://monitor.mzworthington.co.uk',
      MonitorApi: {
        apiOrigin: (_configured: string, pageOrigin: string) => pageOrigin,
        statusWsUrl: (origin: string) => `wss://${new URL(origin).host}/api/ws`,
      },
      applySnapshot,
    });
    listeners.message?.[0]?.({
      data: JSON.stringify({
        status: 'PASS',
        is_running: false,
        fetching: false,
        builds: [],
      }),
    });
    expect(applySnapshot).toHaveBeenCalledWith({
      status: 'PASS',
      is_running: false,
      fetching: false,
      builds: [],
    });
  });

  it('marks the connection live when the socket opens', () => {
    const setConnection = vi.fn();
    const listeners: Record<string, Array<() => void>> = {};
    class FakeWebSocket {
      addEventListener(type: string, fn: () => void) {
        (listeners[type] ||= []).push(fn);
      }
      close() {}
    }
    startLiveStatus({
      WebSocket: FakeWebSocket as unknown as typeof WebSocket,
      document: { querySelector: () => ({ getAttribute: () => '' }) },
      locationOrigin: 'https://monitor.mzworthington.co.uk',
      MonitorApi: {
        apiOrigin: (_configured: string, pageOrigin: string) => pageOrigin,
        statusWsUrl: (origin: string) => `wss://${new URL(origin).host}/api/ws`,
      },
      setConnection,
    });
    listeners.open?.[0]?.();
    expect(setConnection).toHaveBeenCalledWith('live', 'Live');
  });
});
