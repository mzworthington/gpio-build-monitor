import { aggregate, type AggregateStatus, type BuildDetail, type StatusPayload } from '../ci';

export const SLEEP_RUNNING_SECONDS = 120;
export const SLEEP_ATTENTION_SECONDS = 180;
export const SLEEP_FETCH_ERROR_SECONDS = 300;
export const SLEEP_SETTLED_SECONDS = 900;

export const EINK_MAX_WORKFLOWS = 16;

export function sleepSeconds(status: AggregateStatus, isRunning: boolean): number {
  if (isRunning) return SLEEP_RUNNING_SECONDS;
  if (status === 'FAIL' || status === 'UNKNOWN' || status === 'APPROVAL') {
    return SLEEP_ATTENTION_SECONDS;
  }
  if (status === 'CONNECTION_ERROR') return SLEEP_FETCH_ERROR_SECONDS;
  return SLEEP_SETTLED_SECONDS;
}

export interface RepoGlance {
  repo: string;
  status: string;
  workflow_count: number;
  pr_count: number;
  security_count: number;
  is_running: boolean;
  workflows?: Array<{ workflow: string; status: string }>;
}

function sourceCount(source: { count?: number } | null | undefined): number {
  const numeric = Number(source?.count);
  return Number.isFinite(numeric) ? numeric : 0;
}

export function repoGlances(
  builds: StatusPayload['builds'],
  { includeWorkflows = false }: { includeWorkflows?: boolean } = {},
): RepoGlance[] {
  const byRepo = new Map<string, BuildDetail[]>();
  for (const build of builds) {
    const repo = build.repo || '';
    if (!repo) {
      continue;
    }
    const group = byRepo.get(repo);
    if (group) {
      group.push(build);
    } else {
      byRepo.set(repo, [build]);
    }
  }
  const rows: RepoGlance[] = [];
  for (const [repo, group] of byRepo) {
    const { status, is_running } = aggregate(group);
    const pulls = group.find((build) => build.pull_requests != null)?.pull_requests;
    const security = group.find((build) => build.security != null)?.security;
    const row: RepoGlance = {
      repo,
      status,
      workflow_count: group.length,
      pr_count: sourceCount(pulls),
      security_count: sourceCount(security),
      is_running,
    };
    if (includeWorkflows) {
      row.workflows = [...group]
        .sort((a, b) =>
          (a.workflow || '').localeCompare(b.workflow || '', undefined, { sensitivity: 'base' }),
        )
        .slice(0, EINK_MAX_WORKFLOWS)
        .map((build) => ({ workflow: build.workflow, status: build.status }));
    }
    rows.push(row);
  }
  rows.sort((a, b) => a.repo.localeCompare(b.repo));
  return rows;
}

export function openPrGlances(
  builds: StatusPayload['builds'],
): Array<{ repo: string; pr_count: number; pr_url: string }> {
  const glances: Array<{ repo: string; pr_count: number; pr_url: string }> = [];
  const seen = new Set<string>();
  for (const build of builds) {
    const repo = build.repo || '';
    const pulls = build.pull_requests;
    if (!repo || seen.has(repo) || pulls == null) {
      continue;
    }
    const numeric = Number(pulls.count);
    if (!Number.isFinite(numeric) || numeric <= 0) {
      continue;
    }
    seen.add(repo);
    glances.push({
      repo,
      pr_count: numeric,
      pr_url: pulls.url || `https://github.com/${repo}/pulls`,
    });
  }
  return glances;
}

export function securityGlances(
  builds: StatusPayload['builds'],
): Array<{
  repo: string;
  count: number;
  url: string;
  vulnerabilities: number;
  codeql: number;
}> {
  const glances: Array<{
    repo: string;
    count: number;
    url: string;
    vulnerabilities: number;
    codeql: number;
  }> = [];
  const seen = new Set<string>();
  for (const build of builds) {
    const repo = build.repo || '';
    const security = build.security;
    if (!repo || seen.has(repo) || security == null) {
      continue;
    }
    const numeric = Number(security.count);
    if (!Number.isFinite(numeric)) {
      continue;
    }
    seen.add(repo);
    glances.push({
      repo,
      count: numeric,
      url: security.url || `https://github.com/${repo}/security`,
      vulnerabilities: Number(security.vulnerabilities?.count) || 0,
      codeql: Number(security.codeql?.count) || 0,
    });
  }
  return glances;
}

export function snapshotEtag(payload: StatusPayload): string {
  const body = JSON.stringify({
    builds: payload.builds,
    is_running: payload.is_running,
    open_prs: openPrGlances(payload.builds),
    security: securityGlances(payload.builds),
    status: payload.status,
  });
  const digest = hexSha256(body).slice(0, 16);
  return `W/"${digest}"`;
}

