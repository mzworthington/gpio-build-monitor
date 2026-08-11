(() => {
  const root = document.getElementById('push-controls');
  const button = document.getElementById('push-toggle');
  const hint = document.getElementById('push-hint');
  if (!root || !button) return;

  const supported =
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window;

  function setHint(text) {
    if (hint) hint.textContent = text || '';
  }

  function setButton(label, enabled) {
    button.textContent = label;
    button.disabled = !enabled;
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = atob(base64);
    const output = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i += 1) {
      output[i] = raw.charCodeAt(i);
    }
    return output;
  }

  async function fetchPublicKey() {
    const res = await fetch('/api/push/vapid-public-key');
    if (res.status === 503) return null;
    if (!res.ok) throw new Error('vapid key unavailable');
    const data = await res.json();
    if (!data || typeof data.publicKey !== 'string') throw new Error('invalid vapid response');
    return data.publicKey;
  }

  async function currentSubscription(reg) {
    return reg.pushManager.getSubscription();
  }

  async function refreshUi(reg) {
    const sub = await currentSubscription(reg);
    if (Notification.permission === 'denied') {
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

  async function enable(reg) {
    const permission = await Notification.requestPermission();
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
    const res = await fetch('/api/push/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sub.toJSON()),
    });
    if (!res.ok) throw new Error('subscribe failed');
    await refreshUi(reg);
  }

  async function disable(reg) {
    const sub = await currentSubscription(reg);
    if (!sub) {
      await refreshUi(reg);
      return;
    }
    try {
      await fetch('/api/push/subscribe', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ endpoint: sub.endpoint }),
      });
    } catch (_err) {
      // Still unsubscribe locally.
    }
    await sub.unsubscribe();
    await refreshUi(reg);
  }

  async function init() {
    if (!supported) {
      root.hidden = true;
      return;
    }

    let publicKey;
    try {
      publicKey = await fetchPublicKey();
    } catch (_err) {
      root.hidden = true;
      return;
    }
    if (!publicKey) {
      // Hosted Worker without VAPID (or local Pi UI): hide controls.
      root.hidden = true;
      return;
    }

    root.hidden = false;
    const reg = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
    await navigator.serviceWorker.ready;
    await refreshUi(reg);

    button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        if (button.dataset.state === 'on') {
          await disable(reg);
        } else {
          await enable(reg);
        }
      } catch (_err) {
        setHint('Could not update notification subscription.');
        await refreshUi(reg);
      }
    });
  }

  init().catch(() => {
    root.hidden = true;
  });
})();
