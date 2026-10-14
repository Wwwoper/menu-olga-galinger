import test from 'node:test';
import assert from 'node:assert/strict';
import { buildSearcher, normalize, parseQuery } from '../../shared/js/search.js';

const index = {
  days: [
    {
      id: 'day-1', index: 0, label: '1',
      search: '1 день 1 хлебцы яйцо фунчоза вок форель лосось семга творог 5 обычный',
      meals: [
        { t: 'breakfast', d: null, dn: null, i: [
          { s: 'хлебцы ржаные', n: 'Хлебцы ржаные' },
          { s: 'яйцо', n: 'Яйцо' },
        ] },
        { t: 'lunch', d: 'фунчоза вок', dn: 'Фунчоза вок', i: [
          { s: 'слабосоленая форель лосось семга', n: 'Слабосолёная форель/лосось/сёмга' },
        ] },
        { t: 'dinner', d: null, dn: null, i: [
          { s: 'творог 5 обычный', n: 'Творог 5% обычный' },
        ] },
      ],
    },
    {
      id: 'day-2', index: 1, label: '2',
      search: '2 день 2 творог яблоко сыр',
      meals: [
        { t: 'dinner', d: null, dn: null, i: [
          { s: 'творог', n: 'Творог' },
          { s: 'яблоко', n: 'Яблоко' },
        ] },
      ],
    },
    {
      id: 'day-3', index: 2, label: '3',
      search: '3 день 3 омлет яйцо сыр',
      meals: [
        { t: 'breakfast', d: 'омлет с сыром', dn: 'Омлет с сыром', i: [
          { s: 'яйцо', n: 'Яйцо' },
          { s: 'сыр', n: 'Сыр' },
        ] },
      ],
    },
  ],
};
const search = buildSearcher(index);

test('ё и е нормализуются одинаково, пунктуация становится разделителем', () => {
  assert.equal(normalize('Сёмга, 5% / грибы'), 'семга 5 грибы');
});

test('запрос разбивается на слова даже без пробелов вокруг пунктуации', () => {
  assert.deepEqual(parseQuery('творог,сыр').include, ['творог', 'сыр']);
});

test('исключение распознаётся после пунктуации, дефис внутри слова не является исключением', () => {
  assert.deepEqual(parseQuery('творог,-сыр'), { include: ['творог'], exclude: ['сыр'] });
  assert.deepEqual(parseQuery('молоко-растительное'), { include: ['молоко-растительное'], exclude: [] });
});

test('порядок слов не важен, каждое включённое слово обязательно', () => {
  assert.deepEqual(search('яйцо творог').map(result => result.day.id), ['day-1']);
  assert.deepEqual(search('творог яйцо').map(result => result.day.id), ['day-1']);
});

test('запрос 5% совпадает с нормализованной жирностью', () => {
  assert.deepEqual(search('творог 5%').map(result => result.day.id), ['day-1']);
});

test('ё/е и разделитель / работают в данных ингредиента', () => {
  assert.deepEqual(search('сёмга').map(result => result.day.id), ['day-1']);
  assert.deepEqual(search('лосось').map(result => result.day.id), ['day-1']);
});

test('минус исключает дни, в которых найдено соответствующее слово', () => {
  assert.deepEqual(search('творог -яйцо').map(result => result.day.id), ['day-2']);
});

test('префиксный поиск находит начало слова', () => {
  assert.deepEqual(search('фунчоз').map(result => result.day.id), ['day-1']);
});

test('результат содержит конкретный приём пищи и оригинальное имя ингредиента', () => {
  const result = search('творог 5%')[0];
  assert.equal(result.hits[0].type, 'dinner');
  assert.equal(result.hits[0].ingredients[0].name, 'Творог 5% обычный');
});

test('пустой запрос возвращает null — интерфейс может показать исходную навигацию', () => {
  assert.equal(search('   '), null);
});
