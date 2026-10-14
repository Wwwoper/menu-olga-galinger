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
const day1 = new Date(2026, 9, 5, 12);

test.beforeEach(() => store.clear());

test('новое закрепление другого дня сбрасывает отметки', () => {
  S.pinDay('day-5', day1);
  S.setDone('day-5', 'breakfast', true, day1);
  S.pinDay('day-6', day1);
  assert.equal(S.getDone('day-5', day1).size, 0);
});

test('снять закрепление и поставить заново: отметки сброшены', () => {
  S.pinDay('day-5', day1);
  S.setDone('day-5', 'breakfast', true, day1);
  S.setDone('day-5', 'dinner', true, day1);
  S.unpinDay();
  assert.equal(S.getDone('day-5', day1).size, 0);
  S.setDone('day-5', 'lunch', true, day1);
  S.pinDay('day-5', day1);
  assert.equal(S.getDone('day-5', day1).size, 0);
});

test('повторное закрепление того же дня без изменений отметки не трогает', () => {
  S.pinDay('day-5', day1);
  S.setDone('day-5', 'breakfast', true, day1);
  assert.equal(S.pinDay('day-5', day1), false);
  assert.deepEqual([...S.getDone('day-5', day1)], ['breakfast']);
});

test('сброс отметок не трогает статистику и порции', () => {
  S.setPortions(2);
  S.pinDay('day-5', day1);
  S.unpinDay();
  S.pinDay('day-5', day1);
  assert.equal(S.getStats().length, 1);
  assert.equal(S.getPortions(), 2);
});
