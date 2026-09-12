export const DEFAULT_POSTHOG_HOST = 'https://a.mzworthington.co.uk';

export type PostHogWorkerEnv = {
  POSTHOG_TOKEN?: string;
  POSTHOG_HOST?: string;
};

export type PublicPostHogConfig =
  | { enabled: false }
  | { enabled: true; apiKey: string; apiHost: string };

export function resolvePublicPostHogConfig(env: PostHogWorkerEnv): PublicPostHogConfig {
  const apiKey = env.POSTHOG_TOKEN?.trim() ?? '';
  if (apiKey === '') {
    return { enabled: false };
  }
  const apiHost = env.POSTHOG_HOST?.trim() || DEFAULT_POSTHOG_HOST;
  return { enabled: true, apiKey, apiHost };
}

export function posthogConfigResponse(env: PostHogWorkerEnv): Response {
  return Response.json(resolvePublicPostHogConfig(env), {
    headers: { 'Cache-Control': 'no-store' },
  });
}
