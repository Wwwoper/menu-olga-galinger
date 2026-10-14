// Загрузка и кэш JSON. Пути считаются от расположения этого файла,
// поэтому сайт работает и в корне домена, и в подкаталоге /food-flow/.
const contentUrl = (path) => new URL(`../../content/${path}`, import.meta.url);

const cache = new Map();

async function fetchJson(path) {
  const res = await fetch(contentUrl(path), { cache: 'no-cache' });
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json();
}

function cached(key, loader) {
  if (!cache.has(key)) {
    const p = loader().catch((err) => {
      cache.delete(key); // даём шанс повторить
      throw err;
    });
    cache.set(key, p);
  }
  return cache.get(key);
}

export const loadMeta = () => cached('meta', () => fetchJson('meta.json'));
export const loadIndex = () => cached('index', () => fetchJson('days.json'));

let fileById = new Map();
export function registerIndex(index) {
  fileById = new Map(index.days.map((d) => [d.id, d.file]));
}

export function loadDay(id) {
  const file = fileById.get(id);
  if (!file) return Promise.reject(new Error(`Неизвестный день: ${id}`));
  return cached(`day:${id}`, () => fetchJson(file));
}
