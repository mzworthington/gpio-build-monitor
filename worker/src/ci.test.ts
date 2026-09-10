import { describe, expect, it } from 'vitest';
import { aggregate } from './ci';

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
