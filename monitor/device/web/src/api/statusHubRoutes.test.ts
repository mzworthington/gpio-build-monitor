import { describe, expect, it } from 'vitest';
import { isStatusHubPath } from './statusHubRoutes';

describe('isStatusHubPath', () => {
  it('forwards the live socket, refresh, and snapshot', () => {
    expect(isStatusHubPath('/ws')).toBe(true);
    expect(isStatusHubPath('/refresh')).toBe(true);
    expect(isStatusHubPath('/status')).toBe(true);
  });

  it('does not forward unrelated paths', () => {
    expect(isStatusHubPath('/')).toBe(false);
    expect(isStatusHubPath('/health')).toBe(false);
    expect(isStatusHubPath('/status/')).toBe(false);
  });
});
