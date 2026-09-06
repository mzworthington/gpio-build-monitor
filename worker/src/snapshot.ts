import type { AggregateStatus, StatusPayload } from './ci';

export const SLEEP_RUNNING_SECONDS = 120;
export const SLEEP_ATTENTION_SECONDS = 180;
export const SLEEP_FETCH_ERROR_SECONDS = 300;
export const SLEEP_SETTLED_SECONDS = 900;

const GLANCEABLE = new Set([
  'FAIL',
  'CONNECTION_ERROR',
  'APPROVAL',
  'UNKNOWN',
  'RUNNING',
  'WAITING',
]);

export function sleepSeconds(status: AggregateStatus, isRunning: boolean): number {
  if (isRunning) return SLEEP_RUNNING_SECONDS;
  if (status === 'FAIL' || status === 'UNKNOWN' || status === 'APPROVAL') {
    return SLEEP_ATTENTION_SECONDS;
  }
  if (status === 'CONNECTION_ERROR') return SLEEP_FETCH_ERROR_SECONDS;
  return SLEEP_SETTLED_SECONDS;
}

export function snapshotEtag(payload: StatusPayload): string {
  const body = JSON.stringify({
    builds: payload.builds,
    is_running: payload.is_running,
    status: payload.status,
  });
  const digest = hexSha256(body).slice(0, 16);
  return `W/"${digest}"`;
}

export function einkPayload(payload: StatusPayload): StatusPayload & { sleep_seconds: number } {
  return {
    type: 'status',
    fetching: false,
    status: payload.status,
    is_running: payload.is_running,
    builds: payload.builds.filter((build) => GLANCEABLE.has(build.status)),
    poll_in_seconds: payload.poll_in_seconds,
    last_checked_at: payload.last_checked_at,
    next_check_at: payload.next_check_at,
    sleep_seconds: sleepSeconds(payload.status, payload.is_running),
  };
}

export function etagMatches(ifNoneMatch: string | null, etag: string): boolean {
  if (!ifNoneMatch) return false;
  const offered = ifNoneMatch.split(',').map((part) => part.trim()).filter(Boolean);
  return offered.includes('*') || offered.includes(etag);
}

export function statusSnapshotResponse(request: Request, payload: StatusPayload): Response {
  const etag = snapshotEtag(payload);
  const seconds = sleepSeconds(payload.status, payload.is_running);
  const headers = {
    'Cache-Control': 'no-store',
    ETag: etag,
    'Retry-After': String(seconds),
  };
  if (etagMatches(request.headers.get('If-None-Match'), etag)) {
    return new Response(null, { status: 304, headers });
  }

  const url = new URL(request.url);
  const body =
    url.searchParams.get('view') === 'eink'
      ? einkPayload(payload)
      : { ...payload, sleep_seconds: seconds };
  return Response.json(body, { headers });
}

function hexSha256(value: string): string {
  // FNV-1a 64-bit is enough for a weak ETag of this payload; Workers have
  // crypto.subtle but this helper stays sync for unit tests.
  let hash = 0xcbf29ce484222325n;
  for (const byte of new TextEncoder().encode(value)) {
    hash ^= BigInt(byte);
    hash = (hash * 0x100000001b3n) & 0xffffffffffffffffn;
  }
  return hash.toString(16).padStart(16, '0');
}
