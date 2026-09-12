import { describe, expect, it } from 'vitest';
import type { StatusPayload } from '../ci';
import {
  einkPayload,
  einkRepoPayload,
  etagMatches,
  sleepSeconds,
  snapshotEtag,
  statusSnapshotResponse,
} from './snapshot';

const failPayload: StatusPayload = {
  type: 'status',
  fetching: true,
  status: 'FAIL',
  is_running: true,
  builds: [
    {
      repo: 'acme/web',
      workflow: 'CI',
      status: 'FAIL',
      url: 'https://example.com/1',
    },
    {
      repo: 'acme/web',
      workflow: 'Deploy',
      status: 'PASS',
      url: 'https://example.com/2',
    },
    {
      repo: 'acme/api',
      workflow: 'CI',
      status: 'RUNNING',
      url: 'https://example.com/3',
    },
  ],
  poll_in_seconds: 30,
  last_checked_at: 100,
  next_check_at: 130,
};

describe('sleepSeconds', () => {
  it('favours running over green', () => {
    expect(sleepSeconds('PASS', true)).toBe(120);
    expect(sleepSeconds('PASS', false)).toBe(900);
  });

  it('shortens when the panel needs attention', () => {
    expect(sleepSeconds('FAIL', false)).toBe(180);
    expect(sleepSeconds('UNKNOWN', false)).toBe(180);
    expect(sleepSeconds('APPROVAL', false)).toBe(180);
    expect(sleepSeconds('CONNECTION_ERROR', false)).toBe(300);
    expect(sleepSeconds('NONE', false)).toBe(900);
  });
});

