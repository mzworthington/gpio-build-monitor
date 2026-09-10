import { aggregate, type AggregateStatus, type BuildDetail, type StatusPayload } from './ci';

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
  is_running: boolean;
  workflows?: Array<{ workflow: string; status: string }>;
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
    let display: string = status;
    if (status === 'NONE' && is_running) {
      const waitingOnly =
        group.some((build) => build.status === 'WAITING') &&
        !group.some((build) => build.status === 'RUNNING');
      display = waitingOnly ? 'WAITING' : 'RUNNING';
    }
    const prRaw = group.find((build) => build.pr_count != null)?.pr_count;
    const prCount = Number(prRaw);
    const row: RepoGlance = {
      repo,
      status: display,
      workflow_count: group.length,
      pr_count: Number.isFinite(prCount) ? prCount : 0,
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
    if (!repo || seen.has(repo) || build.pr_count == null) {
      continue;
    }
    const numeric = Number(build.pr_count);
    if (!Number.isFinite(numeric) || numeric <= 0) {
      continue;
    }
    seen.add(repo);
    glances.push({
      repo,
      pr_count: numeric,
      pr_url: build.pr_url || `https://github.com/${repo}/pulls`,
    });
  }
  return glances;
}

export function snapshotEtag(payload: StatusPayload): string {
  const body = JSON.stringify({
    builds: payload.builds,
    is_running: payload.is_running,
    open_prs: openPrGlances(payload.builds),
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
  return {
    type: 'status',
    fetching: false,
    status: payload.status,
    is_running: payload.is_running,
    repos: repoGlances(payload.builds, { includeWorkflows: false }),
    sleep_seconds: sleepSeconds(payload.status, payload.is_running),
  };
}

export function einkRepoPayload(payload: StatusPayload, repo: string) {
  const compact = einkPayload(payload);
  compact.repos = repoGlances(payload.builds, { includeWorkflows: true }).filter(
    (row) => row.repo === repo,
  );
  return compact;
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
  const repo = url.searchParams.get('repo');
  const body =
    url.searchParams.get('view') === 'eink'
      ? repo
        ? einkRepoPayload(payload, repo)
        : einkPayload(payload)
      : { ...payload, sleep_seconds: seconds };
  return Response.json(body, { headers });
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
