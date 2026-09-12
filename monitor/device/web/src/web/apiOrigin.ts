export function apiOrigin(configured: string | null | undefined, pageOrigin: string): string {
  const trimmed = configured?.trim() ?? '';
  return trimmed || pageOrigin;
}

export function statusWsUrl(origin: string): string {
  const url = new URL('/api/ws', origin);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return url.toString();
}

export function statusHttpUrl(origin: string): string {
  return new URL('/api/status', origin).toString();
}
