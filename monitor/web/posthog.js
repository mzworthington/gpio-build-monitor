(() => {
  const POSTHOG_ARRAY = 'https://eu-assets.i.posthog.com/static/array.js';

  function loadArray() {
    return new Promise((resolve, reject) => {
      const existing = document.querySelector(`script[src="${POSTHOG_ARRAY}"]`);
      if (existing) {
        resolve(undefined);
        return;
      }
      const script = document.createElement('script');
      script.src = POSTHOG_ARRAY;
      script.async = true;
      script.onload = () => resolve(undefined);
      script.onerror = () => reject(new Error('PostHog array.js failed to load'));
      document.head.appendChild(script);
    });
  }

  async function boot() {
    let cfg;
    try {
      const res = await fetch('/posthog-config.json');
      if (!res.ok) return;
      cfg = await res.json();
    } catch {
      return;
    }
    if (!cfg || cfg.enabled !== true || typeof cfg.apiKey !== 'string' || cfg.apiKey === '') {
      return;
    }
    try {
      await loadArray();
    } catch {
      return;
    }
    const posthog = window.posthog;
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

  void boot();
})();
