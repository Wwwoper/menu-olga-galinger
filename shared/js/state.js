// Личное состояние в localStorage: порции, закреплённый день, отметки «приготовлено», статистика.
// Ключ темы (menu-theme) остаётся в app.js и здесь не трогается.
const KEYS = {
  portions: 'menu-portions',
  pinned: 'menu-pinned',
  done: 'menu-done',
  stats: 'menu-stats',
};
const STATS_LIMIT = 1000;

export const PORTION_OPTIONS = [0.5, 1, 1.5, 2, 3];

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false; // приватный режим или переполнение
  }
}

function remove(key) {
  try {
    localStorage.removeItem(key);
  } catch { /* ignore */ }
}

export function todayStr(now = new Date()) {
  const p = (n) => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())}`;
}

/* ---------- Порции ---------- */
export const scaleGrams = (grams, k) => Math.round(grams * k);
export const formatK = (k) => `×${String(k).replace('.', ',')}`;

export function getPortions() {
  const k = Number(read(KEYS.portions, 1));
  return PORTION_OPTIONS.includes(k) ? k : 1;
}

export function setPortions(k) {
  if (PORTION_OPTIONS.includes(k)) write(KEYS.portions, k);
}

/* ---------- Отметки «приготовлено» (только за сегодня) ---------- */
function readDone(now) {
  const d = read(KEYS.done, null);
  if (d && d.date === todayStr(now) && d.days && typeof d.days === 'object') return d;
  return { date: todayStr(now), days: {} };
}

export function getDone(dayId, now = new Date()) {
  const list = readDone(now).days[dayId];
  return new Set(Array.isArray(list) ? list : []);
}

export function setDone(dayId, mealType, value, now = new Date()) {
  const d = readDone(now);
  const set = new Set(d.days[dayId] || []);
  if (value) set.add(mealType);
  else set.delete(mealType);
  if (set.size) d.days[dayId] = [...set];
  else delete d.days[dayId];
  write(KEYS.done, d);
}

// Отметки относятся к одному «сеансу готовки»: любое новое закрепление или снятие
// закрепления начинает его заново.
export function clearDone() {
  remove(KEYS.done);
}

/* ---------- Закреплённый день ---------- */
export function getPinned(now = new Date()) {
  const p = read(KEYS.pinned, null);
  return p && typeof p.day === 'string' && p.date === todayStr(now) ? p : null;
}

export function getStats() {
  const s = read(KEYS.stats, []);
  return Array.isArray(s) ? s.filter((e) => e && typeof e.day === 'string' && typeof e.d === 'string') : [];
}

// Возвращает true, если закрепление новое (тогда отметки «приготовлено» сбрасываются).
// В статистику одна пара «дата + день» попадает один раз.
export function pinDay(dayId, now = new Date()) {
  const date = todayStr(now);
  const cur = getPinned(now);
  if (cur && cur.day === dayId) return false;
  write(KEYS.pinned, { day: dayId, date });
  clearDone();
  const stats = getStats();
  if (!stats.some((e) => e.d === date && e.day === dayId)) {
    stats.push({ d: date, day: dayId });
    write(KEYS.stats, stats.slice(-STATS_LIMIT));
  }
  return true;
}

export function unpinDay() {
  remove(KEYS.pinned);
  clearDone();
}

export function clearStats() {
  remove(KEYS.stats);
}

/* summarize: чистая функция, удобно тестировать */
export function summarize(events) {
  const counts = new Map();
  const lastSeen = new Map();
  events.forEach((e, i) => {
    counts.set(e.day, (counts.get(e.day) || 0) + 1);
    lastSeen.set(e.day, i);
  });
  const byDay = [...counts.entries()]
    .map(([day, count]) => ({ day, count, last: lastSeen.get(day) }))
    .sort((a, b) => b.count - a.count || b.last - a.last)
    .map(({ day, count }) => ({ day, count }));
  const history = [...events].reverse().slice(0, 14);
  const recentDays = [];
  for (let i = events.length - 1; i >= 0 && recentDays.length < 5; i--) {
    if (!recentDays.includes(events[i].day)) recentDays.push(events[i].day);
  }
  return { total: events.length, distinct: counts.size, byDay, history, recentDays };
}
