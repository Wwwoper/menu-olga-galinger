import test from 'node:test';
import assert from 'node:assert/strict';

class FakeElement {
  constructor(name) { this.name = name; this.attributes = {}; this.innerHTML = ''; }
  setAttribute(key, value) { this.attributes[key] = String(value); }
}

globalThis.document = {
  createElementNS: (_namespace, name) => new FakeElement(name),
};

const { createIcon, ICON_NAMES } = await import('../../shared/js/icons.js');

test('набор иконок содержит только уникальные имена', () => {
  assert.ok(ICON_NAMES.length > 0);
  assert.equal(new Set(ICON_NAMES).size, ICON_NAMES.length);
});

test('createIcon создаёт декоративный SVG с едиными атрибутами', () => {
  const icon = createIcon('star');
  assert.equal(icon.name, 'svg');
  assert.equal(icon.attributes.viewBox, '0 0 24 24');
  assert.equal(icon.attributes.stroke, 'currentColor');
  assert.equal(icon.attributes['aria-hidden'], 'true');
  assert.equal(icon.attributes.focusable, 'false');
  assert.match(icon.innerHTML, /<path/);
});

test('createIcon поддерживает размер и класс', () => {
  const icon = createIcon('menu', { size: 24, className: 'custom-icon' });
  assert.equal(icon.attributes.width, '24');
  assert.equal(icon.attributes.height, '24');
  assert.equal(icon.attributes.class, 'custom-icon');
});

test('неизвестная иконка вызывает понятную ошибку', () => {
  assert.throws(() => createIcon('not-an-icon'), /Неизвестная иконка/);
});
