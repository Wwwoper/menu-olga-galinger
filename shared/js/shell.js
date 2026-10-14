// Строит оболочку страницы (ссылки навигации и пустые секции дней) из content/days.json.
import { loadIndex, loadMeta, registerIndex } from './store.js';
import { PORTION_OPTIONS, formatK } from './state.js';

export function plural(n, forms) {
  const a = Math.abs(n) % 100;
  const b = a % 10;
  if (a > 10 && a < 20) return forms[2];
  if (b > 1 && b < 5) return forms[1];
  if (b === 1) return forms[0];
  return forms[2];
}

export function fill(template, count) {
  return template
    .replace('{count}', String(count))
    .replace('{days}', plural(count, ['день', 'дня', 'дней']));
}

function buildTools() {
  const tools = document.createElement('div');
  tools.className = 'day-tools';

  const pin = document.createElement('button');
  pin.type = 'button';
  pin.className = 'pin-btn';
  pin.setAttribute('aria-pressed', 'false');
  pin.textContent = '📌 Готовлю сегодня';

  const label = document.createElement('label');
  label.className = 'portion-label';
  label.append('Порции ');
  const select = document.createElement('select');
  select.className = 'portion-select';
  for (const k of PORTION_OPTIONS) {
    const opt = document.createElement('option');
    opt.value = String(k);
    opt.textContent = formatK(k);
    select.append(opt);
  }
  label.append(select);

  tools.append(pin, label);
  return tools;
}

export async function initShell() {
  const [meta, index] = await Promise.all([loadMeta(), loadIndex()]);
  registerIndex(index);

  const n = index.mainDays;
  document.title = fill(meta.pageTitle, n);
  const sidebarTitle = document.querySelector('#sidebar h1');
  if (sidebarTitle && sidebarTitle.firstChild) {
    sidebarTitle.firstChild.textContent = `${fill(meta.sidebarTitle, n)} `;
  }
  const mobileDay = document.getElementById('mobile-current-day');
  if (mobileDay) mobileDay.textContent = fill(meta.mobileDefault, n);
  const headerTitle = document.querySelector('#top-header h1');
  const headerSub = document.querySelector('#top-header p');
  if (headerTitle) headerTitle.textContent = meta.title;
  if (headerSub) headerSub.textContent = fill(meta.subtitle, n);

  const navRoot = document.getElementById('nav-links');
  const end = document.getElementById('days-end');
  const navFrag = document.createDocumentFragment();
  const secFrag = document.createDocumentFragment();

  for (const d of index.days) {
    const a = document.createElement('a');
    a.href = `#${d.id}`;
    a.className = 'nav-link';
    a.dataset.day = d.label;
    a.dataset.search = d.search;
    a.textContent = d.label;
    navFrag.append(a, '\n');

    const section = document.createElement('section');
    section.id = d.id;
    section.className = 'day-section';
    section.dataset.index = String(d.index);

    const title = document.createElement('h2');
    title.className = 'day-title';
    title.textContent = d.label;

    const grid = document.createElement('div');
    grid.className = 'meals-grid';
    grid.dataset.loaded = 'false';

    section.append(title, buildTools(), grid);
    secFrag.append(section);
  }
  navRoot.append(navFrag);
  end.before(secFrag);

  return { meta, index, DAY_IDS: index.days.map((d) => d.id) };
}
