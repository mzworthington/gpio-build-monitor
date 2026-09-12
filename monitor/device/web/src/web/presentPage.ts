import type { BuildDetail } from '../ci';
import { shownStatus } from './shownStatus';

const IN_PROGRESS = new Set(['RUNNING', 'WAITING']);

export type RepoSummary = {
  repo: string;
  org: string;
  name: string;
  status: string;
  workflow_count: number;
  is_running: boolean;
  url: string;
  pr_count: number | null;
  pr_url: string;
  workflows: BuildDetail[];
};

export function splitRepo(repo: string): { org: string; name: string } {
  const value = repo || 'unknown repo';
  const index = value.indexOf('/');
  if (index <= 0 || index === value.length - 1) {
    return { org: '', name: value };
  }
  return {
    org: value.slice(0, index + 1),
    name: value.slice(index + 1),
  };
}

export function summarizeRepos(builds: BuildDetail[] | undefined): RepoSummary[] {
  const byRepo = new Map<string, BuildDetail[]>();
  (builds || []).forEach((build) => {
    const key = build.repo || 'unknown repo';
    const group = byRepo.get(key);
    if (group) {
      group.push(build);
    } else {
      byRepo.set(key, [build]);
    }
  });

  return [...byRepo.entries()]
    .map(([repo, repoBuilds]) => {
      const settled = repoBuilds.filter((build) => !IN_PROGRESS.has(build.status));
      let status = 'NONE';
      if (settled.some((build) => build.status === 'FAIL')) {
        status = 'FAIL';
      } else if (settled.some((build) => build.status === 'CONNECTION_ERROR')) {
        status = 'CONNECTION_ERROR';
      } else if (settled.some((build) => build.status === 'APPROVAL')) {
        status = 'APPROVAL';
      } else if (settled.length && settled.every((build) => build.status === 'PASS')) {
        status = 'PASS';
      } else if (settled.length) {
        status = 'UNKNOWN';
      }
      const is_running = repoBuilds.some((build) => IN_PROGRESS.has(build.status));
      if (status === 'NONE' && is_running) {
        const hasRunning = repoBuilds.some((build) => build.status === 'RUNNING');
        const hasWaiting = repoBuilds.some((build) => build.status === 'WAITING');
        status = !hasRunning && hasWaiting ? 'WAITING' : 'RUNNING';
      }
      const workflows = [...repoBuilds].sort((a, b) =>
        String(a.workflow || '').localeCompare(String(b.workflow || '')),
      );
      const { org, name } = splitRepo(repo);
      return {
        repo,
        org,
        name,
        status,
        workflow_count: repoBuilds.length,
        is_running,
        url: repo.includes('/') ? `https://github.com/${repo}` : '',
        pr_count: repoBuilds.find((build) => build.pr_count != null)?.pr_count ?? null,
        pr_url:
          repoBuilds.find((build) => build.pr_url)?.pr_url ||
          (repo.includes('/') ? `https://github.com/${repo}/pulls` : ''),
        workflows,
      };
    })
    .sort((a, b) => a.repo.localeCompare(b.repo));
}

const ATTENTION = new Set(['FAIL', 'CONNECTION_ERROR', 'APPROVAL', 'UNKNOWN']);

const SUMMARIES: Record<string, string> = {
  PASS: 'All builds passed',
  FAIL: 'At least one build failed',
  UNKNOWN: 'Unresolved build status',
  APPROVAL: 'Waiting for human approval',
  CONNECTION_ERROR: 'Could not reach a CI provider',
  NONE: 'No build results yet',
  RUNNING: 'Build in progress',
  WAITING: 'Waiting for another pipeline',
};

const STATUS_WORDS: Record<string, string> = {
  PASS: 'Passing',
  FAIL: 'Failing',
  UNKNOWN: 'Unknown',
  APPROVAL: 'Approval',
  CONNECTION_ERROR: 'Offline',
  NONE: 'Idle',
  RUNNING: 'Running',
  WAITING: 'Waiting',
};

export type LightMode = 'on' | 'off' | 'pulse';

export type PageChrome = {
  shown: string;
  statusWord: string;
  summary: string;
  fetching: boolean;
  lights: Record<'blue' | 'green' | 'yellow' | 'red' | 'purple', LightMode>;
  issues: BuildDetail[];
};

export function presentChrome(snapshot: {
  status: string;
  is_running: boolean;
  fetching: boolean;
  builds: BuildDetail[];
}): PageChrome {
  const shown = shownStatus(snapshot);
  const awaiting = shown === 'RUNNING' || shown === 'WAITING' || shown === 'APPROVAL';
  let summary =
    shown === 'RUNNING' || shown === 'WAITING' || shown === 'APPROVAL'
      ? SUMMARIES[shown]
      : SUMMARIES[snapshot.status] || SUMMARIES.NONE;
  if (!(shown === 'RUNNING' || shown === 'WAITING' || shown === 'APPROVAL') && snapshot.is_running) {
    summary += ' · build running';
  }
  return {
    shown,
    statusWord: STATUS_WORDS[shown] || STATUS_WORDS.NONE,
    summary,
    fetching: snapshot.fetching,
    lights: {
      blue: snapshot.fetching ? 'on' : 'off',
      green: snapshot.status === 'PASS' && !awaiting ? 'on' : 'off',
      yellow:
        snapshot.is_running || shown === 'WAITING' || shown === 'APPROVAL' ? 'pulse' : 'off',
      red: snapshot.status === 'FAIL' || snapshot.status === 'UNKNOWN' ? 'on' : 'off',
      purple: snapshot.status === 'CONNECTION_ERROR' ? 'on' : 'off',
    },
    issues: snapshot.builds.filter((build) => ATTENTION.has(build.status)),
  };
}
