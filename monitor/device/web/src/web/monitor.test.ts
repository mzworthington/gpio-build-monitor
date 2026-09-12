import { describe, expect, it, vi } from 'vitest';
import { registerMonitor } from './monitor';

describe('registerMonitor', () => {
  it('registers the monitor factory on Alpine.data', () => {
    const alpine = { data: vi.fn() };
    registerMonitor(alpine);
    expect(alpine.data).toHaveBeenCalledWith('monitor', expect.any(Function));
  });

  it('factory shown status matches the snapshot roll-up', () => {
    const alpine = { data: vi.fn() };
    registerMonitor(alpine);
    const factory = alpine.data.mock.calls[0]?.[1] as () => {
      applySnapshot: (snapshot: {
        status: string;
        is_running: boolean;
        fetching: boolean;
        builds: Array<{ status: string }>;
      }) => { shown: string };
    };
    const page = factory();
    expect(
      page.applySnapshot({
        status: 'FAIL',
        is_running: true,
        fetching: false,
        builds: [{ status: 'FAIL' }, { status: 'RUNNING' }],
      }).shown,
    ).toBe('FAIL');
  });

  it('presents watched repos from the snapshot builds', () => {
    const alpine = { data: vi.fn() };
    registerMonitor(alpine);
    const factory = alpine.data.mock.calls[0]?.[1] as () => {
      repos: Array<{ repo: string; status: string }>;
      applySnapshot: (snapshot: {
        status: string;
        is_running: boolean;
        fetching: boolean;
        builds: Array<{ repo: string; workflow: string; status: string; url: string }>;
      }) => { repos: Array<{ repo: string; status: string }> };
    };
    const page = factory();
    expect(
      page.applySnapshot({
        status: 'FAIL',
        is_running: true,
        fetching: false,
        builds: [
          { repo: 'acme/web', workflow: 'CI', status: 'FAIL', url: 'https://example.com/ci' },
        ],
      }).repos,
    ).toEqual([expect.objectContaining({ repo: 'acme/web', status: 'FAIL' })]);
  });

  it('keeps watched repos collapsed until the operator opens one', () => {
    const alpine = { data: vi.fn() };
    registerMonitor(alpine);
    const factory = alpine.data.mock.calls[0]?.[1] as () => {
      repoIsOpen: (repo: string) => boolean;
      rememberRepo: (repo: string, open: boolean) => void;
      applySnapshot: (snapshot: {
        status: string;
        is_running: boolean;
        fetching: boolean;
        builds: Array<{ repo: string; workflow: string; status: string; url: string }>;
      }) => unknown;
    };
    const page = factory();
    page.applySnapshot({
      status: 'PASS',
      is_running: false,
      fetching: false,
      builds: [
        { repo: 'mzworthington/archlens', workflow: 'CI', status: 'PASS', url: 'https://example.com/ci' },
      ],
    });
    expect(page.repoIsOpen('mzworthington/archlens')).toBe(false);
  });
});