export function einkPayload(payload: StatusPayload): {
  type: 'status';
  fetching: false;
  status: StatusPayload['status'];
  is_running: boolean;
  repos: RepoGlance[];
  sleep_seconds: number;
} {
  const { status, is_running } = aggregate(payload.builds);
  return {
    type: 'status',
    fetching: false,
    status,
    is_running,
    repos: repoGlances(payload.builds, { includeWorkflows: false }),
    sleep_seconds: sleepSeconds(status, is_running),
  };
}

export function einkRepoPayload(payload: StatusPayload, repo: string) {
  const compact = einkPayload(payload);
  compact.repos = repoGlances(payload.builds, { includeWorkflows: true }).filter(
    (row) => row.repo === repo,
  );
  return compact;
}

export interface AgentWorkflowRef {
  repo: string;
  workflow: string;
  status: string;
  url: string;
}

export interface AgentPullRequestRef {
  repo: string;
  number: number;
  title: string;
  url: string;
  draft: boolean;
}

export type AgentSecuritySource = 'vulnerabilities' | 'codeql';

export interface AgentSecurityRef {
  repo: string;
  title: string;
  severity: string | null;
  url: string;
  state: string;
  source: AgentSecuritySource;
}

export interface AgentSnapshot {
  type: 'status';
  status: AggregateStatus;
  is_running: boolean;
  last_checked_at: number | null;
  retry_after_seconds: number;
  repos: RepoGlance[];
}

export interface AgentRepoSnapshot {
  repo: string;
  status: AggregateStatus;
  is_running: boolean;
  last_checked_at: number | null;
  retry_after_seconds: number;
  workflows: Array<{ workflow: string; status: string; url: string }>;
  pull_requests: Array<{ number: number; title: string; url: string; draft: boolean }>;
  security: Array<{
    title: string;
    severity: string | null;
    url: string;
    state: string;
    source: AgentSecuritySource;
  }>;
}

export interface AgentAttention {
  status: AggregateStatus;
  is_running: boolean;
  last_checked_at: number | null;
  retry_after_seconds: number;
  failed: AgentWorkflowRef[];
  running: AgentWorkflowRef[];
  open_prs: AgentPullRequestRef[];
  security: AgentSecurityRef[];
}

interface AgentTiming {
  status: AggregateStatus;
  is_running: boolean;
  last_checked_at: number | null;
  retry_after_seconds: number;
}

const SECURITY_SOURCES = ['vulnerabilities', 'codeql'] as const;
const IN_PROGRESS_STATUS = new Set<string>(['RUNNING', 'WAITING']);

function agentTiming(payload: StatusPayload): AgentTiming {
  const { status, is_running } = aggregate(payload.builds);
  return {
    status,
    is_running,
    last_checked_at: payload.last_checked_at,
    retry_after_seconds: sleepSeconds(status, is_running),
  };
}

export function agentPayload(payload: StatusPayload): AgentSnapshot {
  const timing = agentTiming(payload);
  return {
    type: 'status',
    ...timing,
    repos: repoGlances(payload.builds),
  };
}

function buildsForRepo(payload: StatusPayload, repo: string): BuildDetail[] {
  if (!repo) return [];
  return payload.builds.filter((build) => build.repo === repo);
}

function pullRequestsFor(builds: BuildDetail[]): AgentRepoSnapshot['pull_requests'] {
  for (const build of builds) {
    const pulls = build.pull_requests;
    if (!pulls || !Number.isFinite(Number(pulls.count)) || Number(pulls.count) <= 0) continue;
    return (pulls.items ?? []).map((item) => ({
      number: item.number,
      title: item.title,
      url: item.url,
      draft: item.draft,
    }));
  }
  return [];
}

function securityBucket(
  security: NonNullable<BuildDetail['security']>,
  source: AgentSecuritySource,
): NonNullable<BuildDetail['security']>['vulnerabilities'] {
  switch (source) {
    case 'vulnerabilities':
      return security.vulnerabilities;
    case 'codeql':
      return security.codeql;
    default: {
      const exhaustive: never = source;
      return exhaustive;
    }
  }
}

function securityFor(builds: BuildDetail[]): AgentRepoSnapshot['security'] {
  for (const build of builds) {
    const security = build.security;
    if (!security || !Number.isFinite(Number(security.count))) continue;
    const rows: AgentRepoSnapshot['security'] = [];
    for (const source of SECURITY_SOURCES) {
      const bucket = securityBucket(security, source);
      for (const item of bucket?.items ?? []) {
        rows.push({
          title: item.title,
          severity: item.severity,
          url: item.url,
          state: item.state,
          source,
        });
      }
    }
    return rows;
  }
  return [];
}

