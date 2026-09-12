import { describe, expect, it } from 'vitest';
import { shownStatus } from './shownStatus';

describe('shownStatus', () => {
  it('keeps FAIL when a settled build failed even if another workflow is running', () => {
    expect(
      shownStatus({
        status: 'FAIL',
        is_running: true,
        fetching: false,
        builds: [
          { repo: 'acme/web', workflow: 'CI', status: 'FAIL', url: 'https://example.com/1' },
          { repo: 'acme/web', workflow: 'Deploy', status: 'RUNNING', url: 'https://example.com/2' },
        ],
      }),
    ).toBe('FAIL');
  });
});
