// Service Worker - minimal cache dla offline read
const CACHE = 'maile-v1';
const ASSETS = ['/', '/index.html', '/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
});

self.addEventListener('fetch', e => {
  // API calls always go to network (real-time)
  if (e.request.url.includes('execute-api')) return;

  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
