export type CiResult =
  | 'PASS'
  | 'FAIL'
  | 'RUNNING'
  | 'WAITING'
  | 'APPROVAL'
  | 'UNKNOWN'
  | 'CONNECTION_ERROR'
  | 'NONE';

export type AggregateStatus =
  | 'PASS'
  | 'FAIL'
  | 'APPROVAL'
  | 'UNKNOWN'
  | 'CONNECTION_ERROR'
  | 'NONE'
  | 'RUNNING'
  | 'WAITING';

const IN_PROGRESS = new Set<string>(['RUNNING', 'WAITING']);

export interface SecurityFinding {
  number: number;
  title: string;
  severity: string | null;
  url: string;
  state: string;
}

export interface SecuritySource {
  count: number;
  url: string;
  items: SecurityFinding[];
}

export interface SecurityFindings {
  count: number;
  url: string;
  vulnerabilities: SecuritySource;
  codeql: SecuritySource;
}

export interface PullRequestItem {
  number: number;
  title: string;
  url: string;
  draft: boolean;
}

export interface PullRequests {
  count: number;
  url: string;
  items: PullRequestItem[];
}

export interface BuildDetail {
  repo: string;
  workflow: string;
  status: string;
  url: string;
  pull_requests?: PullRequests | null;
  security?: SecurityFindings | null;
}

export interface StatusPayload {
  type: 'status';
  fetching: boolean;
  status: AggregateStatus;
  is_running: boolean;
  builds: BuildDetail[];
  poll_in_seconds: number;
  last_checked_at: number | null;
  next_check_at: number | null;
}

export interface IntegrationConfig {
  type: 'GITHUB' | 'CIRCLECI';
  username: string;
  repo: string;
  branch?: string;
  excluded_workflows?: string[];
  excluded_workflow_patterns?: string[];
}

export interface MonitorConfig {
  poll_in_seconds: number;
  integrations: IntegrationConfig[];
}

export function emptyPayload(pollInSeconds: number): StatusPayload {
  return {
    type: 'status',
    fetching: false,
    status: 'NONE',
    is_running: false,
    builds: [],
    poll_in_seconds: pollInSeconds,
    last_checked_at: null,
    next_check_at: null,
  };
}

function fetchErrorOnly(builds: BuildDetail[]): boolean {
  return builds.length > 0 && builds.every((build) => build.status === 'CONNECTION_ERROR');
}

function buildsByRepo(builds: BuildDetail[]): Map<string, BuildDetail[]> {
  const byRepo = new Map<string, BuildDetail[]>();
  for (const build of builds) {
    const group = byRepo.get(build.repo);
    if (group) {
      group.push(build);
    } else {
      byRepo.set(build.repo, [build]);
    }
  }
  return byRepo;
}

export function keepLastValidPayload(
  previous: StatusPayload | undefined,
  next: StatusPayload,
): StatusPayload {
  if (!previous || previous.builds.length === 0) {
    return next;
  }
  if (next.builds.length === 0) {
    return {
      ...previous,
      fetching: next.fetching,
      last_checked_at: next.last_checked_at,
      next_check_at: next.next_check_at,
      poll_in_seconds: next.poll_in_seconds,
    };
  }
  const previousByRepo = buildsByRepo(previous.builds);
  const nextByRepo = buildsByRepo(next.builds);
  const builds: BuildDetail[] = [];
  const repos = new Set([...previousByRepo.keys(), ...nextByRepo.keys()]);
  for (const repo of [...repos].sort()) {
    const incoming = nextByRepo.get(repo);
    const remembered = previousByRepo.get(repo);
    if (incoming && fetchErrorOnly(incoming) && remembered && !fetchErrorOnly(remembered)) {
      builds.push(...remembered);
    } else if (incoming) {
      builds.push(...incoming);
    }
  }
  const { status, is_running } = aggregate(builds);
  return { ...next, status, is_running, builds };
}

