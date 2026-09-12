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
        security: null,
      }),
    ]);
  });

  it('keeps GitHub security findings and leaves CircleCI null', () => {
    expect(
      summarizeRepos([
        {
          repo: 'acme/web',
          workflow: 'CI',
          status: 'PASS',
          url: 'https://example.com/ci',
          security: {
            count: 2,
            url: 'https://github.com/acme/web/security',
            vulnerabilities: {
              count: 2,
              url: 'https://github.com/acme/web/security/dependabot',
              items: [],
            },
            codeql: {
              count: 0,
              url: 'https://github.com/acme/web/security/code-scanning',
              items: [],
            },
          },
        },
        {
          repo: 'acme/ops',
          workflow: 'build',
          status: 'PASS',
          url: 'https://example.com/ops',
          security: null,
        },
      ]),
    ).toEqual([
      expect.objectContaining({ repo: 'acme/ops', security: null }),
      expect.objectContaining({
        repo: 'acme/web',
        security: expect.objectContaining({ count: 2, vulnerabilities: expect.objectContaining({ count: 2 }) }),
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
