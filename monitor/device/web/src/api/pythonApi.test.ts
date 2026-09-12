import { describe, expect, it } from 'vitest';
import { isPythonApiPath, pythonApiUrl } from './pythonApi';

describe('pythonApiUrl', () => {
  it('forwards /api paths to the Python origin', () => {
    expect(isPythonApiPath('/api/status')).toBe(true);
    expect(isPythonApiPath('/api/ws')).toBe(true);
    expect(isPythonApiPath('/api/health')).toBe(true);
    expect(isPythonApiPath('/api/webhooks/github')).toBe(true);
    expect(isPythonApiPath('/')).toBe(false);
    expect(
      pythonApiUrl(
        'https://monitor.mzworthington.co.uk/api/status?view=eink',
        'http://127.0.0.1:8080',
      ),
    ).toBe('http://127.0.0.1:8080/api/status?view=eink');
  });
});