export function aggregate(builds: BuildDetail[]): {
  status: AggregateStatus;
  is_running: boolean;
} {
  // Priority: FAIL > fetch error > approval > all PASS.
  // RUNNING/WAITING elevate the dial via is_running + build statuses.
  const is_running = builds.some((b) => IN_PROGRESS.has(b.status));
  const settled = builds.filter((b) => !IN_PROGRESS.has(b.status));
  if (settled.length === 0) {
    if (!is_running) {
      return { status: 'NONE', is_running };
    }
    const waitingOnly =
      builds.some((build) => build.status === 'WAITING') &&
      !builds.some((build) => build.status === 'RUNNING');
    return { status: waitingOnly ? 'WAITING' : 'RUNNING', is_running };
  }
  if (settled.some((b) => b.status === 'FAIL')) {
    return { status: 'FAIL', is_running };
  }
  if (settled.some((b) => b.status === 'CONNECTION_ERROR')) {
    return { status: 'CONNECTION_ERROR', is_running };
  }
  if (settled.some((b) => b.status === 'APPROVAL')) {
    return { status: 'APPROVAL', is_running };
  }
  if (settled.every((b) => b.status === 'PASS')) {
    return { status: 'PASS', is_running };
  }
  return { status: 'UNKNOWN', is_running };
}

function matchGlob(name: string, pattern: string): boolean {
  // Minimal fnmatch-style: * and ? only.
  const escaped = pattern
    .replace(/[.+^${}()|[\]\\]/g, '\\$&')
    .replace(/\*/g, '.*')
    .replace(/\?/g, '.');
  return new RegExp(`^${escaped}$`).test(name);
}

/** Dependabot version-check display names (`… - Update #N`). */
const DEPENDABOT_UPDATE_KEY =
  /^(?<head>.+?)(?: for .+?)? - Update #\d+$/;

export function workflowIdentityKey(name: string): string {
  const match = DEPENDABOT_UPDATE_KEY.exec(name || '');
  return match?.groups?.head ?? name ?? '';
}

function mapGithubConclusion(run: {
  status: string;
  conclusion: string | null;
}): CiResult {
  const { status, conclusion } = run;
  if (conclusion == null) {
    if (status === 'in_progress') return 'RUNNING';
    if (status === 'waiting' || status === 'queued' || status === 'pending') {
      return 'WAITING';
    }
    return 'UNKNOWN';
  }
  if (status !== 'completed') return 'UNKNOWN';
  if (
    conclusion === 'failure' ||
    conclusion === 'timed_out' ||
    conclusion === 'startup_failure'
  ) {
    return 'FAIL';
  }
  if (conclusion === 'success') return 'PASS';
  if (conclusion === 'action_required') return 'APPROVAL';
  // cancelled / skipped / neutral / stale — ignore for the desk board
  if (
    conclusion === 'cancelled' ||
    conclusion === 'skipped' ||
    conclusion === 'neutral' ||
    conclusion === 'stale'
  ) {
    return 'PASS';
  }
  return 'UNKNOWN';
}

function mapCircleStatus(status: string): CiResult {
  switch (status) {
    case 'success':
      return 'PASS';
    case 'failed':
    case 'error':
      return 'FAIL';
    case 'running':
    case 'failing':
      return 'RUNNING';
    case 'on_hold':
      return 'APPROVAL';
    case 'canceled':
    case 'cancelled':
    case 'not_run':
    case 'unauthorized':
      return 'PASS';
    default:
      return 'UNKNOWN';
  }
}

function githubPublicHeaders(): HeadersInit {
  return {
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'User-Agent': 'gpio-build-monitor-worker',
  };
}

function githubHeaders(token: string): HeadersInit {
  return {
    ...githubPublicHeaders(),
    Authorization: `Bearer ${token}`,
  };
}

let githubPublicLock: Promise<void> = Promise.resolve();
let githubSkipPublicUntilMs = 0;

export function resetGithubPublicClient(): void {
  githubPublicLock = Promise.resolve();
  githubSkipPublicUntilMs = 0;
}

export function githubPollDelaySeconds(configured: number): number {
  const wait = Math.ceil((githubSkipPublicUntilMs - Date.now()) / 1000);
  if (wait <= 0) return configured;
  return Math.max(configured, wait);
}

async function githubGet(url: URL, token: string): Promise<Response> {
  const authed = await fetch(url, { headers: githubHeaders(token) });
  if (authed.ok || (authed.status !== 401 && authed.status !== 403)) {
    return authed;
  }

  const queued = githubPublicLock.then(async () => {
    if (Date.now() < githubSkipPublicUntilMs) {
      return authed;
    }
    const pub = await fetch(url, { headers: githubPublicHeaders() });
    if (pub.status === 403 && pub.headers.get('X-RateLimit-Remaining') === '0') {
      const reset = Number(pub.headers.get('X-RateLimit-Reset'));
      githubSkipPublicUntilMs =
        Number.isFinite(reset) && reset > 0 ? reset * 1000 : Date.now() + 60_000;
    }
    return pub;
  });
  githubPublicLock = queued.then(
    () => undefined,
    () => undefined,
  );
  return queued;
}

