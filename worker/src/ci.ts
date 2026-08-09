export type CiResult =
  | 'PASS'
  | 'FAIL'
  | 'RUNNING'
  | 'UNKNOWN'
  | 'CONNECTION_ERROR'
  | 'NONE';

export type AggregateStatus =
  | 'PASS'
  | 'FAIL'
  | 'UNKNOWN'
  | 'CONNECTION_ERROR'
  | 'NONE';

export interface BuildDetail {
  repo: string;
  workflow: string;
  status: string;
  url: string;
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

export function aggregate(builds: BuildDetail[]): {
  status: AggregateStatus;
  is_running: boolean;
} {
  const is_running = builds.some((b) => b.status === 'RUNNING');
  const settled = builds.filter((b) => b.status !== 'RUNNING');
  if (settled.length === 0) {
    return { status: 'NONE', is_running };
  }
  if (settled.some((b) => b.status === 'CONNECTION_ERROR')) {
    return { status: 'CONNECTION_ERROR', is_running };
  }
  if (settled.some((b) => b.status === 'FAIL')) {
    return { status: 'FAIL', is_running };
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

/** Collapse Dependabot Update #ID (+ optional package list) to ecosystem/dir. */
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
  if (status === 'completed' && conclusion === 'failure') return 'FAIL';
  if (status === 'completed' && conclusion === 'success') return 'PASS';
  if (conclusion == null && (status === 'queued' || status === 'in_progress')) {
    return 'RUNNING';
  }
  return 'UNKNOWN';
}

function mapCircleStatus(status: string): CiResult {
  switch (status) {
    case 'success':
      return 'PASS';
    case 'failed':
    case 'failing':
      return 'FAIL';
    case 'running':
    case 'on_hold':
    case 'not_run':
      return 'RUNNING';
    default:
      return 'UNKNOWN';
  }
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

  const url = new URL(`https://api.github.com/repos/${repo}/actions/runs`);
  url.searchParams.set('per_page', '100');
  const branch = integration.branch ?? 'main';
  if (branch && branch !== '*') {
    url.searchParams.set('branch', branch);
  }

  const resp = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'gpio-build-monitor-worker',
    },
  });
  if (!resp.ok) {
    return [
      {
        repo,
        workflow: `(github ${resp.status})`,
        status: 'CONNECTION_ERROR',
        url: `https://github.com/${repo}`,
      },
    ];
  }

  const payload = (await resp.json()) as {
    workflow_runs?: Array<{
      id: number;
      name: string;
      html_url: string;
      status: string;
      conclusion: string | null;
      created_at?: string;
      head_branch?: string;
    }>;
  };
  const runs = payload.workflow_runs ?? [];

  const excluded = new Set(integration.excluded_workflows ?? []);
  const patterns = integration.excluded_workflow_patterns ?? [];
  type Run = (typeof runs)[number];
  const latestByKey = new Map<string, Run>();

  for (const run of runs) {
    const name = run.name || '';
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
  }));
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
