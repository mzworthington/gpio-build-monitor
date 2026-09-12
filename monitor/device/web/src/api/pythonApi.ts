export function isPythonApiPath(pathname: string): boolean {
  return (
    pathname === '/api/status' ||
    pathname === '/api/ws' ||
    pathname === '/api/health' ||
    pathname.startsWith('/api/webhooks/')
  );
}

export function pythonApiUrl(requestUrl: string, origin: string): string {
  const incoming = new URL(requestUrl);
  return new URL(`${incoming.pathname}${incoming.search}`, origin).toString();
}
