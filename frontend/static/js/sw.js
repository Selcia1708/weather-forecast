/* ══════════════════════════════════════════════════════════════════
   sw.js – Service Worker for PWA offline support
   (place this in /static/js/sw.js so it can be served at root scope
    via a Nginx alias: location /sw.js { alias /static/js/sw.js; })
══════════════════════════════════════════════════════════════════ */
const CACHE_NAME = 'weathersense-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/theme.css',
  '/static/js/app.js',
  '/static/js/map.js',
  '/static/js/charts.js',
  '/static/js/realtime.js',
  '/static/manifest.json',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js',
];

// Install – cache static shell
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME)
          .then(c => c.addAll(STATIC_ASSETS))
          .then(() => self.skipWaiting())
  );
});

// Activate – clean up old caches
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Fetch – network-first for API, cache-first for static
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // API calls: network first, then nothing (no cache for live data)
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(
      fetch(e.request).catch(() => new Response(
        JSON.stringify({ error: 'offline' }),
        { headers: { 'Content-Type': 'application/json' } }
      ))
    );
    return;
  }

  // Static assets: cache first
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(resp => {
        if (resp && resp.status === 200) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
        }
        return resp;
      });
    })
  );
});