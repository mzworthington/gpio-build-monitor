import { pushApiOrigin, pushSubscribeUrl, pushVapidUrl } from './apiOrigin';

export type PushElement = {
  hidden: boolean;
  textContent: string | null;
  disabled?: boolean;
  dataset: Record<string, string | undefined>;
  addEventListener: (type: string, listener: () => void) => void;
};

type PushJson = {
  endpoint?: string;
  toJSON?: () => unknown;
};

type PushRegistration = {
  pushManager: {
    getSubscription: () => Promise<(PushJson & { unsubscribe: () => Promise<boolean> }) | null>;
    subscribe: (options: {
      userVisibleOnly: boolean;
      applicationServerKey: Uint8Array;
    }) => Promise<PushJson & { unsubscribe: () => Promise<boolean> }>;
  };
};

type NotificationPermissionState = 'granted' | 'denied' | 'default';

export type PushHost = {
  getElementById: (id: string) => PushElement | null;
  fetch: (input: string, init?: RequestInit) => Promise<Response>;
  serviceWorker?: {
    register: (url: string, options: { scope: string }) => Promise<PushRegistration>;
    ready: Promise<PushRegistration>;
  };
  notificationPermission?: NotificationPermissionState;
  requestNotificationPermission?: () => Promise<NotificationPermissionState>;
  pushManagerSupported?: boolean;
  locationOrigin?: string;
  configuredApiOrigin?: string;
};

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) {
    output[i] = raw.charCodeAt(i);
  }
  return output;
}

function browserPushHost(): PushHost {
  const win = globalThis as unknown as {
    document: {
      getElementById: (id: string) => PushElement | null;
      querySelector?: (selector: string) => { getAttribute?: (name: string) => string | null } | null;
    };
    location?: { origin?: string };
    fetch: PushHost['fetch'];
    navigator: { serviceWorker?: PushHost['serviceWorker'] };
    Notification?: {
      permission: NotificationPermissionState;
      requestPermission: () => Promise<NotificationPermissionState>;
    };
    PushManager?: unknown;
  };
  const meta = win.document.querySelector?.('meta[name="monitor-api-origin"]');
  return {
    getElementById: (id) => win.document.getElementById(id),
    fetch: win.fetch.bind(win),
    serviceWorker: win.navigator.serviceWorker,
    notificationPermission: win.Notification?.permission,
    requestNotificationPermission: () =>
      win.Notification?.requestPermission() ?? Promise.resolve('denied'),
    pushManagerSupported: 'PushManager' in win,
    locationOrigin: win.location?.origin,
    configuredApiOrigin: meta?.getAttribute?.('content') || '',
  };
}

export function startPushControls(host: PushHost = browserPushHost()): Promise<void> {
  const rootEl = host.getElementById('push-controls');
  const buttonEl = host.getElementById('push-toggle');
  const hint = host.getElementById('push-hint');
  if (!rootEl || !buttonEl) return Promise.resolve();
  const root = rootEl;
  const button = buttonEl;

  const supported = Boolean(
    host.serviceWorker && host.pushManagerSupported && host.requestNotificationPermission,
  );
  const apiOrigin = pushApiOrigin(host.configuredApiOrigin, host.locationOrigin ?? '');
  const vapidUrl = pushVapidUrl(apiOrigin);
  const subscribeUrl = pushSubscribeUrl(apiOrigin);

  function setHint(text: string): void {
    if (hint) hint.textContent = text || '';
  }

  function setButton(label: string, enabled: boolean): void {
    button.textContent = label;
    if (button.disabled !== undefined) button.disabled = !enabled;
  }

  async function fetchPublicKey(): Promise<string | null> {
    const res = await host.fetch(vapidUrl);
    if (!res.ok) throw new Error('vapid key unavailable');
    const data: unknown = await res.json();
    if (
      !data ||
      typeof data !== 'object' ||
      typeof (data as { publicKey?: unknown }).publicKey !== 'string'
    ) {
      return null;
    }
    return (data as { publicKey: string }).publicKey;
  }

  async function refreshUi(reg: PushRegistration): Promise<void> {
    const sub = await reg.pushManager.getSubscription();
    if (host.notificationPermission === 'denied') {
      setButton('Notifications blocked', false);
      setHint('Enable notifications for this site in browser settings.');
      return;
    }
    if (sub) {
      setButton('Disable failure alerts', true);
      setHint('Alerts when status turns red, and again when everything is green.');
      button.dataset.state = 'on';
      return;
    }
    setButton('Notify on failure', true);
    setHint('Chrome desktop or Android. Alerts on fail and recovery.');
    button.dataset.state = 'off';
  }

  async function enable(reg: PushRegistration): Promise<void> {
    const permission = (await host.requestNotificationPermission?.()) ?? 'denied';
    host.notificationPermission = permission;
    if (permission !== 'granted') {
      setHint('Permission not granted.');
      await refreshUi(reg);
      return;
    }
    const publicKey = await fetchPublicKey();
    if (!publicKey) {
      setButton('Alerts unavailable', false);
      setHint('Push is not configured on the server yet.');
      return;
    }
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    });
    const res = await host.fetch(subscribeUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sub.toJSON?.() ?? sub),
    });
    if (!res.ok) throw new Error('subscribe failed');
    await refreshUi(reg);
  }

  async function disable(reg: PushRegistration): Promise<void> {
    const sub = await reg.pushManager.getSubscription();
    if (!sub) {
      await refreshUi(reg);
      return;
    }
    try {
      await host.fetch(subscribeUrl, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ endpoint: sub.endpoint }),
      });
    } catch {
      // Best-effort server unsubscribe.
    }
    await sub.unsubscribe();
    await refreshUi(reg);
  }

  async function init(): Promise<void> {
    if (!supported || !host.serviceWorker) {
      root.hidden = true;
      return;
    }

    let publicKey: string | null;
    try {
      publicKey = await fetchPublicKey();
    } catch {
      root.hidden = true;
      return;
    }
    if (!publicKey) {
      root.hidden = true;
      return;
    }

    root.hidden = false;
    const reg = await host.serviceWorker.register('/sw.js', { scope: '/' });
    await host.serviceWorker.ready;
    await refreshUi(reg);

    button.addEventListener('click', () => {
      void (async () => {
        if (button.disabled !== undefined) button.disabled = true;
        try {
          if (button.dataset.state === 'on') {
            await disable(reg);
          } else {
            await enable(reg);
          }
        } catch {
          setHint('Could not update notification subscription.');
          await refreshUi(reg);
        }
      })();
    });
  }

  return init().catch(() => {
    root.hidden = true;
  });
}