/** Workflow IDs that still have YAML and are enabled (state=active). */
async function fetchActiveGithubWorkflowIds(
  repo: string,
  token: string,
): Promise<Set<number> | null> {
  const url = new URL(
    `https://api.github.com/repos/${repo}/actions/workflows`,
  );
  url.searchParams.set('per_page', '100');
  const resp = await githubGet(url, token);
  if (!resp.ok) {
    return null;
  }
  const payload = (await resp.json()) as {
    workflows?: Array<{ id: number; state?: string }>;
  };
  return new Set(
    (payload.workflows ?? [])
      .filter((workflow) => workflow.state === 'active')
      .map((workflow) => workflow.id),
  );
}

async function fetchGithub(
  integration: IntegrationConfig,
  token: string | undefined,
): Promise<BuildDetail[]> {
  const repo = `${integration.username}/${integration.repo}`;
  if (!token) {
    return [
      {
        repo,
        workflow: '(missing GITHUB_TOKEN)',
        status: 'CONNECTION_ERROR',
        url: `https://github.com/${repo}`,
      },
    ];
  }

  const activeIds = await fetchActiveGithubWorkflowIds(repo, token);
  if (activeIds == null) {
    return [
      {
        repo,
        workflow: '(github workflows)',
        status: 'CONNECTION_ERROR',
        url: `https://github.com/${repo}`,
      },
    ];
  }

  const url = new URL(`https://api.github.com/repos/${repo}/actions/runs`);
  url.searchParams.set('per_page', '100');
  const branch = integration.branch ?? 'main';
  if (branch && branch !== '*') {
    url.searchParams.set('branch', branch);
  }

  const [resp, pullGlance, security] = await Promise.all([
    githubGet(url, token),
    fetchGithubOpenPulls(repo, token),
    fetchGithubSecurity(repo, token),
  ]);
  if (!resp.ok) {
    return [
      {
        repo,
        workflow: `(github ${resp.status})`,
        status: 'CONNECTION_ERROR',
        url: `https://github.com/${repo}`,
        pull_requests: pullGlance,
        security,
      },
    ];
  }

  const payload = (await resp.json()) as {
    workflow_runs?: Array<{
      id: number;
      workflow_id?: number;
      name: string;
      html_url: string;
      status: string;
      conclusion: string | null;
      created_at?: string;
      head_branch?: string;
    }>;
  };
  // Drop runs for deleted/disabled workflows (YAML gone or not runnable).
  const runs = (payload.workflow_runs ?? []).filter(
    (run) => run.workflow_id != null && activeIds.has(run.workflow_id),
  );

  const excluded = new Set(integration.excluded_workflows ?? []);
  const patterns = integration.excluded_workflow_patterns ?? [];
  type Run = (typeof runs)[number];
  const latestByKey = new Map<string, Run>();

  for (const run of runs) {
    const name = run.name || '';
    if (DEPENDABOT_UPDATE_KEY.test(name)) continue;
    if (excluded.has(name)) continue;
    if (patterns.some((p) => matchGlob(name, p))) continue;
    if (branch && branch !== '*' && run.head_branch && run.head_branch !== branch) {
      continue;
    }
    const key = workflowIdentityKey(name);
    const existing = latestByKey.get(key);
    if (
      !existing ||
      (run.created_at || '') > (existing.created_at || '')
    ) {
      latestByKey.set(key, run);
    }
  }

  return [...latestByKey.values()].map((run) => ({
    repo,
    workflow: run.name,
    status: mapGithubConclusion(run),
    url: run.html_url,
    pull_requests: pullGlance,
    security,
  }));
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}

function nestedRecord(parent: Record<string, unknown>, key: string): Record<string, unknown> {
  return asRecord(parent[key]) ?? {};
}

function mapItems<T>(payload: unknown[], mapper: (row: unknown) => T | null): T[] {
  const items: T[] = [];
  for (const row of payload) {
    const mapped = mapper(row);
    if (mapped !== null) {
      items.push(mapped);
    }
  }
  return items;
}

export function mapPullRequest(pull: unknown): PullRequestItem | null {
  const row = asRecord(pull);
  if (!row || typeof row.number !== 'number') {
    return null;
  }
  return {
    number: row.number,
    title: String(row.title || `Pull request #${row.number}`),
    url: String(row.html_url || ''),
    draft: Boolean(row.draft),
  };
}

