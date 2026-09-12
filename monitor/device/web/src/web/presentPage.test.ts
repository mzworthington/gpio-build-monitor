import { describe, expect, it } from 'vitest';
import { presentChrome, summarizeRepos } from './presentPage';

describe('summarizeRepos', () => {
  it('rolls a repo to FAIL when any settled workflow failed', () => {
    expect(
      summarizeRepos([
        { repo: 'acme/web', workflow: 'CI', status: 'FAIL', url: 'https://example.com/ci' },
        { repo: 'acme/web', workflow: 'Deploy', status: 'RUNNING', url: 'https://example.com/deploy' },
      ]),
    ).toEqual([
      expect.objectContaining({
        repo: 'acme/web',
        status: 'FAIL',
        is_running: true,
        workflow_count: 2,
      }),
    ]);
  });
});

describe('presentChrome', () => {
  it('turns the red light on for FAIL', () => {
    expect(
      presentChrome({
        status: 'FAIL',
        is_running: false,
        fetching: false,
        builds: [],
      }).lights.red,
    ).toBe('on');
  });
});
