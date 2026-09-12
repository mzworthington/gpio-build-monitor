import { describe, expect, it } from 'vitest';
import { isStatusHubPath, statusHubInternalPath } from './statusHubRoutes';

describe('isStatusHubPath', () => {
  it('forwards the live socket, refresh, and snapshot', () => {
    expect(isStatusHubPath('/ws')).toBe(true);
    expect(isStatusHubPath('/refresh')).toBe(true);
    expect(isStatusHubPath('/status')).toBe(true);
  });

  it('maps Alpine /api socket and snapshot onto the hub when Python is not proxied', () => {
    expect(statusHubInternalPath('/api/ws')).toBe('/ws');
    expect(statusHubInternalPath('/api/status')).toBe('/status');
    expect(isStatusHubPath('/api/ws')).toBe(true);
    expect(isStatusHubPath('/api/status')).toBe(true);
  });

  it('does not forward unrelated paths', () => {
    expect(isStatusHubPath('/')).toBe(false);
    expect(isStatusHubPath('/health')).toBe(false);
    expect(isStatusHubPath('/status/')).toBe(false);
  });
});