export function mapDependabotAlert(alert: unknown): SecurityFinding | null {
  const row = asRecord(alert);
  if (!row || typeof row.number !== 'number') {
    return null;
  }
  const advisory = nestedRecord(row, 'security_advisory');
  const vuln = nestedRecord(row, 'security_vulnerability');
  const pkg = nestedRecord(nestedRecord(row, 'dependency'), 'package');
  const title = advisory.summary || pkg.name || `Dependabot alert #${row.number}`;
  const severity = vuln.severity || advisory.severity;
  return {
    number: row.number,
    title: String(title),
    severity: severity ? String(severity) : null,
    url: String(row.html_url || ''),
    state: String(row.state || 'open'),
  };
}

export function mapCodeqlAlert(alert: unknown): SecurityFinding | null {
  const row = asRecord(alert);
  if (!row || typeof row.number !== 'number') {
    return null;
  }
  const rule = nestedRecord(row, 'rule');
  const title = rule.description || rule.id || `CodeQL alert #${row.number}`;
  const severity = rule.security_severity_level || rule.severity;
  return {
    number: row.number,
    title: String(title),
    severity: severity ? String(severity) : null,
    url: String(row.html_url || ''),
    state: String(row.state || 'open'),
  };
}

export function githubPullRequests(repo: string, items: PullRequestItem[]): PullRequests {
  return {
    count: items.length,
    url: `https://github.com/${repo}/pulls`,
    items,
  };
}

async function fetchGithubOpenPulls(
  repo: string,
  token: string,
): Promise<PullRequests | null> {
  try {
    const rows = await listOpenGithubPages(
      `https://api.github.com/repos/${repo}/pulls`,
      (url) => githubGet(url, token),
      {},
      { emptyOn404: false },
    );
    if (rows == null) {
      return null;
    }
    return githubPullRequests(repo, mapItems(rows, mapPullRequest));
  } catch {
    return null;
  }
}

export function githubSecurityFindings(
  repo: string,
  vulnerabilities: SecurityFinding[],
  codeql: SecurityFinding[],
): SecurityFindings {
  const url = `https://github.com/${repo}/security`;
  return {
    count: vulnerabilities.length + codeql.length,
    url,
    vulnerabilities: {
      count: vulnerabilities.length,
      url: `${url}/dependabot`,
      items: vulnerabilities,
    },
    codeql: { count: codeql.length, url: `${url}/code-scanning`, items: codeql },
  };
}

function linkRelNext(linkHeader: string | null): string | null {
  if (!linkHeader) return null;
  const match = /<([^>]+)>\s*;\s*rel="next"/i.exec(linkHeader);
  return match?.[1] ?? null;
}

async function listOpenGithubPages(
  startUrl: string,
  get: (url: URL) => Promise<Response>,
  extra: Record<string, string> = {},
  { emptyOn404 }: { emptyOn404: boolean },
): Promise<unknown[] | null> {
  const first = new URL(startUrl);
  first.searchParams.set('state', 'open');
  first.searchParams.set('per_page', '100');
  for (const [key, value] of Object.entries(extra)) {
    first.searchParams.set(key, value);
  }

  let nextUrl: string | null = first.toString();
  const collected: unknown[] = [];
  let pages = 0;
  while (nextUrl && pages < 10) {
    const resp = await get(new URL(nextUrl));
    if (resp.status === 404) {
      return pages === 0 ? (emptyOn404 ? [] : null) : collected;
    }
    if (!resp.ok) {
      return pages === 0 ? null : collected;
    }
    const payload = (await resp.json()) as unknown;
    if (!Array.isArray(payload)) {
      return pages === 0 ? null : collected;
    }
    collected.push(...payload);
    nextUrl = linkRelNext(resp.headers.get('Link'));
    pages += 1;
  }
  return collected;
}

async function fetchGithubSecurity(
  repo: string,
  token: string,
): Promise<SecurityFindings | null> {
  const base = `https://api.github.com/repos/${repo}`;
  const get = (url: URL) => fetch(url, { headers: githubHeaders(token) });
  try {
    const [vulnerabilities, codeql] = await Promise.all([
      listOpenGithubPages(`${base}/dependabot/alerts`, get, {}, { emptyOn404: true }),
      listOpenGithubPages(
        `${base}/code-scanning/alerts`,
        get,
        { tool_name: 'CodeQL' },
        { emptyOn404: true },
      ),
    ]);
    if (vulnerabilities == null && codeql == null) {
      return null;
    }
    return githubSecurityFindings(
      repo,
      mapItems(vulnerabilities ?? [], mapDependabotAlert),
      mapItems(codeql ?? [], mapCodeqlAlert),
    );
  } catch {
    return null;
  }
}

