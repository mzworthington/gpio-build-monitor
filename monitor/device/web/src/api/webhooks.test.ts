import { describe, expect, it } from 'vitest';
import { decideGitHub, handleWebhook } from './webhooks';

describe('decideGitHub', () => {
  it('refreshes on pull_request as well as workflow_run', () => {
    expect(decideGitHub('workflow_run')).toBe('refresh');
    expect(decideGitHub('pull_request')).toBe('refresh');
    expect(decideGitHub('dependabot_alert')).toBe('refresh');
    expect(decideGitHub('code_scanning_alert')).toBe('refresh');
    expect(decideGitHub('ping')).toBe('ack');
    expect(decideGitHub('issues')).toBe('ignore');
  });
});

describe('handleWebhook GitHub', () => {
  it('rejects unsigned pull_request when a secret is configured', async () => {
    const result = await handleWebhook(
      new Request('https://monitor.example/webhooks/github', {
        method: 'POST',
        headers: { 'X-GitHub-Event': 'pull_request' },
        body: '{}',
      }),
      'github',
      { GITHUB_WEBHOOK_SECRET: 's3cret' },
    );
    expect(result.response.status).toBe(403);
    expect(result.decision).toBe('ignore');
  });
});
