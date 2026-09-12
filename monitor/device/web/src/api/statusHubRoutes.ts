export function isStatusHubPath(pathname: string): boolean {
  return pathname === '/ws' || pathname === '/refresh' || pathname === '/status';
}
