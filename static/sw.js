// Service Worker GRID-Chat v4 Unificado
const CACHE_NAME = 'grid-chat-v4-unified';
const urlsToCache = [
  '/',
  '/static/css/style.css',
  '/static/manifest.json',
  '/static/img/logo.ico',
  '/static/img/logo.svg',
  '/static/img/logo-web-app-manifest-512x512.png'
];

// Evento de instalación: cachea recursos y se activa inmediatamente
self.addEventListener('install', event => {
  console.log('[Service Worker] Instalando GRID-Chat v4...');
  
  // Forzar activación inmediata
  self.skipWaiting();
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[Service Worker] Cacheando recursos esenciales');
        return cache.addAll(urlsToCache);
      })
      .catch(error => {
        console.error('[Service Worker] Error al cachear recursos:', error);
      })
  );
});

// Evento de activación: limpia cachés antiguas y reclama control
self.addEventListener('activate', event => {
  console.log('[Service Worker] Activando GRID-Chat v4...');
  
  event.waitUntil(
    Promise.all([
      // Limpiar cachés antiguas
      caches.keys().then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            if (cacheName !== CACHE_NAME) {
              console.log('[Service Worker] Eliminando caché antigua:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      }),
      // Reclamar control de clientes inmediatamente
      self.clients.claim()
    ])
  );
  
  console.log('[Service Worker] Listo para controlar clientes');
});

// Evento fetch: estrategia Network First, fallback a Cache
self.addEventListener('fetch', event => {
  const { request } = event;
  
  // Ignorar peticiones a Socket.io
  if (request.url.includes('/socket.io/')) {
    return;
  }
  
  // Para solicitudes de navegación (páginas), usar Network First
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .catch(() => caches.match('/'))
    );
    return;
  }
  
  // Para recursos estáticos, usar Cache First con actualización en red
  if (request.url.includes('/static/')) {
    event.respondWith(
      caches.match(request)
        .then(response => {
          // Si encontramos en caché, responder con eso
          if (response) {
            // Actualizar caché en segundo plano
            fetch(request).then(networkResponse => {
              caches.open(CACHE_NAME).then(cache => {
                cache.put(request, networkResponse);
              });
            }).catch(() => {});
            return response;
          }
          
          // Si no está en caché, buscar en red
          return fetch(request)
            .then(networkResponse => {
              // Guardar en caché para futuras solicitudes
              const responseClone = networkResponse.clone();
              caches.open(CACHE_NAME)
                .then(cache => cache.put(request, responseClone));
              return networkResponse;
            })
            .catch(() => {
              // Si falla la red, intentar con recursos genéricos
              if (request.url.includes('.css')) {
                return caches.match('/static/css/style.css');
              }
              return null;
            });
        })
    );
    return;
  }
  
  // Para otras peticiones, usar Network First
  event.respondWith(
    fetch(request)
      .catch(() => caches.match(request))
  );
});

// Manejo de mensajes desde la aplicación principal
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});