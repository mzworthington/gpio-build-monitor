import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchAllBuilds } from './ci';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('fetchAllBuilds GitHub', () => {
  it('retries actions/runs without credentials after an authenticated 403', async () => {
    const fetchMock = vi.fn(async (input: string | URL, init?: RequestInit) => {
      const url = String(input);
      const headers = new Headers(init?.headers);
      const authed = headers.has('Authorization');
      if (url.includes('/actions/workflows')) {
        return Response.json({
          workflows: [{ id: 1001, state: 'active' }],
        });
      }
      if (url.includes('/actions/runs')) {
        if (authed) {
          return Response.json(
            { message: 'API rate limit exceeded' },
            { status: 403 },
          );
        }
        return Response.json({
          workflow_runs: [
            {
              id: 1,
              workflow_id: 1001,
              name: 'CI',
              html_url: 'https://example.com/ci',
              created_at: '2020-01-02T00:00:00Z',
              status: 'completed',
              conclusion: 'success',
              head_branch: 'main',
            },
          ],
        });
      }
      return new Response('not found', { status: 404 });
    });
    vi.stubGlobal('fetch', fetchMock);

    const builds = await fetchAllBuilds(
      {
        poll_in_seconds: 60,
        integrations: [
          { type: 'GITHUB', username: 'super-man', repo: 'awesome' },
        ],
      },
      { githubToken: 'secret' },
    );

    expect(builds).toEqual([
      {
        repo: 'super-man/awesome',
        workflow: 'CI',
        status: 'PASS',
        url: 'https://example.com/ci',
        pr_count: null,
        pr_url: null,
      },
    ]);
    const runCalls = fetchMock.mock.calls.filter((call) =>
      String(call[0]).includes('/actions/runs'),
    );
    expect(runCalls).toHaveLength(2);
  });

  it('counts open pull requests including drafts without changing CI status', async () => {
    const fetchMock = vi.fn(async (input: string | URL) => {
      const url = String(input);
      if (url.includes('/actions/workflows')) {
        return Response.json({
          workflows: [{ id: 1001, state: 'active' }],
        });
      }
      if (url.includes('/actions/runs')) {
        return Response.json({
          workflow_runs: [
            {
              id: 1,
              workflow_id: 1001,
              name: 'CI',
              html_url: 'https://example.com/ci',
              created_at: '2020-01-02T00:00:00Z',
              status: 'completed',
              conclusion: 'success',
              head_branch: 'main',
            },
          ],
        });
      }
      if (url.includes('/pulls')) {
        return Response.json([{ number: 1, draft: false }, { number: 2, draft: true }]);
      }
      return new Response('not found', { status: 404 });
    });
    vi.stubGlobal('fetch', fetchMock);

    const builds = await fetchAllBuilds(
      {
        poll_in_seconds: 60,
        integrations: [
          { type: 'GITHUB', username: 'super-man', repo: 'awesome' },
        ],
      },
      { githubToken: 'secret' },
    );

    expect(builds).toEqual([
      {
        repo: 'super-man/awesome',
        workflow: 'CI',
        status: 'PASS',
        url: 'https://example.com/ci',
        pr_count: 2,
        pr_url: 'https://github.com/super-man/awesome/pulls',
      },
    ]);
    expect(String(fetchMock.mock.calls.find((call) => String(call[0]).includes('/pulls'))?.[0])).toContain(
      'state=open',
    );
  });
});
