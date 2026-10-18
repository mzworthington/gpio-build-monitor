import { createMcpHandler } from 'agents/mcp/server';
import { McpServer } from '@modelcontextprotocol/server';
import { z } from 'zod';

import { runAgentTool, parseStatusPayload, type AgentToolName } from './agentTools';

export interface StatusHubEnv {
  STATUS: DurableObjectNamespace;
  PYTHON_API_ORIGIN?: string;
}

const SERVER_NAME = 'build-monitor';
const SERVER_VERSION = '1.0.0';

const repoInput = {
  repo: z.string().describe('Repository as owner/name, for example acme/web'),
};

export function isMcpPath(pathname: string): boolean {
  return pathname === '/mcp' || pathname === '/api/mcp';
}

export function pythonStatusUrl(origin: string): string {
  return new URL('/api/status', origin.replace(/\/$/, '')).toString();
}

export async function readHubStatus(env: StatusHubEnv): Promise<ReturnType<typeof parseStatusPayload>> {
  const origin = env.PYTHON_API_ORIGIN?.trim() ?? '';
  try {
    const response = origin
      ? await fetch(pythonStatusUrl(origin))
      : await env.STATUS.get(env.STATUS.idFromName('monitor')).fetch(new Request('https://monitor/status'));
    if (!response.ok) return null;
    return parseStatusPayload(await response.json());
  } catch {
    return null;
  }
}

function createBuildMonitorServer(env: StatusHubEnv): McpServer {
  const server = new McpServer({ name: SERVER_NAME, version: SERVER_VERSION });
  registerStatusTool(server, env, 'get_build_status', {
    title: 'Build status',
    description:
      'Read aggregated CI status for every repo this monitor watches. Includes retry_after_seconds. Wait that long before calling again. Does not poll GitHub or CircleCI.',
  });
  server.registerTool(
    'get_repo_status',
    {
      title: 'Repo status',
      description:
        'Read workflows, open pull requests, and security findings for one repo (owner/name). retry_after_seconds matches the hub snapshot. Unknown repos return an error and the known repo list.',
      inputSchema: repoInput,
      annotations: { readOnlyHint: true },
    },
    async ({ repo }) => {
      const payload = await readHubStatus(env);
      return runAgentTool(payload, 'get_repo_status', repo);
    },
  );
  registerStatusTool(server, env, 'list_attention', {
    title: 'Attention list',
    description:
      'List failed workflows, in-progress workflows, open pull requests, and security findings, each with a URL. Wait retry_after_seconds before calling again.',
  });
  return server;
}

function registerStatusTool(
  server: McpServer,
  env: StatusHubEnv,
  name: Exclude<AgentToolName, 'get_repo_status'>,
  config: { title: string; description: string },
): void {
  server.registerTool(
    name,
    { ...config, annotations: { readOnlyHint: true } },
    async () => runAgentTool(await readHubStatus(env), name),
  );
}

export function handleBuildMonitorMcp(
  request: Request,
  env: StatusHubEnv,
  ctx: ExecutionContext,
): Promise<Response> {
  const mcpRequest = rewriteApiMcpPath(request);
  return createMcpHandler(() => createBuildMonitorServer(env))(mcpRequest, env, ctx);
}

function rewriteApiMcpPath(request: Request): Request {
  const url = new URL(request.url);
  if (url.pathname !== '/api/mcp') return request;
  url.pathname = '/mcp';
  return new Request(url, request);
}
