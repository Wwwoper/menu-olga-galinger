// JSON дня -> DOM карточек. Разметка повторяет прежний шаблон 1:1,
// плюс data-grams (для порций) и чекбокс «Приготовлено».

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === 'class') node.className = v;
    else node.setAttribute(k, v);
  }
  node.append(...children);
  return node;
}

function row(ing) {
  return el('tr', {},
    el('td', {}, ing.name),
    el('td', { class: 'grams', 'data-grams': String(ing.grams) }, `${ing.grams} г`));
}

function renderMeal(meal, meta) {
  const type = meta.mealTypes[meal.type];
  const h3 = el('h3', {}, meal.dish ? `${type.icon} ${type.label} ` : `${type.icon} ${type.label}`);
  if (meal.dish) {
    h3.append(el('span', { class: 'dish-name' }, `— ${meal.dish}`));
  }

  const limit = meta.collapseAfter;
  const visible = meal.ingredients.slice(0, limit);
  const extra = meal.ingredients.slice(limit);

  const table = el('table', {},
    el('thead', {}, el('tr', {},
      el('th', { scope: 'col' }, 'Ингредиент'),
      el('th', { scope: 'col' }, 'Граммовка'))),
    el('tbody', {}, ...visible.map(row)));

  const card = el('div', { class: 'meal-card', 'data-meal': meal.type },
    h3, el('div', { class: 'table-scroll' }, table));

  if (extra.length) {
    const tbody = el('tbody', { class: 'extra-rows' }, ...extra.map(row));
    tbody.hidden = true;
    table.append(tbody);
    card.append(el('button', {
      type: 'button',
      class: 'toggle-rows',
      'aria-expanded': 'false',
    }, `Показать ещё ${extra.length}`));
  }

  const check = el('input', { type: 'checkbox', class: 'done-check', 'data-meal': meal.type });
  card.append(el('label', { class: 'done-toggle' }, check, ' Приготовлено'));
  return card;
}

export function renderMeals(day, meta) {
  const frag = document.createDocumentFragment();
  for (const meal of day.meals) frag.append(renderMeal(meal, meta));
  return frag;
}
