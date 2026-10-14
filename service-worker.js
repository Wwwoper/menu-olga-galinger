// Офлайн-режим. Стратегия: сначала сеть (свежие данные), при сбое или медленном
// соединении (> 4 с) — копия из кэша. При установке кэшируются оболочка и ВСЕ дни.
// Меняете этот файл или список SHELL? Увеличьте VERSION.
// На localhost (локальная разработка) кэш отключён: файлы всегда берутся с сервера.
const VERSION = 'v2';
const CACHE = `food-flow-${VERSION}`;
const NETWORK_TIMEOUT_MS = 4000;
const DEV = ['localhost', '127.0.0.1', '[::1]'].includes(self.location.hostname);

const SHELL = [
  './',
  'index.html',
  'manifest.json',
  'shared/css/main.css',
  'shared/css/search.css',
  'shared/js/app.js',
  'shared/js/features.js',
  'shared/js/render.js',
  'shared/js/search.js',
  'shared/js/shell.js',
  'shared/js/state.js',
  'shared/js/store.js',
  'content/meta.json',
  'content/days.json',
  'icons/icon-192.png',
  'icons/icon-512.png',
  'icons/apple-touch-icon.png',
];

self.addEventListener('install', (event) => {
  if (DEV) { self.skipWaiting(); return; }
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await Promise.allSettled(SHELL.map((url) => cache.add(new Request(url, { cache: 'reload' }))));
    try {
      const res = await fetch('content/days.json', { cache: 'reload' });
      const index = await res.json();
      await Promise.allSettled(index.days.map((d) => cache.add(new Request(`content/${d.file}`, { cache: 'reload' }))));
    } catch (err) {
      // нет сети при установке: остальное закэшируется при обычном использовании
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    // на localhost чистим все кэши; в проде — только старые версии
    await Promise.all(keys.filter((k) => DEV || (k.startsWith('food-flow-') && k !== CACHE)).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

function withTimeout(promise, ms) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error('timeout')), ms);
    promise.then((v) => { clearTimeout(t); resolve(v); }, (e) => { clearTimeout(t); reject(e); });
  });
}

async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const res = await withTimeout(fetch(request.url, { cache: 'no-cache' }), NETWORK_TIMEOUT_MS);
    if (res.ok) cache.put(request, res.clone());
    return res;
  } catch (err) {
    const hit = await cache.match(request, { ignoreSearch: true });
    if (hit) return hit;
    if (request.mode === 'navigate') {
      const shell = await cache.match('index.html');
      if (shell) return shell;
    }
    throw err;
  }
}

self.addEventListener('fetch', (event) => {
  if (DEV) return; // localhost: браузер ходит за файлами сам
  const { request } = event;
  if (request.method !== 'GET') return;
  if (new URL(request.url).origin !== self.location.origin) return;
  event.respondWith(networkFirst(request));
});