async function fetchCircle(
  integration: IntegrationConfig,
  token: string | undefined,
): Promise<BuildDetail[]> {
  const repo = `${integration.username}/${integration.repo}`;
  const vcsUrl = `https://github.com/${repo}`;
  if (!token) {
    return [
      {
        repo,
        workflow: '(fetch)',
        status: 'CONNECTION_ERROR',
        url: '',
      },
    ];
  }

  const slug = `gh/${integration.username}/${integration.repo}`;
  const pipelinesUrl = `https://circleci.com/api/v2/project/${slug}/pipeline`;
  const headers = {
    'Circle-Token': token,
    Accept: 'application/json',
  };

  const pipelinesResp = await fetch(pipelinesUrl, { headers });
  if (!pipelinesResp.ok) {
    return [
      {
        repo,
        workflow: '(fetch)',
        status: 'CONNECTION_ERROR',
        url: '',
      },
    ];
  }

  const pipelines = ((await pipelinesResp.json()) as { items?: Array<{ id: string }> })
    .items ?? [];
  const excluded = new Set(integration.excluded_workflows ?? []);
  const workflowsByName = new Map<
    string,
    { name: string; id: string; status: string; created_at: string }
  >();

  for (const pipeline of pipelines.slice(0, 10)) {
    const workflowsUrl = `https://circleci.com/api/v2/pipeline/${pipeline.id}/workflow`;
    const workflowResp = await fetch(workflowsUrl, { headers });
    if (!workflowResp.ok) {
      return [
        {
          repo,
          workflow: '(fetch)',
          status: 'CONNECTION_ERROR',
          url: '',
        },
      ];
    }
    const items =
      ((await workflowResp.json()) as {
        items?: Array<{
          name: string;
          id: string;
          status: string;
          created_at: string;
        }>;
      }).items ?? [];

    for (const workflow of items) {
      if (excluded.has(workflow.name)) continue;
      const existing = workflowsByName.get(workflow.name);
      if (!existing || workflow.created_at > existing.created_at) {
        workflowsByName.set(workflow.name, workflow);
      }
    }
  }

  return [...workflowsByName.values()]
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((workflow) => ({
      repo,
      workflow: workflow.name,
      status: mapCircleStatus(workflow.status),
      url: vcsUrl,
      pull_requests: null,
      security: null,
    }));
}

export async function fetchAllBuilds(
  config: MonitorConfig,
  secrets: { githubToken?: string; circleToken?: string },
): Promise<BuildDetail[]> {
  const chunks = await Promise.all(
    config.integrations.map(async (integration) => {
      try {
        if (integration.type === 'GITHUB') {
          return await fetchGithub(integration, secrets.githubToken);
        }
        if (integration.type === 'CIRCLECI') {
          return await fetchCircle(integration, secrets.circleToken);
        }
        return [
          {
            repo: `${integration.username}/${integration.repo}`,
            workflow: '(fetch)',
            status: 'CONNECTION_ERROR',
            url: '',
          },
        ] satisfies BuildDetail[];
      } catch {
        return [
          {
            repo: `${integration.username}/${integration.repo}`,
            workflow: '(fetch)',
            status: 'CONNECTION_ERROR',
            url: '',
          },
        ] satisfies BuildDetail[];
      }
    }),
  );
  return chunks.flat();
}

export function parseMonitorConfig(raw: string | undefined): MonitorConfig {
  if (!raw?.trim()) {
    return { poll_in_seconds: 30, integrations: [] };
  }
  const parsed = JSON.parse(raw) as Partial<MonitorConfig>;
  const poll = Number(parsed.poll_in_seconds ?? 30);
  const integrations = (Array.isArray(parsed.integrations) ? parsed.integrations : [])
    .filter((item) => {
      if (!item || typeof item !== 'object') return false;
      const username = String(item.username ?? '').trim();
      const repo = String(item.repo ?? '').trim();
      if (!username || !repo) return false;
      // Ignore template placeholders from monitor.config.example.json
      if (username.startsWith('your-') || repo.startsWith('your-')) return false;
      return item.type === 'GITHUB' || item.type === 'CIRCLECI';
    });
  return {
    poll_in_seconds: Number.isFinite(poll) && poll > 0 ? poll : 30,
    integrations,
  };
}
