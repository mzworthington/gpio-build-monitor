import { describe, expect, it } from 'vitest';
import type { BuildDetail } from '../src/ci';
import type { AggregateStatus } from '../src/ci';
import {
  failureNotificationMessage,
  isPushSubscription,
  parsePushSubscription,
  recoveryNotificationMessage,
  shouldNotifyFailure,
  shouldNotifyRecovery,
  statusToRemember,
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

describe('shouldNotifyRecovery', () => {
  it('notifies only on FAIL → PASS once builds have settled', () => {
    expect(shouldNotifyRecovery('FAIL', 'PASS', false)).toBe(true);
  });

  it('does not notify FAIL → PASS while a rebuild is still in progress', () => {
    expect(shouldNotifyRecovery('FAIL', 'PASS', true)).toBe(false);
  });

  it('does not notify for other transitions into PASS', () => {
    expect(shouldNotifyRecovery('NONE', 'PASS', false)).toBe(false);
    expect(shouldNotifyRecovery('APPROVAL', 'PASS', false)).toBe(false);
    expect(shouldNotifyRecovery('CONNECTION_ERROR', 'PASS', false)).toBe(false);
    expect(shouldNotifyRecovery(null, 'PASS', false)).toBe(false);
    expect(shouldNotifyRecovery(undefined, 'PASS', false)).toBe(false);
  });

  it('does not notify while still FAIL or still PASS', () => {
    expect(shouldNotifyRecovery('FAIL', 'FAIL', false)).toBe(false);
    expect(shouldNotifyRecovery('PASS', 'PASS', false)).toBe(false);
  });

  it('does not notify FAIL → non-PASS', () => {
    expect(shouldNotifyRecovery('FAIL', 'APPROVAL', false)).toBe(false);
    expect(shouldNotifyRecovery('FAIL', 'CONNECTION_ERROR', false)).toBe(false);
    expect(shouldNotifyRecovery('FAIL', 'NONE', true)).toBe(false);
  });
});

describe('statusToRemember', () => {
  it('holds FAIL while a rebuild is in progress so recovery can fire later', () => {
    expect(statusToRemember('FAIL', 'PASS', true)).toBe('FAIL');
    expect(statusToRemember('FAIL', 'NONE', true)).toBe('FAIL');
  });

  it('records the settled status when nothing is in progress', () => {
    expect(statusToRemember('FAIL', 'PASS', false)).toBe('PASS');
    expect(statusToRemember('PASS', 'FAIL', false)).toBe('FAIL');
  });

  it('records FAIL immediately even if other builds are still running', () => {
    expect(statusToRemember('PASS', 'FAIL', true)).toBe('FAIL');
    expect(statusToRemember('FAIL', 'FAIL', true)).toBe('FAIL');
  });
});

describe('recovery after a rebuild', () => {
  it('waits for the in-progress build, then notifies once it passes', () => {
    let previous: AggregateStatus | null = 'FAIL';

    const duringRebuild = {
      notify: shouldNotifyRecovery(previous, 'PASS', true),
      remember: statusToRemember(previous, 'PASS', true),
    };
    expect(duringRebuild.notify).toBe(false);
    expect(duringRebuild.remember).toBe('FAIL');

    previous = duringRebuild.remember;
    const settled = {
      notify: shouldNotifyRecovery(previous, 'PASS', false),
      remember: statusToRemember(previous, 'PASS', false),
    };
    expect(settled.notify).toBe(true);
    expect(settled.remember).toBe('PASS');
  });

  it('does not send recovery when the rebuild fails again', () => {
    let previous: AggregateStatus | null = 'FAIL';
    previous = statusToRemember(previous, 'PASS', true);
    expect(shouldNotifyRecovery(previous, 'FAIL', false)).toBe(false);
    expect(shouldNotifyFailure(previous, 'FAIL')).toBe(false);
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

describe('recoveryNotificationMessage', () => {
  it('reports all builds passing', () => {
    const message = recoveryNotificationMessage('https://monitor.example');
    expect(message.data).toContain('All builds passing');
    expect(message.data).toContain('https://monitor.example');
    expect(message.options?.urgency).toBe('normal');
  });
});
