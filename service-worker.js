// Офлайн-режим. Стратегия: сначала сеть (свежие данные), при сбое или медленном
// соединении (> 4 с) — копия из кэша. При установке кэшируются оболочка и ВСЕ дни.
// Меняете этот файл или список SHELL? Увеличьте VERSION.
// На localhost (локальная разработка) кэш отключён: файлы всегда берутся с сервера.
const VERSION = 'v6';
const CACHE = `food-flow-${VERSION}`;
const NETWORK_TIMEOUT_MS = 4000;
const DEV = ['localhost', '127.0.0.1', '[::1]'].includes(self.location.hostname);

const SHELL = [
  './',
  'index.html',
  'manifest.json',
  'client.json',
  'shared/css/main.css',
  'shared/css/search.css',
  'shared/js/app.js',
  'shared/js/features.js',
  'shared/js/icons.js',
  'shared/js/render.js',
  'shared/js/search.js',
  'shared/js/shell.js',
  'shared/js/state.js',
  'shared/js/store.js',
  'content/meta.json',
  'shared/assets/default/favicon.ico',
  'shared/assets/default/favicon-16x16.png',
  'shared/assets/default/favicon-32x32.png',
  'shared/assets/default/icon-192x192.png',
  'shared/assets/default/icon-512x512.png',
  'shared/assets/default/apple-touch-icon.png',
];

self.addEventListener('install', (event) => {
  if (DEV) { self.skipWaiting(); return; }
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    // Оболочка обязательна: ошибка отсутствующего файла должна сорвать установку,
    // а не оставлять частично работающий офлайн-кэш.
    const shell = SHELL.filter((url) => url !== 'client.json' && url !== 'manifest.json');
    await cache.addAll(shell.map((url) => new Request(url, { cache: 'reload' })));

    // client.json и manifest обязательны в клиентском деплое, но отсутствуют
    // в исходном репозитории шаблона. При локальном просмотре шаблона пропускаем их.
    const clientResponse = await fetch('client.json', { cache: 'reload' });
    if (clientResponse.ok) {
      const client = await clientResponse.clone().json();
      await cache.put('client.json', clientResponse);
      const assets = Object.values(client.assets || {});
      if (assets.length) await cache.addAll(assets);
      const manifestResponse = await fetch('manifest.json', { cache: 'reload' });
      if (!manifestResponse.ok) throw new Error(`Не удалось загрузить manifest.json: HTTP ${manifestResponse.status}`);
      await cache.put('manifest.json', manifestResponse);
    }

    const response = await fetch('content/days.json', { cache: 'reload' });
    if (!response.ok) throw new Error(`Не удалось загрузить content/days.json: HTTP ${response.status}`);
    const index = await response.clone().json();
    if (!index || !Array.isArray(index.days)) {
      throw new Error('Некорректный content/days.json: ожидается массив days');
    }
    await cache.put('content/days.json', response);

    const dayRequests = index.days.map((day) => {
      if (!day || typeof day.file !== 'string' || day.file.startsWith('/') || day.file.includes('..')) {
        throw new Error('Некорректный путь файла дня в content/days.json');
      }
      return new Request(`content/${day.file}`, { cache: 'reload' });
    });
    if (dayRequests.length) await cache.addAll(dayRequests);
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
