import { describe, expect, it } from 'vitest';
import { DEFAULT_POSTHOG_HOST, resolvePublicPostHogConfig } from './posthogConfig';

describe('resolvePublicPostHogConfig', () => {
  it('disables capture when the token is missing', () => {
    expect(resolvePublicPostHogConfig({})).toEqual({ enabled: false });
  });

  it('returns the reverse-proxy host by default', () => {
    expect(resolvePublicPostHogConfig({ POSTHOG_TOKEN: ' phc_test ' })).toEqual({
      enabled: true,
      apiKey: 'phc_test',
      apiHost: DEFAULT_POSTHOG_HOST,
    });
  });

  it('honours POSTHOG_HOST when set', () => {
    expect(
      resolvePublicPostHogConfig({
        POSTHOG_TOKEN: 'phc_test',
        POSTHOG_HOST: ' https://eu.i.posthog.com ',
      }),
    ).toEqual({
      enabled: true,
      apiKey: 'phc_test',
      apiHost: 'https://eu.i.posthog.com',
    });
  });
});
