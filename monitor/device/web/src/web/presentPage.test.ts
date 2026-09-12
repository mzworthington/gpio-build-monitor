import { describe, expect, it } from 'vitest';
import {
  collectOpenFindings,
  collectOpenPulls,
  findingCardClass,
  openFindingKey,
  openPullKey,
  prChipClass,
  presentChrome,
  repoFindingKey,
  securityChipClass,
  summarizeRepos,
} from './presentPage';

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
        pull_requests: null,
        security: null,
      }),
    ]);
  });

  it('keeps GitHub pull requests and leaves CircleCI null', () => {
    const pulls = {
      count: 1,
      url: 'https://github.com/acme/web/pulls',
      items: [
        {
          number: 12,
          title: 'Ready',
          url: 'https://github.com/acme/web/pull/12',
          draft: false,
        },
      ],
    };
    expect(
      summarizeRepos([
        {
          repo: 'acme/web',
          workflow: 'CI',
          status: 'PASS',
          url: 'https://example.com/ci',
          pull_requests: pulls,
        },
        {
          repo: 'acme/ops',
          workflow: 'build',
          status: 'PASS',
          url: 'https://example.com/ops',
          pull_requests: null,
        },
      ]),
    ).toEqual([
      expect.objectContaining({ repo: 'acme/ops', pull_requests: null }),
      expect.objectContaining({ repo: 'acme/web', pull_requests: pulls }),
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

describe('open glances', () => {
  const repos = summarizeRepos([
    {
      repo: 'acme/web',
      workflow: 'CI',
      status: 'PASS',
      url: 'https://example.com/ci',
      pull_requests: {
        count: 2,
        url: 'https://github.com/acme/web/pulls',
        items: [
          { number: 12, title: 'Ready', url: 'https://github.com/acme/web/pull/12', draft: false },
          { number: 13, title: 'WIP', url: 'https://github.com/acme/web/pull/13', draft: true },
        ],
      },
      security: {
        count: 2,
        url: 'https://github.com/acme/web/security',
        vulnerabilities: {
          count: 1,
          url: 'https://github.com/acme/web/security/dependabot',
          items: [
            {
              number: 8,
              title: 'Prototype pollution',
              severity: 'high',
              url: 'https://github.com/acme/web/security/dependabot/8',
              state: 'open',
            },
          ],
        },
        codeql: {
          count: 1,
          url: 'https://github.com/acme/web/security/code-scanning',
          items: [
            {
              number: 9,
              title: 'Path injection',
              severity: 'critical',
              url: 'https://github.com/acme/web/security/code-scanning/9',
              state: 'open',
            },
          ],
        },
      },
    },
    {
      repo: 'acme/ops',
      workflow: 'build',
      status: 'PASS',
      url: 'https://example.com/ops',
      pull_requests: null,
      security: null,
    },
  ]);

  it('lists ready pull requests before drafts and skips CircleCI', () => {
    expect(collectOpenPulls(repos).map((item) => item.number)).toEqual([12, 13]);
  });

  it('tags findings with Dependabot or CodeQL and sorts by severity', () => {
    expect(collectOpenFindings(repos).map((item) => `${item.source}:${item.severity}`)).toEqual([
      'CodeQL:critical',
      'Dependabot:high',
    ]);
  });

  it('colors chips by count and worst severity', () => {
    const ops = repos.find((entry) => entry.repo === 'acme/ops');
    const web = repos.find((entry) => entry.repo === 'acme/web');
    expect(prChipClass(0)).toBe('chip chip-muted');
    expect(prChipClass(2)).toBe('chip chip-pr');
    expect(securityChipClass(ops?.security ?? null)).toBe('chip chip-muted');
    expect(securityChipClass(web?.security)).toBe('chip chip-find-hot');
    expect(findingCardClass('medium')).toBe('glance-card finding-medium');
  });

  it('keeps open-board keys distinct when repo names share a prefix', () => {
    expect(openPullKey({ repo: 'acme/web', number: 12 })).toBe('open-pr:acme/web:12');
    expect(openPullKey({ repo: 'acme/web1', number: 2 })).toBe('open-pr:acme/web1:2');
    expect(openFindingKey({ repo: 'acme/web', source: 'Dependabot', number: 8 })).toBe(
      'open-sec:acme/web:Dependabot:8',
    );
    expect(openFindingKey({ repo: 'acme/webDependabot', source: '', number: 8 })).toBe(
      'open-sec:acme/webDependabot::8',
    );
    expect(repoFindingKey({ source: 'Dependabot', number: 12 })).toBe('sec:Dependabot:12');
    expect(repoFindingKey({ source: 'Dependabot1', number: 2 })).toBe('sec:Dependabot1:2');
  });

  it('treats Dependabot findings without severity as needing attention', () => {
    expect(
      securityChipClass({
        count: 1,
        url: 'https://github.com/acme/web/security',
        vulnerabilities: {
          count: 1,
          url: 'https://github.com/acme/web/security/dependabot',
          items: [
            {
              number: 2,
              title: 'left-pad',
              severity: null,
              url: 'https://github.com/acme/web/security/dependabot/2',
              state: 'open',
            },
          ],
        },
        codeql: { count: 0, url: 'https://github.com/acme/web/security/code-scanning', items: [] },
      }),
    ).toBe('chip chip-find-warm');
  });
});
