import {
  buildPushPayload,
  type PushMessage,
  type PushSubscription,
  type VapidKeys,
} from '@block65/webcrypto-web-push';
import type { AggregateStatus, BuildDetail } from './ci';

export interface StoredPushSubscription {
  endpoint: string;
  expirationTime: number | null;
  keys: {
    p256dh: string;
    auth: string;
  };
}

const SUB_KEY_PREFIX = 'push:sub:';

/** Edge-trigger: notify only when status newly becomes FAIL. */
export function shouldNotifyFailure(
  previous: AggregateStatus | null | undefined,
  next: AggregateStatus,
): boolean {
  return next === 'FAIL' && previous !== 'FAIL';
}

/** Edge-trigger: notify when aggregate recovers from FAIL to all PASS. */
export function shouldNotifyRecovery(
  previous: AggregateStatus | null | undefined,
  next: AggregateStatus,
  isRunning: boolean,
): boolean {
  // In-progress rebuilds drop the failed run from the settled rollup, which
  // can look like PASS before the new run finishes. Wait until it settles.
  if (isRunning) return false;
  return previous === 'FAIL' && next === 'PASS';
}

/**
 * Status stored for the next edge-trigger comparison.
 * Hold FAIL while a rebuild is in flight so recovery can still fire after settle.
 */
export function statusToRemember(
  previous: AggregateStatus | null | undefined,
  next: AggregateStatus,
  isRunning: boolean,
): AggregateStatus {
  if (isRunning && previous === 'FAIL' && next !== 'FAIL') {
    return 'FAIL';
  }
  return next;
}

export async function hashedPushSubscriptionKey(endpoint: string): Promise<string> {
  // Hash keeps DO keys short and stable (push endpoints are long URLs).
  const digest = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(endpoint),
  );
  const hex = [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
  return `${SUB_KEY_PREFIX}${hex}`;
}

export function isPushSubscription(value: unknown): value is StoredPushSubscription {
  if (!value || typeof value !== 'object') return false;
  const sub = value as Record<string, unknown>;
  if (typeof sub.endpoint !== 'string' || !sub.endpoint) return false;
  if (!sub.keys || typeof sub.keys !== 'object') return false;
  const keys = sub.keys as Record<string, unknown>;
  return typeof keys.p256dh === 'string' && typeof keys.auth === 'string';
}

export function parsePushSubscription(body: unknown): StoredPushSubscription | null {
  if (!isPushSubscription(body)) return null;
  return {
    endpoint: body.endpoint,
    expirationTime: typeof body.expirationTime === 'number' ? body.expirationTime : null,
    keys: {
      p256dh: body.keys.p256dh,
      auth: body.keys.auth,
    },
  };
}

function pushMessage(body: string, origin: string, urgency: 'high' | 'normal'): PushMessage {
  return {
    data: JSON.stringify({
      title: 'Build monitor',
      body,
      url: origin || '/',
    }),
    options: {
      // Keep long enough for a closed laptop to still receive it.
      ttl: 60 * 60,
      urgency,
    },
  };
}

export function failureNotificationMessage(
  builds: BuildDetail[],
  origin: string,
): PushMessage {
  const failed = builds.filter((b) => b.status === 'FAIL');
  const names = [...new Set(failed.map((b) => b.repo))];
  let body: string;
  if (names.length === 0) {
    body = 'At least one build failed';
  } else if (names.length === 1) {
    body = `${names[0]} failed`;
  } else if (names.length === 2) {
    body = `${names[0]} and ${names[1]} failed`;
  } else {
    body = `${names[0]} and ${names.length - 1} more failed`;
  }

  return pushMessage(body, origin, 'high');
}

export function recoveryNotificationMessage(origin: string): PushMessage {
  return pushMessage('All builds passing', origin, 'normal');
}

export function vapidFromEnv(env: {
  VAPID_PUBLIC_KEY?: string;
  VAPID_PRIVATE_KEY?: string;
  VAPID_SUBJECT?: string;
}): VapidKeys | null {
  const publicKey = env.VAPID_PUBLIC_KEY?.trim();
  const privateKey = env.VAPID_PRIVATE_KEY?.trim();
  if (!publicKey || !privateKey) return null;
  const subject = env.VAPID_SUBJECT?.trim() || 'mailto:monitor@mzworthington.co.uk';
  return { subject, publicKey, privateKey };
}

export async function sendWebPush(
  subscription: StoredPushSubscription,
  message: PushMessage,
  vapid: VapidKeys,
): Promise<{ ok: boolean; gone: boolean; status: number }> {
  const payload = await buildPushPayload(
    message,
    subscription as PushSubscription,
    vapid,
  );
  const res = await fetch(subscription.endpoint, payload);
  // 404/410: subscription expired or unsubscribed — drop it.
  const gone = res.status === 404 || res.status === 410;
  return { ok: res.ok, gone, status: res.status };
}

export { SUB_KEY_PREFIX };