describe('snapshotEtag', () => {
  it('changes when only pr_count changes', () => {
    const zero = snapshotEtag({
      ...failPayload,
      status: 'PASS',
      is_running: false,
      builds: [
        {
          repo: 'acme/web',
          workflow: 'CI',
          status: 'PASS',
          url: 'https://example.com/1',
          pr_count: 0,
          pr_url: 'https://github.com/acme/web/pulls',
        },
      ],
    });
    const four = snapshotEtag({
      ...failPayload,
      status: 'PASS',
      is_running: false,
      builds: [
        {
          repo: 'acme/web',
          workflow: 'CI',
          status: 'PASS',
          url: 'https://example.com/1',
          pr_count: 4,
          pr_url: 'https://github.com/acme/web/pulls',
        },
      ],
    });
    expect(zero).not.toBe(four);
  });

  it('changes when only security count changes', () => {
    const zero = snapshotEtag({
      ...failPayload,
      status: 'PASS',
      is_running: false,
      builds: [
        {
          repo: 'acme/web',
          workflow: 'CI',
          status: 'PASS',
          url: 'https://example.com/1',
          security: {
            count: 0,
            url: 'https://github.com/acme/web/security',
            vulnerabilities: {
              count: 0,
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
      ],
    });
    const two = snapshotEtag({
      ...failPayload,
      status: 'PASS',
      is_running: false,
      builds: [
        {
          repo: 'acme/web',
          workflow: 'CI',
          status: 'PASS',
          url: 'https://example.com/1',
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
      ],
    });
    expect(zero).not.toBe(two);
  });
});

describe('einkPayload', () => {
  it('lists every checked repo with action and pr counts', () => {
    const compact = einkPayload(failPayload);
    expect(compact.repos).toEqual([
      {
        repo: 'acme/api',
        status: 'RUNNING',
        workflow_count: 1,
        pr_count: 0,
        security_count: 0,
        is_running: true,
      },
      {
        repo: 'acme/web',
        status: 'FAIL',
        workflow_count: 2,
        pr_count: 0,
        security_count: 0,
        is_running: false,
      },
    ]);
  });

  it('omits builds, open_prs, and nested workflows', () => {
    const compact = einkPayload(failPayload);
    expect(compact.fetching).toBe(false);
    expect(compact.sleep_seconds).toBe(120);
    expect(compact).not.toHaveProperty('builds');
    expect(compact).not.toHaveProperty('open_prs');
    expect(compact.repos[0]).not.toHaveProperty('workflows');
  });

  it('uses RUNNING when the hub still reports NONE for in-progress jobs', () => {
    const compact = einkPayload({
      type: 'status',
      fetching: false,
      status: 'NONE',
      is_running: true,
      builds: [
        {
          repo: 'acme/web',
          workflow: 'CI',
          status: 'RUNNING',
          url: 'https://example.com/1',
        },
      ],
      poll_in_seconds: 30,
      last_checked_at: 100,
      next_check_at: 130,
    });
    expect(compact.status).toBe('RUNNING');
    expect(compact.repos[0]?.status).toBe('RUNNING');
  });

  it('keeps pr_count on green repos', () => {
    const compact = einkPayload({
      type: 'status',
      fetching: false,
      status: 'PASS',
      is_running: false,
      builds: [
        {
          repo: 'acme/web',
          workflow: 'CI',
          status: 'PASS',
          url: 'https://example.com/1',
          pr_count: 4,
          pr_url: 'https://github.com/acme/web/pulls',
        },
      ],
      poll_in_seconds: 30,
      last_checked_at: 100,
      next_check_at: 130,
    });
    expect(compact.repos).toEqual([
      {
        repo: 'acme/web',
        status: 'PASS',
        workflow_count: 1,
        pr_count: 4,
        security_count: 0,
        is_running: false,
      },
    ]);
  });

  it('includes capped workflows for a single repo', () => {
    const builds = Array.from({ length: 18 }, (_, i) => ({
      repo: 'acme/web',
      workflow: `W${String(i).padStart(2, '0')}`,
      status: i === 0 ? 'FAIL' : 'PASS',
      url: `https://example.com/${i}`,
    }));
    const compact = einkRepoPayload({ ...failPayload, builds }, 'acme/web');
    expect(compact.repos[0]?.workflow_count).toBe(18);
    expect(compact.repos[0]?.workflows).toHaveLength(16);
    expect(compact.repos[0]?.workflows?.[0]).toEqual({ workflow: 'W00', status: 'FAIL' });
  });
});

describe('statusSnapshotResponse', () => {
  it('returns 304 when If-None-Match matches', async () => {
    const etag = snapshotEtag(failPayload);
    const response = statusSnapshotResponse(
      new Request('https://monitor.example/status', {
        headers: { 'If-None-Match': etag },
      }),
      failPayload,
    );
    expect(response.status).toBe(304);
    expect(response.headers.get('ETag')).toBe(etag);
    expect(response.headers.get('Retry-After')).toBe('120');
    expect(await response.text()).toBe('');
  });

  it('returns a compact body for view=eink', async () => {
    const response = statusSnapshotResponse(
      new Request('https://monitor.example/status?view=eink'),
      failPayload,
    );
    expect(response.status).toBe(200);
    const body = (await response.json()) as {
      sleep_seconds: number;
      fetching: boolean;
      builds?: unknown;
      repos: Array<{ workflows?: unknown }>;
    };
    expect(body.sleep_seconds).toBe(120);
    expect(body.builds).toBeUndefined();
    expect(body.repos[0]?.workflows).toBeUndefined();
    expect(body.fetching).toBe(false);
  });

  it('returns workflows for view=eink&repo=', async () => {
    const response = statusSnapshotResponse(
      new Request('https://monitor.example/status?view=eink&repo=acme/web'),
      failPayload,
    );
    const body = (await response.json()) as {
      repos: Array<{ repo: string; workflows: Array<{ workflow: string }> }>;
    };
    expect(body.repos).toHaveLength(1);
    expect(body.repos[0]?.repo).toBe('acme/web');
    expect(body.repos[0]?.workflows.map((row) => row.workflow)).toEqual(['CI', 'Deploy']);
  });
});

describe('etagMatches', () => {
  it('accepts a matching weak tag in a list', () => {
    expect(etagMatches('W/"abc", W/"def"', 'W/"def"')).toBe(true);
    expect(etagMatches(null, 'W/"def"')).toBe(false);
  });
});
