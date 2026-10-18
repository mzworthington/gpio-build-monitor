import { type AggregateStatus, type BuildDetail, type StatusPayload } from '../ci';
import { agentAttention, agentPayload, agentRepoStatus, knownRepos } from './snapshot';

export type AgentToolName = 'get_build_status' | 'get_repo_status' | 'list_attention';

export interface AgentToolResult {
  [key: string]: unknown;
  content: Array<{ type: 'text'; text: string }>;
  structuredContent: Record<string, unknown>;
  isError?: boolean;
}

function jsonResult(value: object, isError = false): AgentToolResult {
  const structuredContent: Record<string, unknown> = {};
  for (const [key, entry] of Object.entries(value)) {
    structuredContent[key] = entry;
  }
  return {
    content: [{ type: 'text', text: JSON.stringify(value) }],
    structuredContent,
    ...(isError ? { isError: true } : {}),
  };
}

export function runAgentTool(
  payload: StatusPayload | null,
  name: AgentToolName,
  repo?: string,
): AgentToolResult {
  if (!payload) {
    return jsonResult({ error: 'status hub unavailable' }, true);
  }
  switch (name) {
    case 'get_build_status':
      return jsonResult(agentPayload(payload));
    case 'get_repo_status':
      return repoStatusResult(payload, repo ?? '');
    case 'list_attention':
      return jsonResult(agentAttention(payload));
    default: {
      const exhaustive: never = name;
      return exhaustive;
    }
  }
}

function repoStatusResult(payload: StatusPayload, repo: string): AgentToolResult {
  const detail = agentRepoStatus(payload, repo);
  if (!detail) {
    return jsonResult({ error: 'unknown repo', repo, known_repos: knownRepos(payload) }, true);
  }
  return jsonResult(detail);
}

export function parseStatusPayload(value: unknown): StatusPayload | null {
  if (typeof value !== 'object' || value === null) return null;
  if (!('type' in value) || value.type !== 'status') return null;
  if (!('builds' in value) || !Array.isArray(value.builds)) return null;
  if (!('status' in value) || typeof value.status !== 'string') return null;
  if (!('is_running' in value) || typeof value.is_running !== 'boolean') return null;
  if (!('fetching' in value) || typeof value.fetching !== 'boolean') return null;
  if (!('poll_in_seconds' in value) || typeof value.poll_in_seconds !== 'number') return null;
  if (!isAggregateStatus(value.status)) return null;
  const lastChecked = 'last_checked_at' in value ? value.last_checked_at : null;
  const nextCheck = 'next_check_at' in value ? value.next_check_at : null;
  if (lastChecked !== null && typeof lastChecked !== 'number') return null;
  if (nextCheck !== null && typeof nextCheck !== 'number') return null;
  const builds = parseBuilds(value.builds);
  if (!builds) return null;
  return {
    type: 'status',
    fetching: value.fetching,
    status: value.status,
    is_running: value.is_running,
    builds,
    poll_in_seconds: value.poll_in_seconds,
    last_checked_at: lastChecked,
    next_check_at: nextCheck,
  };
}

function isAggregateStatus(value: string): value is AggregateStatus {
  switch (value) {
    case 'PASS':
    case 'FAIL':
    case 'APPROVAL':
    case 'UNKNOWN':
    case 'CONNECTION_ERROR':
    case 'NONE':
    case 'RUNNING':
    case 'WAITING':
      return true;
    default:
      return false;
  }
}

function parseBuilds(value: unknown[]): BuildDetail[] | null {
  const builds: BuildDetail[] = [];
  for (const item of value) {
    const build = parseBuild(item);
    if (!build) return null;
    builds.push(build);
  }
  return builds;
}

function parseBuild(value: unknown): BuildDetail | null {
  if (typeof value !== 'object' || value === null) return null;
  if (!('repo' in value) || typeof value.repo !== 'string') return null;
  if (!('workflow' in value) || typeof value.workflow !== 'string') return null;
  if (!('status' in value) || typeof value.status !== 'string') return null;
  if (!('url' in value) || typeof value.url !== 'string') return null;
  const build: BuildDetail = {
    repo: value.repo,
    workflow: value.workflow,
    status: value.status,
    url: value.url,
  };
  if ('pull_requests' in value) {
    if (value.pull_requests === null) build.pull_requests = null;
    else if (isRecord(value.pull_requests)) build.pull_requests = pullRequestsFrom(value.pull_requests);
  }
  if ('security' in value) {
    if (value.security === null) build.security = null;
    else if (isRecord(value.security)) build.security = securityFrom(value.security);
  }
  return build;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function pullRequestsFrom(value: Record<string, unknown>): BuildDetail['pull_requests'] {
  const items = Array.isArray(value.items) ? value.items.flatMap(pullItemFrom) : [];
  return {
    count: typeof value.count === 'number' ? value.count : items.length,
    url: typeof value.url === 'string' ? value.url : '',
    items,
  };
}

function pullItemFrom(value: unknown): NonNullable<BuildDetail['pull_requests']>['items'] {
  if (!isRecord(value)) return [];
  if (typeof value.number !== 'number' || typeof value.title !== 'string' || typeof value.url !== 'string') {
    return [];
  }
  return [{ number: value.number, title: value.title, url: value.url, draft: value.draft === true }];
}

function securityFrom(value: Record<string, unknown>): BuildDetail['security'] {
  const vulnerabilities = securitySourceFrom(value.vulnerabilities);
  const codeql = securitySourceFrom(value.codeql);
  const count = typeof value.count === 'number' ? value.count : vulnerabilities.count + codeql.count;
  return {
    count,
    url: typeof value.url === 'string' ? value.url : '',
    vulnerabilities,
    codeql,
  };
}

function securitySourceFrom(value: unknown): NonNullable<BuildDetail['security']>['vulnerabilities'] {
  if (!isRecord(value)) return { count: 0, url: '', items: [] };
  const items = Array.isArray(value.items) ? value.items.flatMap(securityItemFrom) : [];
  return {
    count: typeof value.count === 'number' ? value.count : items.length,
    url: typeof value.url === 'string' ? value.url : '',
    items,
  };
}

function securityItemFrom(
  value: unknown,
): NonNullable<BuildDetail['security']>['vulnerabilities']['items'] {
  if (!isRecord(value)) return [];
  if (typeof value.number !== 'number' || typeof value.title !== 'string' || typeof value.url !== 'string') {
    return [];
  }
  const state = typeof value.state === 'string' ? value.state : '';
  const severity = typeof value.severity === 'string' || value.severity === null ? value.severity : null;
  return [{ number: value.number, title: value.title, url: value.url, state, severity }];
}
