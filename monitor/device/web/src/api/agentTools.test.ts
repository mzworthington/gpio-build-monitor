import { describe, expect, it } from 'vitest';
import type { StatusPayload } from '../ci';
import { parseStatusPayload, runAgentTool } from './agentTools';

const payload: StatusPayload = {
  type: 'status',
  fetching: false,
  status: 'FAIL',
  is_running: false,
  builds: [
    { repo: 'acme/web', workflow: 'CI', status: 'FAIL', url: 'https://example.com/1' },
  ],
  poll_in_seconds: 30,
  last_checked_at: 100,
  next_check_at: 130,
};

describe('runAgentTool', () => {
  it('returns the glance for get_build_status', () => {
    const result = runAgentTool(payload, 'get_build_status');
    expect(result.isError).toBeUndefined();
    expect(result.structuredContent.status).toBe('FAIL');
    expect(JSON.parse(result.content[0].text).repos).toEqual([
      {
        repo: 'acme/web',
        status: 'FAIL',
        workflow_count: 1,
        pr_count: 0,
        security_count: 0,
        is_running: false,
      },
    ]);
  });

  it('errors when the hub has no snapshot', () => {
    const result = runAgentTool(null, 'list_attention');
    expect(result.isError).toBe(true);
    expect(result.structuredContent).toEqual({ error: 'status hub unavailable' });
  });

  it('errors with the known repo list for an unknown repo', () => {
    const result = runAgentTool(payload, 'get_repo_status', 'other/repo');
    expect(result.isError).toBe(true);
    expect(result.structuredContent).toEqual({
      error: 'unknown repo',
      repo: 'other/repo',
      known_repos: ['acme/web'],
    });
  });
});

describe('parseStatusPayload', () => {
  it('accepts a hub snapshot and drops an unknown status', () => {
    expect(parseStatusPayload(payload)?.builds[0]?.workflow).toBe('CI');
    expect(parseStatusPayload({ ...payload, status: 'BROKEN' })).toBeNull();
    expect(parseStatusPayload({ ...payload, builds: [{ repo: 1 }] })).toBeNull();
  });
});
