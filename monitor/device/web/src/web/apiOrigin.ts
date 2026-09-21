export const HOSTED_MONITOR_ORIGIN = 'https://monitor.mzworthington.co.uk';

export function apiOrigin(configured: string | null | undefined, pageOrigin: string): string {
  const trimmed = configured?.trim() ?? '';
  return trimmed || pageOrigin;
}

export function isPagesPreviewOrigin(pageOrigin: string): boolean {
  try {
    const host = new URL(pageOrigin).hostname;
    return host === 'gpio-build-monitor.pages.dev' || host.endsWith('.gpio-build-monitor.pages.dev');
  } catch {
    return false;
  }
}

/** Pages preview has no StatusHub; live status and push must hit the Worker. */
export function hostedApiOrigin(configured: string | null | undefined, pageOrigin: string): string {
  const trimmed = configured?.trim() ?? '';
  if (trimmed) return trimmed;
  if (isPagesPreviewOrigin(pageOrigin)) return HOSTED_MONITOR_ORIGIN;
  return pageOrigin;
}

export const pushApiOrigin = hostedApiOrigin;

export function statusWsUrl(origin: string): string {
  const url = new URL('/api/ws', origin);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return url.toString();
}

export function statusHttpUrl(origin: string): string {
  return new URL('/api/status', origin).toString();
}

export function pushVapidUrl(origin: string): string {
  if (!origin) return '/api/push/vapid-public-key';
  return new URL('/api/push/vapid-public-key', origin).toString();
}

export function pushSubscribeUrl(origin: string): string {
  if (!origin) return '/api/push/subscribe';
  return new URL('/api/push/subscribe', origin).toString();
}
