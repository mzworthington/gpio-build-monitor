export type PostHogConfig =
  | { enabled: false }
  | { enabled: true; apiKey: string; apiHost: string };

export type PostHogClient = {
  init: (
    apiKey: string,
    options: {
      api_host?: string;
      ui_host?: string;
      defaults?: string;
      capture_pageview?: string;
      cookieless_mode?: string;
      person_profiles?: string;
      disable_session_recording?: boolean;
    },
  ) => void;
};

export type PostHogHost = {
  fetch: (input: string) => Promise<Response>;
  querySelector: (selector: string) => { src?: string } | null;
  createScript: (src: string) => Promise<void>;
  posthog?: PostHogClient;
};

const POSTHOG_ARRAY = 'https://eu-assets.i.posthog.com/static/array.js';

function browserHost(): PostHogHost {
  const doc = globalThis as unknown as {
    document: {
      querySelector: (selector: string) => { src?: string } | null;
      createElement: (tag: string) => {
        src: string;
        async: boolean;
        onload: (() => void) | null;
        onerror: (() => void) | null;
      };
      head: { appendChild: (node: unknown) => void };
    };
    fetch: (input: string) => Promise<Response>;
    posthog?: PostHogClient;
  };
  return {
    fetch: (input) => doc.fetch(input),
    querySelector: (selector) => doc.document.querySelector(selector),
    createScript: (src) =>
      new Promise((resolve, reject) => {
        const script = doc.document.createElement('script');
        script.src = src;
        script.async = true;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error('PostHog array.js failed to load'));
        doc.document.head.appendChild(script);
      }),
    get posthog() {
      return (globalThis as unknown as { posthog?: PostHogClient }).posthog;
    },
  };
}

async function loadArray(host: PostHogHost): Promise<void> {
  if (host.querySelector(`script[src="${POSTHOG_ARRAY}"]`)) {
    return;
  }
  await host.createScript(POSTHOG_ARRAY);
}

export async function bootPosthog(host: PostHogHost = browserHost()): Promise<void> {
  let cfg: PostHogConfig;
  try {
    const res = await host.fetch('/posthog-config.json');
    if (!res.ok) return;
    cfg = (await res.json()) as PostHogConfig;
  } catch {
    return;
  }
  if (!cfg || cfg.enabled !== true || typeof cfg.apiKey !== 'string' || cfg.apiKey === '') {
    return;
  }
  try {
    await loadArray(host);
  } catch {
    return;
  }
  const posthog = host.posthog;
  if (!posthog || typeof posthog.init !== 'function') return;
  posthog.init(cfg.apiKey, {
    api_host: cfg.apiHost,
    ui_host: 'https://eu.posthog.com',
    defaults: '2026-05-30',
    capture_pageview: 'history_change',
    cookieless_mode: 'always',
    person_profiles: 'never',
    disable_session_recording: true,
  });
}
