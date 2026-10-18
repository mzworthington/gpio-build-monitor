import { afterEach, describe, expect, it, vi } from 'vitest';
import type { StatusPayload } from '../ci';
import { handleBuildMonitorMcp, isMcpPath, pythonStatusUrl, readHubStatus, type StatusHubEnv } from './mcp';

const payload: StatusPayload = {
  type: 'status',
  fetching: false,
  status: 'PASS',
  is_running: false,
  builds: [],
  poll_in_seconds: 30,
  last_checked_at: 10,
  next_check_at: 40,
};

function hubEnv(origin = '', snapshot: StatusPayload = payload): StatusHubEnv {
  return {
    PYTHON_API_ORIGIN: origin,
    STATUS: {
      idFromName: () => 'monitor-id',
      get: () => ({
        fetch: async () => Response.json(snapshot),
      }),
    } as unknown as StatusHubEnv['STATUS'],
  };
}

describe('isMcpPath', () => {
  it('accepts the public mcp paths and rejects the status snapshot', () => {
    expect(isMcpPath('/mcp')).toBe(true);
    expect(isMcpPath('/api/mcp')).toBe(true);
    expect(isMcpPath('/api/status')).toBe(false);
    expect(isMcpPath('/mcp/')).toBe(false);
  });
});

describe('readHubStatus', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('reads the durable object when no python origin is configured', async () => {
    const status = await readHubStatus(hubEnv(''));
    expect(status?.status).toBe('PASS');
  });

  it('reads the python hub when PYTHON_API_ORIGIN is set', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: string) => {
        expect(input).toBe('http://127.0.0.1:8080/api/status');
        return Response.json(payload);
      }),
    );
    const status = await readHubStatus(hubEnv('http://127.0.0.1:8080/'));
    expect(status?.last_checked_at).toBe(10);
    expect(pythonStatusUrl('http://127.0.0.1:8080/')).toBe('http://127.0.0.1:8080/api/status');
  });

  it('returns null when the hub responds with an error', async () => {
    const env = hubEnv();
    env.STATUS = {
      idFromName: () => 'monitor-id',
      get: () => ({
        fetch: async () => new Response('no', { status: 503 }),
      }),
    } as unknown as StatusHubEnv['STATUS'];
    expect(await readHubStatus(env)).toBeNull();
  });
});

describe('handleBuildMonitorMcp', () => {
  it('lists the read-only tools and returns a glance', async () => {
    const env = hubEnv('', {
      ...payload,
      builds: [
        { repo: 'acme/web', workflow: 'CI', status: 'PASS', url: 'https://example.com/1' },
      ],
    });
    const ctx = {
      waitUntil() {},
      passThroughOnException() {},
    } as unknown as ExecutionContext;
    const initialize = await handleBuildMonitorMcp(mcpRequest('initialize', 1, {
      protocolVersion: '2025-06-18',
      capabilities: {},
      clientInfo: { name: 'test', version: '0' },
    }), env, ctx);
    expect(initialize.status).toBe(200);
    const listed = await handleBuildMonitorMcp(
      mcpRequest('tools/list', 2, {}),
      env,
      ctx,
    );
    const listBody = await readMcpBody(listed);
    const names = toolNames(listBody);
    expect(names).toEqual(['get_build_status', 'get_repo_status', 'list_attention']);

    const called = await handleBuildMonitorMcp(
      mcpRequest('tools/call', 3, { name: 'get_build_status', arguments: {} }),
      env,
      ctx,
    );
    const callBody = await readMcpBody(called);
    const text = callBody.result?.content?.[0]?.text;
    expect(typeof text).toBe('string');
    expect(JSON.parse(String(text)).status).toBe('PASS');
  });
});

function mcpRequest(method: string, id: number, params: object): Request {
  return new Request('https://monitor.example/api/mcp', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      accept: 'application/json, text/event-stream',
    },
    body: JSON.stringify({ jsonrpc: '2.0', id, method, params }),
  });
}

async function readMcpBody(response: Response): Promise<{
  result?: { tools?: Array<{ name: string }>; content?: Array<{ text?: string }> };
}> {
  const text = await response.text();
  const jsonLine = text
    .split('\n')
    .map((line) => line.trim())
    .find((line) => line.startsWith('{') || line.startsWith('data: {'));
  const raw = jsonLine?.startsWith('data:') ? jsonLine.slice(5).trim() : jsonLine;
  return JSON.parse(raw ?? text) as {
    result?: { tools?: Array<{ name: string }>; content?: Array<{ text?: string }> };
  };
}

function toolNames(body: { result?: { tools?: Array<{ name: string }> } }): string[] {
  return (body.result?.tools ?? []).map((tool) => tool.name);
}
