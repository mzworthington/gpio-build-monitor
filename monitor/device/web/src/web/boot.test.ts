import { describe, expect, it, vi } from 'vitest';
import { bootMonitor, type MonitorApiHost } from './boot';
import type { LiveDocument } from './liveStatus';

describe('bootMonitor', () => {
  it('registers monitor then starts Alpine', () => {
    const alpine = { data: vi.fn(), start: vi.fn() };
    bootMonitor(alpine);
    expect(alpine.data).toHaveBeenCalledWith('monitor', expect.any(Function));
    expect(alpine.start).toHaveBeenCalledOnce();
  });

  it('exposes API origin helpers for the Pages client', () => {
    const alpine = { data: vi.fn(), start: vi.fn() };
    const host: MonitorApiHost = {};
    bootMonitor(alpine, host);
    expect(host.MonitorApi?.statusWsUrl('https://api.example')).toBe('wss://api.example/api/ws');
    expect(host.MonitorApi?.statusHttpUrl('https://api.example')).toBe('https://api.example/api/status');
  });

  it('connects the Alpine page to the Python API websocket', () => {
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
    const alpine = { data: vi.fn(), start: vi.fn(), $data: vi.fn() };
    const host: MonitorApiHost = {
      WebSocket: FakeWebSocket as unknown as typeof WebSocket,
      document: {
        querySelector: () => ({ getAttribute: () => '' }),
      } as LiveDocument,
      location: { origin: 'https://monitor.mzworthington.co.uk' },
    };
    bootMonitor(alpine, host);
    expect(opened).toEqual(['wss://monitor.mzworthington.co.uk/api/ws']);
  });
});
