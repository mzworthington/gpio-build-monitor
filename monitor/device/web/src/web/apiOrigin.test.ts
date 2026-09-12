import { describe, expect, it } from 'vitest';
import { apiOrigin, statusHttpUrl, statusWsUrl } from './apiOrigin';

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
