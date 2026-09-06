import { describe, expect, it } from 'vitest';
import type { StatusPayload } from './ci';
import {
  einkPayload,
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
});

describe('einkPayload', () => {
  it('keeps only glanceable builds and adds sleep_seconds', () => {
    const compact = einkPayload(failPayload);
    expect(compact.fetching).toBe(false);
    expect(compact.sleep_seconds).toBe(120);
    expect(compact.builds.map((build) => build.workflow)).toEqual(['CI', 'CI']);
  });

  it('keeps open_prs when workflows are green', () => {
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
    expect(compact.builds).toEqual([]);
    expect(compact.open_prs).toEqual([
      {
        repo: 'acme/web',
        pr_count: 4,
        pr_url: 'https://github.com/acme/web/pulls',
      },
    ]);
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
      builds: unknown[];
      fetching: boolean;
    };
    expect(body.sleep_seconds).toBe(120);
    expect(body.builds).toHaveLength(2);
    expect(body.fetching).toBe(false);
  });
});

describe('etagMatches', () => {
  it('accepts a matching weak tag in a list', () => {
    expect(etagMatches('W/"abc", W/"def"', 'W/"def"')).toBe(true);
    expect(etagMatches(null, 'W/"def"')).toBe(false);
  });
});