export function agentRepoStatus(payload: StatusPayload, repo: string): AgentRepoSnapshot | null {
  const builds = buildsForRepo(payload, repo);
  if (builds.length === 0) return null;
  const timing = agentTiming(payload);
  const { status, is_running } = aggregate(builds);
  return {
    repo,
    status,
    is_running,
    last_checked_at: timing.last_checked_at,
    retry_after_seconds: timing.retry_after_seconds,
    workflows: [...builds]
      .sort((a, b) =>
        (a.workflow || '').localeCompare(b.workflow || '', undefined, { sensitivity: 'base' }),
      )
      .map((build) => ({ workflow: build.workflow, status: build.status, url: build.url })),
    pull_requests: pullRequestsFor(builds),
    security: securityFor(builds),
  };
}

export function agentRepoPayload(payload: StatusPayload, repo: string): AgentRepoSnapshot {
  const found = agentRepoStatus(payload, repo);
  if (found) return found;
  const timing = agentTiming(payload);
  return {
    repo,
    status: 'NONE',
    is_running: false,
    last_checked_at: timing.last_checked_at,
    retry_after_seconds: timing.retry_after_seconds,
    workflows: [],
    pull_requests: [],
    security: [],
  };
}

function workflowRef(build: BuildDetail): AgentWorkflowRef {
  return {
    repo: build.repo,
    workflow: build.workflow,
    status: build.status,
    url: build.url,
  };
}

function byRepoThenWorkflow(a: AgentWorkflowRef, b: AgentWorkflowRef): number {
  const repo = a.repo.localeCompare(b.repo, undefined, { sensitivity: 'base' });
  if (repo !== 0) return repo;
  return a.workflow.localeCompare(b.workflow, undefined, { sensitivity: 'base' });
}

export function agentAttention(payload: StatusPayload): AgentAttention {
  const timing = agentTiming(payload);
  const open_prs: AgentPullRequestRef[] = [];
  const security: AgentSecurityRef[] = [];
  for (const repo of knownRepos(payload)) {
    const builds = buildsForRepo(payload, repo);
    for (const item of pullRequestsFor(builds)) {
      open_prs.push({ repo, ...item });
    }
    for (const item of securityFor(builds)) {
      security.push({ repo, ...item });
    }
  }
  return {
    ...timing,
    failed: payload.builds
      .filter((build) => build.repo && build.status === 'FAIL')
      .map(workflowRef)
      .sort(byRepoThenWorkflow),
    running: payload.builds
      .filter((build) => build.repo && IN_PROGRESS_STATUS.has(build.status))
      .map(workflowRef)
      .sort(byRepoThenWorkflow),
    open_prs,
    security,
  };
}

export function knownRepos(payload: StatusPayload): string[] {
  return [...new Set(payload.builds.map((build) => build.repo).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, undefined, { sensitivity: 'base' }),
  );
}

export function etagMatches(ifNoneMatch: string | null, etag: string): boolean {
  if (!ifNoneMatch) return false;
  const offered = ifNoneMatch.split(',').map((part) => part.trim()).filter(Boolean);
  return offered.includes('*') || offered.includes(etag);
}

export function statusSnapshotResponse(request: Request, payload: StatusPayload): Response {
  const etag = snapshotEtag(payload);
  const seconds = sleepSeconds(payload.status, payload.is_running);
  const headers = {
    'Cache-Control': 'no-store',
    ETag: etag,
    'Retry-After': String(seconds),
  };
  if (etagMatches(request.headers.get('If-None-Match'), etag)) {
    return new Response(null, { status: 304, headers });
  }

  const url = new URL(request.url);
  const body = snapshotBody(snapshotView(url.searchParams.get('view')), payload, url.searchParams.get('repo'));
  return Response.json(body, { headers });
}

type SnapshotView = 'eink' | 'agent' | 'full';

function snapshotView(value: string | null): SnapshotView {
  if (value === 'eink' || value === 'agent') return value;
  return 'full';
}

function snapshotBody(view: SnapshotView, payload: StatusPayload, repo: string | null): unknown {
  switch (view) {
    case 'eink':
      return repo ? einkRepoPayload(payload, repo) : einkPayload(payload);
    case 'agent':
      return repo ? agentRepoPayload(payload, repo) : agentPayload(payload);
    case 'full':
      return { ...payload, sleep_seconds: sleepSeconds(payload.status, payload.is_running) };
    default: {
      const exhaustive: never = view;
      return exhaustive;
    }
  }
}

function hexSha256(value: string): string {
  // FNV-1a 64-bit is enough for a weak ETag of this payload; Workers have
  // crypto.subtle but this helper stays sync for unit tests.
  let hash = 0xcbf29ce484222325n;
  for (const byte of new TextEncoder().encode(value)) {
    hash ^= BigInt(byte);
    hash = (hash * 0x100000001b3n) & 0xffffffffffffffffn;
  }
  return hash.toString(16).padStart(16, '0');
}
