import { describe, expect, it, vi } from 'vitest';
import { startPushControls, type PushElement, type PushHost } from './pushControls';

function element(overrides: Partial<PushElement> = {}): PushElement {
  return {
    hidden: false,
    textContent: 'Notify on failure',
    disabled: true,
    dataset: { state: 'off' },
    addEventListener: vi.fn(),
    ...overrides,
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    json: async () => body,
  } as Response;
}

function host(overrides: Partial<PushHost> & { button?: PushElement; root?: PushElement } = {}): {
  host: PushHost;
  root: PushElement;
  button: PushElement;
} {
  const root = overrides.root ?? element({ hidden: true });
  const button = overrides.button ?? element();
  const hint = element({ textContent: '' });
  const { button: _b, root: _r, ...rest } = overrides;
  const pushHost: PushHost = {
    getElementById: (id) => {
      if (id === 'push-controls') return root;
      if (id === 'push-toggle') return button;
      if (id === 'push-hint') return hint;
      return null;
    },
    fetch: vi.fn(async () => jsonResponse({ publicKey: null })),
    serviceWorker: {
      register: vi.fn(async () => ({
        pushManager: {
          getSubscription: async () => null,
          subscribe: vi.fn(),
        },
      })),
      ready: Promise.resolve({
        pushManager: {
          getSubscription: async () => null,
          subscribe: vi.fn(),
        },
      }),
    },
    notificationPermission: 'default',
    requestNotificationPermission: async () => 'granted',
    pushManagerSupported: true,
    ...rest,
  };
  return { host: pushHost, root, button };
}

describe('startPushControls', () => {
  it('keeps the control hidden and unused when VAPID is not configured', async () => {
    const { host: pushHost, root, button } = host();
    await startPushControls(pushHost);
    expect(root.hidden).toBe(true);
    expect(button.disabled).toBe(true);
    expect(button.textContent).toBe('Alerts unavailable');
    expect(button.addEventListener).not.toHaveBeenCalled();
  });

  it('enables alerts and flips the button after a successful subscribe', async () => {
    const subscription = {
      endpoint: 'https://push.example/123',
      toJSON: () => ({ endpoint: 'https://push.example/123', keys: { p256dh: 'a', auth: 'b' } }),
      unsubscribe: async () => true,
    };
    let stored: typeof subscription | null = null;
    const registration = {
      pushManager: {
        getSubscription: async () => stored,
        subscribe: vi.fn(async () => {
          stored = subscription;
          return subscription;
        }),
      },
    };
    const fetch = vi.fn(async (input: string, init?: RequestInit) => {
      if (String(input).includes('vapid-public-key')) {
        return jsonResponse({ publicKey: 'B'.repeat(87) });
      }
      if (String(input).includes('/api/push/subscribe') && init?.method === 'POST') {
        return jsonResponse({ status: 'subscribed' });
      }
      return jsonResponse({ error: 'unexpected' }, 500);
    });
    const { host: pushHost, root, button } = host({
      fetch,
      serviceWorker: {
        register: async () => registration,
        ready: Promise.resolve(registration),
      },
    });
    await startPushControls(pushHost);
    expect(root.hidden).toBe(false);
    expect(button.disabled).toBe(false);
    expect(button.textContent).toBe('Notify on failure');

    const click = vi.mocked(button.addEventListener).mock.calls[0]?.[1];
    expect(click).toBeTypeOf('function');
    await click();
    expect(button.textContent).toBe('Disable failure alerts');
    expect(button.disabled).toBe(false);
    expect(registration.pushManager.subscribe).toHaveBeenCalled();
  });
});
