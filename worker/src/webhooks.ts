export type WebhookDecision = 'refresh' | 'ack' | 'ignore';

export interface EnvSecrets {
  GITHUB_WEBHOOK_SECRET?: string;
  CIRCLE_CI_WEBHOOK_SECRET?: string;
}

function timingSafeEqualHex(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i += 1) {
    out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return out === 0;
}

async function hmacSha256Hex(secret: string, body: ArrayBuffer): Promise<string> {
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  const sig = await crypto.subtle.sign('HMAC', key, body);
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export async function verifyGitHubSignature(
  body: ArrayBuffer,
  secret: string,
  header: string | null,
): Promise<boolean> {
  if (!header || !secret) return false;
  const expected = `sha256=${await hmacSha256Hex(secret, body)}`;
  return timingSafeEqualHex(expected, header);
}

export async function verifyCircleSignature(
  body: ArrayBuffer,
  secret: string,
  header: string | null,
): Promise<boolean> {
  if (!header || !secret) return false;
  const versions: Record<string, string> = {};
  for (const pair of header.split(',')) {
    if (!pair.includes('=')) continue;
    const [version, value] = pair.split('=', 2);
    versions[version.trim()] = value.trim();
  }
  const provided = versions.v1;
  if (!provided) return false;
  const expected = await hmacSha256Hex(secret, body);
  return timingSafeEqualHex(expected, provided);
}

export function decideGitHub(eventName: string | null): WebhookDecision {
  if (!eventName) return 'ignore';
  if (eventName === 'ping') return 'ack';
  if (eventName === 'workflow_run') return 'refresh';
  return 'ignore';
}

export function decideCircle(eventName: string | null): WebhookDecision {
  if (!eventName) return 'ignore';
  if (eventName === 'workflow-completed' || eventName === 'job-completed') {
    return 'refresh';
  }
  return 'ignore';
}

export async function handleWebhook(
  request: Request,
  provider: 'github' | 'circleci',
  secrets: EnvSecrets,
): Promise<{ response: Response; decision: WebhookDecision }> {
  const secret =
    provider === 'github'
      ? secrets.GITHUB_WEBHOOK_SECRET
      : secrets.CIRCLE_CI_WEBHOOK_SECRET;

  const body = await request.arrayBuffer();

  // Signature check is optional: only enforce when a Worker secret is configured.
  if (secret) {
    const ok =
      provider === 'github'
        ? await verifyGitHubSignature(body, secret, request.headers.get('X-Hub-Signature-256'))
        : await verifyCircleSignature(body, secret, request.headers.get('circleci-signature'));

    if (!ok) {
      return {
        decision: 'ignore',
        response: new Response('invalid signature', { status: 403 }),
      };
    }
  }

  const eventName =
    provider === 'github'
      ? request.headers.get('X-GitHub-Event')
      : request.headers.get('circleci-event-type');

  const decision =
    provider === 'github' ? decideGitHub(eventName) : decideCircle(eventName);

  if (decision === 'refresh') {
    return {
      decision,
      response: Response.json({ status: 'accepted', action: 'refresh' }),
    };
  }
  if (decision === 'ack') {
    return {
      decision,
      response: Response.json({ status: 'ok', action: 'ack' }),
    };
  }
  return {
    decision,
    response: Response.json({ status: 'ignored' }),
  };
}
