/* Build monitor — push notifications (Chrome desktop / Android). */
self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
  let title = 'Build monitor';
  let body = 'At least one build failed';
  let url = '/';

  try {
    const raw = event.data ? event.data.text() : '';
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object') {
        if (typeof parsed.title === 'string' && parsed.title) title = parsed.title;
        if (typeof parsed.body === 'string' && parsed.body) body = parsed.body;
        if (typeof parsed.url === 'string' && parsed.url) url = parsed.url;
      } else if (raw) {
        body = raw;
      }
    }
  } catch (_err) {
    // Fall through to defaults.
  }

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: '/icon-192.png',
      badge: '/favicon-32.png',
      data: { url },
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target =
    event.notification.data && typeof event.notification.data.url === 'string'
      ? event.notification.data.url
      : '/';

  event.waitUntil(
    (async () => {
      const all = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
      for (const client of all) {
        if ('focus' in client) {
          await client.focus();
          if ('navigate' in client && target) {
            try {
              await client.navigate(target);
            } catch (_err) {
              // Older clients may not support navigate.
            }
          }
          return;
        }
      }
      if (self.clients.openWindow) {
        await self.clients.openWindow(target);
      }
    })(),
  );
});
