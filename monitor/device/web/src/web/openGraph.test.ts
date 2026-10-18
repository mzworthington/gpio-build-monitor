import { describe, expect, it } from 'vitest';
import { stampOpenGraph } from './openGraph';

const TAGLINE = 'CI you notice without looking for it - on the web or glowing on your desk.';

const html = `<meta name="viewport" content="width=device-width, initial-scale=1">
<meta
    name="description"
    content="${TAGLINE}"
  >
<meta
    property="og:description"
    content="${TAGLINE}"
  >
  <meta
    name="twitter:description"
    content="${TAGLINE}"
  >`;

describe('stampOpenGraph', () => {
  it('writes the open pull and finding counts into the Open Graph description', () => {
    const pulls = {
      count: 18,
      url: 'https://github.com/acme/web/pulls',
      items: Array.from({ length: 18 }, (_, index) => ({
        number: index + 1,
        title: `PR ${index + 1}`,
        url: `https://github.com/acme/web/pull/${index + 1}`,
        draft: false,
      })),
    };
    const findings = Array.from({ length: 17 }, (_, index) => ({
      number: index + 1,
      title: `Finding ${index + 1}`,
      url: `https://github.com/acme/web/security/${index + 1}`,
      severity: 'high',
      state: 'open',
    }));
    const security = {
      count: 17,
      url: 'https://github.com/acme/web/security',
      vulnerabilities: {
        count: 17,
        url: 'https://github.com/acme/web/security/dependabot',
        items: findings,
      },
      codeql: { count: 0, url: 'https://github.com/acme/web/security/codeql', items: [] },
    };
    const workflow = {
      repo: 'acme/web',
      status: 'PASS',
      url: 'https://example.com/ci',
      pull_requests: pulls,
      security,
    };

    const stamped = stampOpenGraph(html, [
      { ...workflow, workflow: 'CI' },
      { ...workflow, workflow: 'Deploy' },
    ]);

    expect(stamped).toContain('content="18 PRs and 17 findings. ' + TAGLINE + '"');
    expect(stamped.match(/18 PRs and 17 findings/g)).toHaveLength(3);
    expect(stamped).toContain('content="width=device-width, initial-scale=1"');
  });
});
