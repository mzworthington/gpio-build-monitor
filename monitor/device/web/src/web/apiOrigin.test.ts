import { describe, expect, it } from 'vitest';
import {
  apiOrigin,
  HOSTED_MONITOR_ORIGIN,
  hostedApiOrigin,
  isPagesPreviewOrigin,
  pushSubscribeUrl,
  pushVapidUrl,
  statusHttpUrl,
  statusWsUrl,
} from './apiOrigin';

describe('apiOrigin', () => {
  it('uses the configured API origin when the Pages meta is set', () => {
    expect(apiOrigin('https://api.monitor.mzworthington.co.uk', 'https://monitor.mzworthington.co.uk')).toBe(
      'https://api.monitor.mzworthington.co.uk',
    );
  });

  it('falls back to the page origin when no API origin is configured', () => {
    expect(apiOrigin('', 'https://monitor.mzworthington.co.uk')).toBe(
      'https://monitor.mzworthington.co.uk',
    );
  });

  it('opens the status websocket on the API origin', () => {
    expect(statusWsUrl('https://monitor.mzworthington.co.uk')).toBe(
      'wss://monitor.mzworthington.co.uk/api/ws',
    );
  });

  it('pulls the status snapshot under /api', () => {
    expect(statusHttpUrl('https://monitor.mzworthington.co.uk')).toBe(
      'https://monitor.mzworthington.co.uk/api/status',
    );
  });
});

describe('hostedApiOrigin', () => {
  it('keeps same-origin on the public Worker hostname', () => {
    expect(hostedApiOrigin('', HOSTED_MONITOR_ORIGIN)).toBe(HOSTED_MONITOR_ORIGIN);
  });

  it('sends Pages preview and branch aliases to the Worker', () => {
    expect(isPagesPreviewOrigin('https://gpio-build-monitor.pages.dev')).toBe(true);
    expect(isPagesPreviewOrigin('https://abc123.gpio-build-monitor.pages.dev')).toBe(true);
    expect(isPagesPreviewOrigin(HOSTED_MONITOR_ORIGIN)).toBe(false);
    expect(hostedApiOrigin('', 'https://gpio-build-monitor.pages.dev')).toBe(HOSTED_MONITOR_ORIGIN);
    expect(hostedApiOrigin('', 'https://abc123.gpio-build-monitor.pages.dev')).toBe(
      HOSTED_MONITOR_ORIGIN,
    );
  });

  it('still honors an explicit meta origin', () => {
    expect(
      hostedApiOrigin('https://api.monitor.mzworthington.co.uk', 'https://gpio-build-monitor.pages.dev'),
    ).toBe('https://api.monitor.mzworthington.co.uk');
  });

  it('builds push URLs on the Worker from a Pages preview', () => {
    const origin = hostedApiOrigin('', 'https://gpio-build-monitor.pages.dev');
    expect(pushVapidUrl(origin)).toBe(`${HOSTED_MONITOR_ORIGIN}/api/push/vapid-public-key`);
    expect(pushSubscribeUrl(origin)).toBe(`${HOSTED_MONITOR_ORIGIN}/api/push/subscribe`);
  });
});
