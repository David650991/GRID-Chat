// Service Worker Básico - Estrategia: Network First (Red primero, si falla, usa caché)
const CACHE_NAME = 'chat-3v-v1';
const urlsToCache = [
  '/',
  '/static/css/style.css',
  '/static/manifest.json'
];

// Instalación: Guardamos archivos críticos
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Cache abierta');
        return cache.addAll(urlsToCache);
      })
  );
});

// Activación: Limpiamos cachés viejas
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Intercepción de peticiones (Fetch)
self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request)
      .catch(() => {
        // Si no hay internet, intentamos servir desde la caché
        return caches.match(event.request);
      })
  );
});