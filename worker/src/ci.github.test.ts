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
      },
    ]);
    const runCalls = fetchMock.mock.calls.filter((call) =>
      String(call[0]).includes('/actions/runs'),
    );
    expect(runCalls).toHaveLength(2);
  });
});
