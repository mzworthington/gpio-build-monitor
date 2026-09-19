import { describe, expect, it } from 'vitest';
import { HOSTED_MONITOR_ORIGIN } from './apiOrigin';
import { startPushControls, type PushElement, type PushHost } from './pushControls';

function el(init: Partial<PushElement> = {}): PushElement {
  return {
    hidden: true,
    textContent: null,
    disabled: false,
    dataset: {},
    addEventListener() {},
    ...init,
  };
}

describe('startPushControls', () => {
  it('loads the VAPID key from the Worker when the page is a Pages preview', async () => {
    const fetched: string[] = [];
    const root = el();
    const button = el({ hidden: false, textContent: 'Notify on failure' });
    const host: PushHost = {
      getElementById(id) {
        if (id === 'push-controls') return root;
        if (id === 'push-toggle') return button;
        if (id === 'push-hint') return el();
        return null;
      },
      async fetch(input) {
        fetched.push(String(input));
        return Response.json({ publicKey: 'BEjZ4idL7_iKy-2M3TTbEP1BPxBMo_yV5cazF3mGH_Oa9D5x3U_I3Zqv2R7NGl8y8pNf_Jn4X-HObaX95V5VIi8' });
      },
      locationOrigin: 'https://gpio-build-monitor.pages.dev',
      configuredApiOrigin: '',
      pushManagerSupported: true,
      requestNotificationPermission: async () => 'granted',
      serviceWorker: {
        register: async () => ({
          pushManager: {
            getSubscription: async () => null,
            subscribe: async () => ({ endpoint: 'https://fcm.example/x', unsubscribe: async () => true }),
          },
        }),
        ready: Promise.resolve({
          pushManager: {
            getSubscription: async () => null,
            subscribe: async () => ({ endpoint: 'https://fcm.example/x', unsubscribe: async () => true }),
          },
        }),
      },
    };

    await startPushControls(host);
    expect(fetched).toEqual([`${HOSTED_MONITOR_ORIGIN}/api/push/vapid-public-key`]);
    expect(root.hidden).toBe(false);
  });
});
