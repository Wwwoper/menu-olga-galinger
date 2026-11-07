// Строит оболочку страницы (ссылки навигации и пустые секции дней) из content/days.json.
import { loadIndex, loadMeta, registerIndex } from './store.js';
import { PORTION_OPTIONS, formatK } from './state.js';
import { createIcon } from './icons.js';

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
  pin.setAttribute('aria-label', 'Закрепить день на сегодня');
  pin.title = 'Закрепить день на сегодня';
  pin.append(createIcon('pin'));

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

  const favorite = document.createElement('button');
  favorite.type = 'button';
  favorite.className = 'favorite-btn';
  favorite.setAttribute('aria-pressed', 'false');
  favorite.setAttribute('aria-label', 'Добавить день в избранное');
  favorite.title = 'Добавить день в избранное';
  favorite.append(createIcon('star'));

  const hide = document.createElement('button');
  hide.type = 'button';
  hide.className = 'hide-day-btn';
  hide.setAttribute('aria-label', 'Скрыть день');
  hide.title = 'Скрыть день';
  hide.append(createIcon('eye-off'));

  tools.append(pin, favorite, hide, label);
  return tools;
}

async function loadClientConfig() {
  try {
    const response = await fetch(new URL('../../client.json', import.meta.url), { cache: 'no-cache' });
    if (!response.ok) throw new Error(`client.json: HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    if (error instanceof TypeError || String(error.message).includes('HTTP 404')) {
      return {
        name: 'Меню', shortName: 'Меню', themeColor: '#2f7a4f',
        assets: {
          favicon: 'shared/assets/default/favicon.ico',
          favicon16: 'shared/assets/default/favicon-16x16.png',
          favicon32: 'shared/assets/default/favicon-32x32.png',
          icon192: 'shared/assets/default/icon-192x192.png',
          icon512: 'shared/assets/default/icon-512x512.png',
          appleTouchIcon: 'shared/assets/default/apple-touch-icon.png',
        },
      };
    }
    throw error;
  }
}

function applyClientConfig(config) {
  document.title = config.name;
  const headerTitle = document.querySelector('#top-header h1');
  if (headerTitle) headerTitle.textContent = config.name;
  const sidebarTitle = document.querySelector('#sidebar h1');
  if (sidebarTitle?.firstChild) sidebarTitle.firstChild.textContent = `${config.shortName} `;
  const mobileTitle = document.getElementById('client-apple-title');
  if (mobileTitle) mobileTitle.content = config.shortName;
  const theme = document.getElementById('client-theme-color');
  if (theme) theme.content = config.themeColor;
  const links = {
    'client-favicon': config.assets.favicon,
    'client-favicon-16': config.assets.favicon16,
    'client-favicon-32': config.assets.favicon32,
    'client-favicon-192': config.assets.icon192,
    'client-favicon-512': config.assets.icon512,
    'client-apple-touch-icon': config.assets.appleTouchIcon,
  };
  for (const [id, href] of Object.entries(links)) {
    const link = document.getElementById(id);
    if (link) link.href = href;
  }
}

export async function initShell() {
  const [meta, index, client] = await Promise.all([loadMeta(), loadIndex(), loadClientConfig()]);
  applyClientConfig(client);
  registerIndex(index);

  const n = index.mainDays;
  document.title = `${client.name} · ${fill(meta.pageTitle, n)}`;
  const sidebarTitle = document.querySelector('#sidebar h1');
  if (sidebarTitle && sidebarTitle.firstChild) {
    sidebarTitle.firstChild.textContent = `${client.shortName} `;
  }
  const mobileDay = document.getElementById('mobile-current-day');
  if (mobileDay) mobileDay.textContent = fill(meta.mobileDefault, n);
  const headerSub = document.querySelector('#top-header p');
  if (headerSub) headerSub.textContent = fill(meta.subtitle, n);

  const navRoot = document.getElementById('nav-links');
  const end = document.getElementById('days-end');
  const filters = document.createElement('div');
  filters.id = 'day-filters';
  filters.setAttribute('role', 'group');
  filters.setAttribute('aria-label', 'Разделы дней');
  for (const [value, label] of [['all', 'Все'], ['favorites', 'Избранное'], ['hidden', 'Скрытые']]) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'day-filter-btn';
    button.dataset.filter = value;
    button.setAttribute('aria-label', label);
    button.title = label;
    button.append(createIcon(value === 'all' ? 'list-days' : value === 'favorites' ? 'star' : 'eye-off'));
    button.setAttribute('aria-pressed', 'false');
    filters.append(button);
  }
  navRoot.before(filters);
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

  return { meta, index, client, DAY_IDS: index.days.map((d) => d.id) };
}
