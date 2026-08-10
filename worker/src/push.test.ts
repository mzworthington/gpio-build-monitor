import { describe, expect, it } from 'vitest';
import type { BuildDetail } from '../src/ci';
import {
  failureNotificationMessage,
  isPushSubscription,
  parsePushSubscription,
  shouldNotifyFailure,
} from '../src/push';

describe('shouldNotifyFailure', () => {
  it('notifies on transition into FAIL', () => {
    expect(shouldNotifyFailure('PASS', 'FAIL')).toBe(true);
    expect(shouldNotifyFailure('NONE', 'FAIL')).toBe(true);
    expect(shouldNotifyFailure(null, 'FAIL')).toBe(true);
    expect(shouldNotifyFailure(undefined, 'FAIL')).toBe(true);
  });

  it('does not re-notify while still FAIL', () => {
    expect(shouldNotifyFailure('FAIL', 'FAIL')).toBe(false);
  });

  it('does not notify for non-FAIL statuses', () => {
    expect(shouldNotifyFailure('PASS', 'PASS')).toBe(false);
    expect(shouldNotifyFailure('FAIL', 'PASS')).toBe(false);
    expect(shouldNotifyFailure('NONE', 'CONNECTION_ERROR')).toBe(false);
  });
});

describe('parsePushSubscription', () => {
  it('accepts a browser PushSubscriptionJSON shape', () => {
    const sub = parsePushSubscription({
      endpoint: 'https://fcm.googleapis.com/fcm/send/abc',
      expirationTime: null,
      keys: { p256dh: 'p', auth: 'a' },
    });
    expect(sub?.endpoint).toContain('fcm.googleapis.com');
    expect(isPushSubscription(sub)).toBe(true);
  });

  it('rejects incomplete payloads', () => {
    expect(parsePushSubscription({ endpoint: 'x' })).toBeNull();
    expect(parsePushSubscription(null)).toBeNull();
  });
});

describe('failureNotificationMessage', () => {
  it('summarises failed repos', () => {
    const builds: BuildDetail[] = [
      { repo: 'gpio-build-monitor', workflow: 'CI', status: 'FAIL', url: 'https://example.com/1' },
      { repo: 'other', workflow: 'CI', status: 'PASS', url: 'https://example.com/2' },
    ];
    const message = failureNotificationMessage(builds, 'https://monitor.example');
    expect(message.data).toContain('gpio-build-monitor failed');
    expect(message.data).toContain('https://monitor.example');
  });
});
