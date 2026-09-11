import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchAllBuilds, githubPollDelaySeconds, resetGithubPublicClient } from './ci';

const PASSING_RUN = {
  id: 1,
  workflow_id: 1001,
  name: 'CI',
  html_url: 'https://example.com/ci',
  created_at: '2020-01-02T00:00:00Z',
  status: 'completed',
  conclusion: 'success',
  head_branch: 'main',
};

const SINGLE_REPO = {
  poll_in_seconds: 60,
  integrations: [{ type: 'GITHUB' as const, username: 'super-man', repo: 'awesome' }],
};

function stubGithubFetch(
  onRequest: (url: string, authed: boolean) => Response,
): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn(async (input: string | URL, init?: RequestInit) => {
    const url = String(input);
    const authed = new Headers(init?.headers).has('Authorization');
    if (url.includes('/actions/workflows')) {
      return Response.json({ workflows: [{ id: 1001, state: 'active' }] });
    }
    return onRequest(url, authed);
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

function rateLimited(headers: HeadersInit = {}): Response {
  return Response.json(
    { message: 'API rate limit exceeded' },
    { status: 403, headers },
  );
}

function forbidden(): Response {
  return Response.json({ message: 'Resource not accessible' }, { status: 403 });
}

function passingRuns(): Response {
  return Response.json({ workflow_runs: [PASSING_RUN] });
}

async function pollGithub(
  integrations = SINGLE_REPO.integrations,
): Promise<Awaited<ReturnType<typeof fetchAllBuilds>>> {
  return fetchAllBuilds({ poll_in_seconds: 60, integrations }, { githubToken: 'secret' });
}

afterEach(() => {
  resetGithubPublicClient();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('fetchAllBuilds GitHub', () => {
  it('retries actions/runs without credentials after an authenticated 403', async () => {
    const fetchMock = stubGithubFetch((url, authed) => {
      if (url.includes('/actions/runs')) {
        return authed ? rateLimited() : passingRuns();
      }
      return new Response('not found', { status: 404 });
    });

    const builds = await pollGithub();

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
    expect(
      fetchMock.mock.calls.filter((call) => String(call[0]).includes('/actions/runs')),
    ).toHaveLength(2);
    expect(githubPollDelaySeconds(60)).toBeGreaterThanOrEqual(20 * 60);
  });

  it('keeps the configured poll cadence when authenticated GitHub calls succeed', async () => {
    stubGithubFetch((url) =>
      url.includes('/actions/runs') ? passingRuns() : Response.json([]),
    );

    await pollGithub();

    expect(githubPollDelaySeconds(60)).toBe(60);
  });

  it.each([
    { label: 'no reset header', resetInSeconds: undefined, minDelay: 20 * 60 },
    { label: 'reset in 5 minutes', resetInSeconds: 5 * 60, minDelay: 20 * 60 },
    { label: 'reset in 60 minutes', resetInSeconds: 3600, minDelay: 3500 },
  ])(
    'backs off the next poll after a public fallback ($label)',
    async ({ resetInSeconds, minDelay }) => {
      stubGithubFetch((url, authed) => {
        if (!url.includes('/actions/runs')) return Response.json([]);
        if (authed) return forbidden();
        const headers: Record<string, string> = { 'X-RateLimit-Remaining': '0' };
        if (resetInSeconds != null) {
          headers['X-RateLimit-Reset'] = String(
            Math.floor(Date.now() / 1000) + resetInSeconds,
          );
        }
        return rateLimited(headers);
      });

      await pollGithub();

      expect(githubPollDelaySeconds(60)).toBeGreaterThanOrEqual(minDelay);
    },
  );

  it('skips further unauthenticated GitHub GETs after a public rate-limit 403', async () => {
    const fetchMock = stubGithubFetch((url, authed) => {
      if (url.includes('/actions/runs')) {
        if (authed) return forbidden();
        return rateLimited({
          'X-RateLimit-Remaining': '0',
          'X-RateLimit-Reset': String(Math.floor(Date.now() / 1000) + 3600),
        });
      }
      return Response.json([]);
    });

    await pollGithub([
      { type: 'GITHUB', username: 'super-man', repo: 'awesome' },
      { type: 'GITHUB', username: 'super-man', repo: 'second' },
    ]);

    const publicRunCalls = fetchMock.mock.calls.filter((call) => {
      const url = String(call[0]);
      const headers = new Headers(call[1]?.headers);
      return url.includes('/actions/runs') && !headers.has('Authorization');
    });
    expect(publicRunCalls).toHaveLength(1);
  });

  it('counts open pull requests including drafts without changing CI status', async () => {
    const fetchMock = stubGithubFetch((url) => {
      if (url.includes('/actions/runs')) return passingRuns();
      if (url.includes('/pulls')) {
        return Response.json([{ number: 1, draft: false }, { number: 2, draft: true }]);
      }
      return new Response('not found', { status: 404 });
    });

    const builds = await pollGithub();

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
    expect(
      String(fetchMock.mock.calls.find((call) => String(call[0]).includes('/pulls'))?.[0]),
    ).toContain('state=open');
  });
});
