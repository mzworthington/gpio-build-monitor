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

  it('labels pull requests from the nested count', () => {
    const alpine = { data: vi.fn() };
    registerMonitor(alpine);
    const factory = alpine.data.mock.calls[0]?.[1] as () => {
      prLabel: (entry: {
        pull_requests: { count: number; url: string; items: unknown[] } | null;
      }) => string;
      prItems: (entry: {
        pull_requests: { count: number; url: string; items: Array<{ number: number }> } | null;
      }) => Array<{ number: number }>;
      prChipClass: (entry: { pull_requests: { count: number } | null }) => string;
    };
    const page = factory();
    const entry = {
      pull_requests: {
        count: 1,
        url: 'https://github.com/acme/web/pulls',
        items: [{ number: 12 }],
      },
    };
    expect(page.prLabel(entry)).toBe('1 PR');
    expect(page.prItems(entry)).toEqual([{ number: 12 }]);
    expect(page.prChipClass(entry)).toBe('chip chip-pr');
  });

  it('builds an Open board from pull and finding items', () => {
    const alpine = { data: vi.fn() };
    registerMonitor(alpine);
    const factory = alpine.data.mock.calls[0]?.[1] as () => {
      openCount: () => number;
      openPulls: () => Array<{ title: string }>;
      openFindings: () => Array<{ source: string; title: string }>;
      applySnapshot: (snapshot: {
        status: string;
        is_running: boolean;
        fetching: boolean;
        builds: Array<{
          repo: string;
          workflow: string;
          status: string;
          url: string;
          pull_requests?: {
            count: number;
            url: string;
            items: Array<{ number: number; title: string; url: string; draft: boolean }>;
          };
          security?: {
            count: number;
            url: string;
            vulnerabilities: {
              count: number;
              url: string;
              items: Array<{
                number: number;
                title: string;
                severity: string;
                url: string;
                state: string;
              }>;
            };
            codeql: { count: number; url: string; items: [] };
          };
        }>;
      }) => unknown;
    };
    const page = factory();
    page.applySnapshot({
      status: 'PASS',
      is_running: false,
      fetching: false,
      builds: [
        {
          repo: 'acme/web',
          workflow: 'CI',
          status: 'PASS',
          url: 'https://example.com/ci',
          pull_requests: {
            count: 1,
            url: 'https://github.com/acme/web/pulls',
            items: [
              { number: 12, title: 'Ready', url: 'https://github.com/acme/web/pull/12', draft: false },
            ],
          },
          security: {
            count: 1,
            url: 'https://github.com/acme/web/security',
            vulnerabilities: {
              count: 1,
              url: 'https://github.com/acme/web/security/dependabot',
              items: [
                {
                  number: 8,
                  title: 'Prototype pollution',
                  severity: 'high',
                  url: 'https://github.com/acme/web/security/dependabot/8',
                  state: 'open',
                },
              ],
            },
            codeql: { count: 0, url: 'https://github.com/acme/web/security/code-scanning', items: [] },
          },
        },
      ],
    });
    expect(page.openCount()).toBe(2);
    expect(page.openPulls().map((item) => item.title)).toEqual(['Ready']);
    expect(page.openFindings().map((item) => item.source)).toEqual(['Dependabot']);
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
