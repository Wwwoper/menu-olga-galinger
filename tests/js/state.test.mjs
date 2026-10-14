// Запуск: node --test tests/js
import test from 'node:test';
import assert from 'node:assert/strict';

const store = new Map();
globalThis.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
};

const S = await import('../../shared/js/state.js');
const { plural, fill } = await import('../../shared/js/shell.js').catch(() => ({}));

const day1 = new Date(2026, 9, 5, 12);
const day2 = new Date(2026, 9, 6, 8);

test.beforeEach(() => store.clear());

test('todayStr использует локальную дату', () => {
  assert.equal(S.todayStr(day1), '2026-10-05');
  assert.equal(S.todayStr(new Date(2026, 0, 3)), '2026-01-03');
});

test('порции: масштабирование и допустимые значения', () => {
  assert.equal(S.scaleGrams(22, 2), 44);
  assert.equal(S.scaleGrams(13, 1.5), 20);
  assert.equal(S.scaleGrams(13, 0.5), 7);
  assert.equal(S.getPortions(), 1);
  S.setPortions(1.5);
  assert.equal(S.getPortions(), 1.5);
  S.setPortions(7);
  assert.equal(S.getPortions(), 1.5);
  store.set('menu-portions', '"мусор"');
  assert.equal(S.getPortions(), 1);
  assert.equal(S.formatK(1.5), '×1,5');
});

test('закрепление дня действует только сегодня', () => {
  assert.equal(S.pinDay('day-12', day1), true);
  assert.equal(S.getPinned(day1).day, 'day-12');
  assert.equal(S.getPinned(day2), null);
  assert.equal(S.pinDay('day-12', day1), false);
  S.unpinDay();
  assert.equal(S.getPinned(day1), null);
});

test('статистика: пара дата+день считается один раз', () => {
  S.pinDay('day-12', day1);
  S.unpinDay();
  S.pinDay('day-12', day1);
  S.pinDay('day-7', day1);
  S.pinDay('day-12', day2);
  const sum = S.summarize(S.getStats());
  assert.equal(sum.total, 3);
  assert.equal(sum.distinct, 2);
  assert.deepEqual(sum.byDay, [{ day: 'day-12', count: 2 }, { day: 'day-7', count: 1 }]);
  assert.deepEqual(sum.recentDays, ['day-12', 'day-7']);
  assert.equal(sum.history[0].d, '2026-10-06');
});

test('статистика: повреждённые данные игнорируются', () => {
  store.set('menu-stats', '{"x":1}');
  assert.deepEqual(S.getStats(), []);
  store.set('menu-stats', '[{"d":"2026-10-05","day":"day-1"},null,{"d":1}]');
  assert.equal(S.getStats().length, 1);
  store.set('menu-stats', 'не json');
  assert.deepEqual(S.getStats(), []);
});

test('отметки «приготовлено»: сохраняются за сегодня и сбрасываются завтра', () => {
  S.setDone('day-5', 'breakfast', true, day1);
  S.setDone('day-5', 'dinner', true, day1);
  assert.deepEqual([...S.getDone('day-5', day1)].sort(), ['breakfast', 'dinner']);
  S.setDone('day-5', 'breakfast', false, day1);
  assert.deepEqual([...S.getDone('day-5', day1)], ['dinner']);
  assert.equal(S.getDone('day-5', day2).size, 0);
});

test('clearStats очищает историю', () => {
  S.pinDay('day-1', day1);
  S.clearStats();
  assert.equal(S.getStats().length, 0);
});

test('plural и fill для «день/дня/дней»', { skip: !plural }, () => {
  const f = ['день', 'дня', 'дней'];
  assert.equal(plural(1, f), 'день');
  assert.equal(plural(44, f), 'дня');
  assert.equal(plural(45, f), 'дней');
  assert.equal(plural(11, f), 'дней');
  assert.equal(plural(21, f), 'день');
  assert.equal(fill('Меню на {count} {days}', 44), 'Меню на 44 дня');
});
