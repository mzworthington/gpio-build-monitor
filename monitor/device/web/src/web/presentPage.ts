import type {
  BuildDetail,
  PullRequestItem,
  PullRequests,
  SecurityFinding,
  SecurityFindings,
} from '../ci';
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
  pull_requests: PullRequests | null;
  security: SecurityFindings | null;
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
        pull_requests: repoBuilds.find((build) => build.pull_requests != null)?.pull_requests ?? null,
        security: repoBuilds.find((build) => build.security != null)?.security ?? null,
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

export type FindingSource = 'Dependabot' | 'CodeQL';

export type TaggedFinding = SecurityFinding & { source: FindingSource };

export type OpenPullGlance = PullRequestItem & {
  repo: string;
  org: string;
  name: string;
};

export type OpenFindingGlance = TaggedFinding & {
  repo: string;
  org: string;
  name: string;
};

const SEVERITY_RANK = ['critical', 'high', 'medium', 'low'] as const;

export function taggedSecurityItems(security: SecurityFindings | null | undefined): TaggedFinding[] {
  if (!security) {
    return [];
  }
  return [
    ...security.vulnerabilities.items.map((item) => ({ ...item, source: 'Dependabot' as const })),
    ...security.codeql.items.map((item) => ({ ...item, source: 'CodeQL' as const })),
  ];
}

export function normalizeSeverity(severity: string | null | undefined): string {
  const value = String(severity || '').toLowerCase();
  return (SEVERITY_RANK as readonly string[]).includes(value) ? value : 'open';
}

export function severityRank(severity: string | null | undefined): number {
  const index = (SEVERITY_RANK as readonly string[]).indexOf(normalizeSeverity(severity));
  return index >= 0 ? index : SEVERITY_RANK.length;
}

export function worstSeverity(items: Array<{ severity: string | null }>): string | null {
  if (items.length === 0) {
    return null;
  }
  return items.reduce((worst, item) =>
    (severityRank(item.severity) < severityRank(worst) ? normalizeSeverity(item.severity) : worst),
  'open');
}

export function prChipClass(count: number): string {
  return count > 0 ? 'chip chip-pr' : 'chip chip-muted';
}

export function securityChipClass(security: SecurityFindings | null | undefined): string {
  if (!security) {
    return 'chip chip-muted';
  }
  if ((security.count || 0) <= 0) {
    return 'chip chip-find-ok';
  }
  const items = taggedSecurityItems(security);
  const worst = worstSeverity(items);
  if (worst === 'critical' || worst === 'high' || items.length === 0) {
    return 'chip chip-find-hot';
  }
  if (worst === 'medium') {
    return 'chip chip-find-warm';
  }
  return 'chip chip-find-ok';
}

export function pullRowClass(draft: boolean): string {
  return draft ? 'glance-row pr-draft' : 'glance-row';
}

export function findingRowClass(severity: string | null | undefined): string {
  return `glance-row finding-${normalizeSeverity(severity)}`;
}

export function pullCardClass(draft: boolean): string {
  return draft ? 'glance-card pr-draft' : 'glance-card';
}

export function findingCardClass(severity: string | null | undefined): string {
  return `glance-card finding-${normalizeSeverity(severity)}`;
}

export function collectOpenPulls(repos: RepoSummary[]): OpenPullGlance[] {
  const glances: OpenPullGlance[] = [];
  for (const entry of repos) {
    for (const item of entry.pull_requests?.items ?? []) {
      glances.push({ ...item, repo: entry.repo, org: entry.org, name: entry.name });
    }
  }
  return glances.sort((a, b) => {
    if (a.draft !== b.draft) {
      return a.draft ? 1 : -1;
    }
    const repo = a.repo.localeCompare(b.repo);
    if (repo !== 0) {
      return repo;
    }
    return b.number - a.number;
  });
}

export function collectOpenFindings(repos: RepoSummary[]): OpenFindingGlance[] {
  const glances: OpenFindingGlance[] = [];
  for (const entry of repos) {
    for (const item of taggedSecurityItems(entry.security)) {
      glances.push({ ...item, repo: entry.repo, org: entry.org, name: entry.name });
    }
  }
  return glances.sort((a, b) => {
    const rank = severityRank(a.severity) - severityRank(b.severity);
    if (rank !== 0) {
      return rank;
    }
    const repo = a.repo.localeCompare(b.repo);
    if (repo !== 0) {
      return repo;
    }
    return a.title.localeCompare(b.title);
  });
}
