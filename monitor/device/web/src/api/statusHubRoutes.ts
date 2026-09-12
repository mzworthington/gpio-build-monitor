export function statusHubInternalPath(pathname: string): string | null {
  if (pathname === '/ws' || pathname === '/api/ws') return '/ws';
  if (pathname === '/refresh' || pathname === '/api/refresh') return '/refresh';
  if (pathname === '/status' || pathname === '/api/status') return '/status';
  return null;
}

export function isStatusHubPath(pathname: string): boolean {
  return statusHubInternalPath(pathname) !== null;
}
