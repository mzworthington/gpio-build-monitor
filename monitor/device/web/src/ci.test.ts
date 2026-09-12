import { afterEach, describe, expect, it, vi } from 'vitest';
import { aggregate, fetchAllBuilds, keepLastValidPayload } from './ci';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('aggregate', () => {
  it('uses RUNNING when every workflow is still in progress', () => {
    expect(
      aggregate([
        { repo: 'acme/web', workflow: 'CI', status: 'RUNNING', url: 'https://example.com/1' },
      ]),
    ).toEqual({ status: 'RUNNING', is_running: true });
  });

  it('uses WAITING when jobs are queued and none are executing', () => {
    expect(
      aggregate([
        { repo: 'acme/web', workflow: 'CI', status: 'WAITING', url: 'https://example.com/1' },
      ]),
    ).toEqual({ status: 'WAITING', is_running: true });
  });

  it('keeps NONE only when there are no builds at all', () => {
    expect(aggregate([])).toEqual({ status: 'NONE', is_running: false });
  });
});

describe('keepLastValidPayload', () => {
  it('keeps last PASS builds for a repo when the next snapshot is only CONNECTION_ERROR', () => {
    const previous = {
      type: 'status' as const,
      fetching: false,
      status: 'PASS' as const,
      is_running: false,
      builds: [
        { repo: 'acme/web', workflow: 'CI', status: 'PASS', url: 'https://example.com/1' },
      ],
      poll_in_seconds: 60,
      last_checked_at: 1,
      next_check_at: 61,
    };
    const next = {
      ...previous,
      status: 'CONNECTION_ERROR' as const,
      last_checked_at: 2,
      next_check_at: 62,
      builds: [
        {
          repo: 'acme/web',
          workflow: '(github workflows)',
          status: 'CONNECTION_ERROR',
          url: 'https://github.com/acme/web',
        },
      ],
    };
    expect(keepLastValidPayload(previous, next).builds).toEqual(previous.builds);
    expect(keepLastValidPayload(previous, next).status).toBe('PASS');
  });

  it('drops remembered CONNECTION_ERROR repos that the new snapshot does not include', () => {
    const previous = {
      type: 'status' as const,
      fetching: false,
      status: 'CONNECTION_ERROR' as const,
      is_running: false,
      builds: [
        { repo: 'acme/web', workflow: 'CI', status: 'PASS', url: 'https://example.com/1' },
        {
          repo: 'acme/dotfiles',
          workflow: '(missing GITHUB_TOKEN)',
          status: 'CONNECTION_ERROR',
          url: 'https://github.com/acme/dotfiles',
        },
      ],
      poll_in_seconds: 60,
      last_checked_at: 1,
      next_check_at: 61,
    };
    const next = {
      ...previous,
      status: 'PASS' as const,
      last_checked_at: 2,
      next_check_at: 62,
      builds: [
        { repo: 'acme/web', workflow: 'CI', status: 'PASS', url: 'https://example.com/1' },
      ],
    };
    expect(keepLastValidPayload(previous, next).builds).toEqual(next.builds);
    expect(keepLastValidPayload(previous, next).status).toBe('PASS');
  });
});

describe('fetchAllBuilds CircleCI', () => {
  it('returns null security findings', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: string | URL) => {
      const url = String(input);
      if (url.includes('/pipeline/') && url.includes('/workflow')) {
        return Response.json({
          items: [
            {
              id: 'wf-1',
              name: 'build',
              status: 'success',
              created_at: '2020-01-02T00:00:00Z',
            },
          ],
        });
      }
      if (url.includes('/pipeline')) {
        return Response.json({ items: [{ id: 'pipe-1' }] });
      }
      return new Response('not found', { status: 404 });
    }));

    const builds = await fetchAllBuilds(
      {
        poll_in_seconds: 60,
        integrations: [{ type: 'CIRCLECI', username: 'super-man', repo: 'awesome' }],
      },
      { circleToken: 'secret' },
    );

    expect(builds).toEqual([
      {
        repo: 'super-man/awesome',
        workflow: 'build',
        status: 'PASS',
        url: 'https://github.com/super-man/awesome',
        security: null,
        pull_requests: null,
      },
    ]);
  });
});
