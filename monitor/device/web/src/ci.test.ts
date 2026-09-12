import { describe, expect, it } from 'vitest';
import { aggregate, keepLastValidPayload } from './ci';

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
});
