/**
 * FinanPy — Service Worker
 *
 * Estratégias:
 *   - HTML autenticado:    NetworkFirst → fallback para /offline/
 *   - Estáticos (CSS/JS):  StaleWhileRevalidate
 *   - Imagens:             CacheFirst com expiração
 *   - Fontes Google:       CacheFirst com longa duração
 *   - APIs GET (snapshot): NetworkFirst com fallback ao cache (5s timeout)
 *   - APIs POST (writes):  Background Sync (Workbox BackgroundSyncPlugin)
 *
 * Mantemos `ignoreURLParametersMatching` para evitar cache duplicado de
 * URLs com `?source=pwa` ou `?source=shortcut`.
 *
 * IMPORTANTE: este arquivo é servido em /static/sw.js mas escopado para "/"
 * via header `Service-Worker-Allowed: /` configurado em core/views.py.
 */

importScripts('https://storage.googleapis.com/workbox-cdn/releases/7.1.0/workbox-sw.js');

if (workbox) {
  workbox.setConfig({ debug: false });

  const { core, precaching, routing, strategies, expiration, backgroundSync, cacheableResponse } = workbox;

  // ---------------------------------------------------------------------------
  // App shell: precache mínimo (offline page + ícones essenciais)
  // ---------------------------------------------------------------------------
  precaching.precacheAndRoute([
    { url: '/offline/', revision: 'v1' },
    { url: '/static/manifest.webmanifest', revision: 'v1' },
    { url: '/static/images/icons/icon-192.png', revision: 'v1' },
    { url: '/static/images/icons/icon-512.png', revision: 'v1' },
  ]);

  // ---------------------------------------------------------------------------
  // 1) Documentos HTML — NetworkFirst com fallback offline
  // Apps autenticados NÃO devem servir HTML cacheado de outro usuário.
  // Por isso usamos NetworkFirst e só recorremos ao cache em falha de rede.
  // ---------------------------------------------------------------------------
  routing.registerRoute(
    ({ request }) => request.mode === 'navigate',
    async (params) => {
      const networkFirst = new strategies.NetworkFirst({
        cacheName: 'finanpy-pages-v1',
        networkTimeoutSeconds: 4,
        plugins: [
          new cacheableResponse.CacheableResponsePlugin({ statuses: [200] }),
          new expiration.ExpirationPlugin({ maxEntries: 30, maxAgeSeconds: 60 * 60 * 24 }),
        ],
      });
      try {
        return await networkFirst.handle(params);
      } catch (err) {
        const cache = await caches.open(workbox.core.cacheNames.precache);
        const offline = await cache.match(precaching.getCacheKeyForURL('/offline/'));
        return offline || Response.error();
      }
    }
  );

  // ---------------------------------------------------------------------------
  // 2) CSS / JS / Web Workers — StaleWhileRevalidate
  // ---------------------------------------------------------------------------
  routing.registerRoute(
    ({ request }) =>
      request.destination === 'style' ||
      request.destination === 'script' ||
      request.destination === 'worker',
    new strategies.StaleWhileRevalidate({
      cacheName: 'finanpy-static-v1',
      plugins: [new cacheableResponse.CacheableResponsePlugin({ statuses: [0, 200] })],
    })
  );

  // ---------------------------------------------------------------------------
  // 3) Imagens locais — CacheFirst (60 dias)
  // ---------------------------------------------------------------------------
  routing.registerRoute(
    ({ request, url }) =>
      request.destination === 'image' && url.origin === self.location.origin,
    new strategies.CacheFirst({
      cacheName: 'finanpy-images-v1',
      plugins: [
        new cacheableResponse.CacheableResponsePlugin({ statuses: [0, 200] }),
        new expiration.ExpirationPlugin({
          maxEntries: 80,
          maxAgeSeconds: 60 * 60 * 24 * 60, // 60 dias
          purgeOnQuotaError: true,
        }),
      ],
    })
  );

  // ---------------------------------------------------------------------------
  // 4) Google Fonts — CacheFirst (1 ano), até migrarmos para self-hosted
  // ---------------------------------------------------------------------------
  routing.registerRoute(
    ({ url }) =>
      url.origin === 'https://fonts.googleapis.com' || url.origin === 'https://fonts.gstatic.com',
    new strategies.CacheFirst({
      cacheName: 'finanpy-fonts-v1',
      plugins: [
        new cacheableResponse.CacheableResponsePlugin({ statuses: [0, 200] }),
        new expiration.ExpirationPlugin({ maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 365 }),
      ],
    })
  );

  // ---------------------------------------------------------------------------
  // 5) APIs GET (read-only) — NetworkFirst com cache leve
  // Permite ler dashboard offline com dados ligeiramente stale.
  // ---------------------------------------------------------------------------
  routing.registerRoute(
    ({ url, request }) => url.pathname.startsWith('/api/') && request.method === 'GET',
    new strategies.NetworkFirst({
      cacheName: 'finanpy-api-v1',
      networkTimeoutSeconds: 5,
      plugins: [
        new cacheableResponse.CacheableResponsePlugin({ statuses: [200] }),
        new expiration.ExpirationPlugin({ maxEntries: 50, maxAgeSeconds: 60 * 60 * 24 }),
      ],
    })
  );

  // ---------------------------------------------------------------------------
  // 6) APIs POST de transações — Background Sync (offline-write)
  // Quando o usuário cria uma transação offline, a request é enfileirada
  // e re-tentada quando a rede volta. Endpoint Hermes: /api/v1/transactions/quick/
  // ---------------------------------------------------------------------------
  const txQueue = new backgroundSync.BackgroundSyncPlugin('finanpy-tx-queue', {
    maxRetentionTime: 60 * 24, // 24 horas em minutos
    onSync: async ({ queue }) => {
      let entry;
      while ((entry = await queue.shiftRequest())) {
        try {
          await fetch(entry.request.clone());
        } catch (error) {
          await queue.unshiftRequest(entry);
          throw error;
        }
      }
      // Notifica clientes ativos de que a fila foi drenada
      const clients = await self.clients.matchAll({ type: 'window' });
      clients.forEach((c) => c.postMessage({ type: 'SYNC_DRAINED', queue: 'finanpy-tx-queue' }));
    },
  });

  routing.registerRoute(
    ({ url, request }) =>
      request.method === 'POST' && url.pathname.startsWith('/api/v1/transactions/'),
    new strategies.NetworkOnly({ plugins: [txQueue] }),
    'POST'
  );

  // ---------------------------------------------------------------------------
  // Skip waiting / claim — ativação imediata em deploys
  // ---------------------------------------------------------------------------
  self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
      self.skipWaiting();
    }
  });

  self.addEventListener('activate', (event) => {
    event.waitUntil(self.clients.claim());
  });
} else {
  // eslint-disable-next-line no-console
  console.error('[FinanPy SW] Workbox não carregou.');
}
