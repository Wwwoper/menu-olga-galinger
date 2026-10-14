import { initShell } from './shell.js';
import { loadDay } from './store.js';
import { renderMeals } from './render.js';
import { initFeatures } from './features.js';
import { getPinned } from './state.js';
import { buildSearcher, normalize, parseQuery } from './search.js';

const { meta, index, DAY_IDS } = await initShell();
const links = Array.from(document.querySelectorAll('.nav-link'));
const sections = Array.from(document.querySelectorAll('.day-section'));
const searchBox = document.getElementById('search-box');
const noResults = document.getElementById('no-results');
const searchStatus = document.getElementById('search-status');
const navLinks = document.getElementById('nav-links');
const searchResults = document.getElementById('search-results');
const searchClear = document.getElementById('search-clear');
const searcher = buildSearcher(index);
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('sidebar-overlay');
const menuToggle = document.getElementById('menu-toggle');
const mobileCurrentDay = document.getElementById('mobile-current-day');
const themeToggleBtns = document.querySelectorAll('.theme-toggle-btn');
const backBtn = document.getElementById('back-to-top');
const swipeToast = document.getElementById('swipe-toast');
const prevBtn = document.getElementById('day-prev');
const nextBtn = document.getElementById('day-next');
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ===================== Ленивая отрисовка дней ===================== */
function loadSection(section) {
  const grid = section.querySelector('.meals-grid');
  if (grid.dataset.loaded === 'true') return Promise.resolve();
  if (grid.dataset.loading === 'true') return grid.loadPromise ?? Promise.resolve();
  grid.dataset.loading = 'true';
  grid.loadPromise = (async () => {
    try {
      const day = await loadDay(section.id);
      grid.replaceChildren(renderMeals(day, meta));
      grid.dataset.loaded = 'true';
      initToggleButtons(grid);
      features.afterRender(section);
    } catch (err) {
      console.error(err);
      const msg = document.createElement('div');
      msg.className = 'load-error';
      msg.setAttribute('role', 'alert');
      msg.style.gridColumn = '1 / -1';
      msg.append('Не удалось загрузить день. ');
      const retry = document.createElement('button');
      retry.type = 'button';
      retry.className = 'toggle-rows';
      retry.textContent = 'Повторить';
      retry.addEventListener('click', () => loadSection(section));
      msg.append(retry);
      grid.replaceChildren(msg);
    } finally {
      delete grid.dataset.loading;
      delete grid.loadPromise;
    }
  })();
  return grid.loadPromise;
}
function clearSearchHighlights(scope = document) {
  scope.querySelectorAll('tr.search-hit, .dish-name.search-hit').forEach(node => {
    node.classList.remove('search-hit');
  });
  scope.querySelectorAll('tbody.extra-rows[data-search-opened="true"]').forEach(extra => {
    extra.hidden = true;
    delete extra.dataset.searchOpened;
    const button = extra.closest('.meal-card')?.querySelector('.toggle-rows');
    if (button) {
      button.setAttribute('aria-expanded', 'false');
      button.textContent = button.dataset.label || 'Показать ещё';
    }
  });
}
function highlightSearchMatches(section, terms) {
  if (!terms.length) return;
  clearSearchHighlights(section);
  section.querySelectorAll('.meal-card').forEach(card => {
    const dish = card.querySelector('.dish-name');
    if (dish && terms.some(term => normalize(dish.textContent).split(' ').some(word => word.startsWith(term)))) {
      dish.classList.add('search-hit');
    }
    card.querySelectorAll('tbody tr').forEach(row => {
      const cell = row.querySelector('td:first-child');
      if (!cell) return;
      const words = normalize(cell.textContent).split(' ');
      if (!terms.some(term => words.some(word => word.startsWith(term)))) return;
      row.classList.add('search-hit');
      const extra = row.closest('tbody.extra-rows');
      if (extra && extra.hidden) {
        extra.hidden = false;
        extra.dataset.searchOpened = 'true';
        const button = extra.closest('.meal-card')?.querySelector('.toggle-rows');
        if (button) {
          button.setAttribute('aria-expanded', 'true');
          button.textContent = 'Скрыть';
        }
      }
    });
  });
}

/* Подгружаем соседние дни перед прокруткой, чтобы страница не «уезжала» */
async function revealSection(section, { instant = true, terms = [] } = {}) {
  if (!terms.length && section.dataset.searchTerms !== undefined) {
    terms = section.dataset.searchTerms.split(/\s+/).filter(Boolean);
    delete section.dataset.searchTerms;
  }
  const i = sections.indexOf(section);
  await Promise.all(sections.slice(Math.max(0, i - 3), i + 2).map(loadSection));
  highlightSearchMatches(section, terms);
  section.scrollIntoView({ block: 'start', behavior: instant || reduceMotion ? 'instant' : 'smooth' });
  history.replaceState(null, '', `#${section.id}`);
}

const features = initFeatures({ index, revealSection });

const lazyObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) loadSection(entry.target);
  });
}, { rootMargin: '800px 0px 800px 0px' });
sections.forEach(s => lazyObserver.observe(s));

/* ===================== Сворачиваемые длинные списки ===================== */
function initToggleButtons(scope) {
  scope.querySelectorAll('.toggle-rows').forEach(btn => {
    if (btn.dataset.bound) return;
    btn.dataset.bound = '1';
    btn.dataset.label = btn.textContent;

    btn.addEventListener('click', () => {
      const card = btn.closest('.meal-card');
      if (!card) return;

      const table = card.querySelector('table');
      if (!table) return;

      const extra = table.querySelector('.extra-rows');
      if (!extra) return;

      const expanded = btn.getAttribute('aria-expanded') === 'true';
      extra.hidden = expanded;
      delete extra.dataset.searchOpened;
      btn.setAttribute('aria-expanded', String(!expanded));
      btn.textContent = expanded ? btn.dataset.label : 'Скрыть';
    });
  });
}
/* ===================== Поиск по дням и ингредиентам ===================== */
const MEAL_LABEL = type => meta.mealTypes[type]?.label ?? type;
function renderSearchResults(found, terms) {
  const fragment = document.createDocumentFragment();
  for (const result of found.slice(0, 30)) {
    const card = document.createElement('article');
    card.className = 'sr-card';
    const link = document.createElement('a');
    link.className = 'sr-day';
    link.href = `#${result.day.id}`;
    link.dataset.reveal = result.day.id;
    link.dataset.searchTerms = terms.join(' ');
    link.textContent = `День ${result.day.label}`;
    card.append(link);

    for (const hit of result.hits.slice(0, 3)) {
      const row = document.createElement('p');
      row.className = 'sr-hit';
      const details = [];
      if (hit.dishMatched && hit.dish) details.push(`Блюдо: ${hit.dish}`);
      const names = hit.ingredients.slice(0, 4).map(ingredient => ingredient.name);
      if (names.length) details.push(`Ингредиенты: ${names.join(', ')}`);
      row.textContent = `${MEAL_LABEL(hit.type)}${details.length ? ` · ${details.join('; ')}` : ''}`;
      card.append(row);
    }
    fragment.append(card);
  }
  if (found.length > 30) {
    const more = document.createElement('p');
    more.className = 'sr-more';
    more.textContent = `Показаны первые 30 из ${found.length} дней`;
    fragment.append(more);
  }
  searchResults.replaceChildren(fragment);
}
function applySearch() {
  const raw = searchBox.value;
  const found = searcher(raw);
  clearSearchHighlights();
  searchResults.replaceChildren();
  searchClear.hidden = !raw.trim();
  navLinks.hidden = found !== null;

  if (found === null) {
    links.forEach(link => { link.hidden = false; link.style.display = ''; });
    searchResults.hidden = true;
    noResults.hidden = true;
    searchStatus.textContent = '';
    return;
  }

  const ids = new Set(found.map(result => result.day.id));
  links.forEach(link => { link.hidden = !ids.has(link.getAttribute('href').slice(1)); });
  searchResults.hidden = found.length === 0;
  noResults.hidden = found.length > 0;
  searchStatus.textContent = found.length ? `Найдено дней: ${found.length}` : 'Найдено дней: 0';
  renderSearchResults(found, parseQuery(raw).include);
}
let searchTimer;
searchBox.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(applySearch, 80);
});
searchBox.addEventListener('keydown', event => {
  if (event.key === 'Escape' && searchBox.value) {
    event.preventDefault();
    event.stopPropagation();
    searchBox.value = '';
    clearTimeout(searchTimer);
    applySearch();
  } else if (event.key === 'Enter') {
    clearTimeout(searchTimer);
    applySearch();
    const firstResult = searchResults.querySelector('.sr-day');
    if (firstResult) {
      event.preventDefault();
      firstResult.click();
    }
  }
});
searchClear.addEventListener('click', () => {
  searchBox.value = '';
  clearTimeout(searchTimer);
  applySearch();
  searchBox.focus();
});
searchResults.addEventListener('click', event => {
  const link = event.target.closest('.sr-day');
  if (!link) return;
  const section = document.getElementById(link.dataset.reveal);
  if (section) section.dataset.searchTerms = link.dataset.searchTerms || '';
  if (window.innerWidth <= 768 && sidebar.classList.contains('open')) closeSidebar();
});

/* ===================== Активный день / индикатор ===================== */
function setActiveById(id) {
  links.forEach(l => l.classList.remove('active'));
  const link = document.querySelector(`.nav-link[href="#${id}"]`);
  if (link) {
    link.classList.add('active');
    mobileCurrentDay.textContent = link.getAttribute('data-day');
  }
  const idx = DAY_IDS.indexOf(id);
  if (prevBtn) prevBtn.disabled = idx <= 0;
  if (nextBtn) nextBtn.disabled = idx === -1 || idx >= DAY_IDS.length - 1;
}
const activeObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) setActiveById(entry.target.getAttribute('id'));
  });
}, { rootMargin: '-10% 0px -80% 0px' });
sections.forEach(s => activeObserver.observe(s));

window.addEventListener('scroll', () => {
  backBtn.style.display = window.scrollY > 400 ? 'block' : 'none';
});
backBtn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' }));

/* ===================== Тёмная тема ===================== */
const root = document.documentElement;
function applyTheme(theme) {
  root.setAttribute('data-theme', theme);
  localStorage.setItem('menu-theme', theme);
  themeToggleBtns.forEach(b => b.textContent = theme === 'dark' ? '☀️' : '🌙');
}
const savedTheme = localStorage.getItem('menu-theme')
  || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
applyTheme(savedTheme);
themeToggleBtns.forEach(btn => btn.addEventListener('click', () => {
  applyTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
}));

/* ===================== Мобильное выдвижное меню + focus trap ===================== */
let lastFocused = null;
function getFocusable() {
  return Array.from(sidebar.querySelectorAll('a,button,input')).filter(el => el.offsetParent !== null);
}
function openSidebar() {
  lastFocused = document.activeElement;
  sidebar.classList.add('open');
  overlay.classList.add('visible');
  document.body.style.overflow = 'hidden';
  menuToggle.setAttribute('aria-expanded', 'true');
  document.getElementById('content').setAttribute('aria-hidden', 'true');
  setTimeout(() => searchBox.focus(), 150);
}
function closeSidebar() {
  sidebar.classList.remove('open');
  overlay.classList.remove('visible');
  document.body.style.overflow = '';
  menuToggle.setAttribute('aria-expanded', 'false');
  document.getElementById('content').removeAttribute('aria-hidden');
  if (lastFocused) lastFocused.focus();
}
menuToggle.addEventListener('click', () => {
  sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
});
overlay.addEventListener('click', closeSidebar);
document.addEventListener('keydown', e => {
  if (!sidebar.classList.contains('open')) return;
  if (e.key === 'Escape') { closeSidebar(); return; }
  if (e.key === 'Tab') {
    const focusable = getFocusable();
    if (focusable.length === 0) return;
    const first = focusable[0], last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }
});
links.forEach(l => l.addEventListener('click', () => {
  if (window.innerWidth <= 768) closeSidebar();
}));

/* ===================== Переход между днями (кнопки) ===================== */
function goToDay(idx) {
  if (idx < 0 || idx >= DAY_IDS.length) return;
  const el = document.getElementById(DAY_IDS[idx]);
  if (!el) return;
  loadSection(el);
  el.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
  showToast(el.querySelector('.day-title').textContent);
}
function currentIndex() {
  const activeLink = document.querySelector('.nav-link.active');
  if (!activeLink) return 0;
  const id = activeLink.getAttribute('href').slice(1);
  return DAY_IDS.indexOf(id);
}
if (prevBtn) prevBtn.addEventListener('click', () => goToDay(currentIndex() - 1));
if (nextBtn) nextBtn.addEventListener('click', () => goToDay(currentIndex() + 1));

function showToast(text) {
  swipeToast.textContent = 'День ' + text;
  swipeToast.classList.add('show');
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => swipeToast.classList.remove('show'), 900);
}

/* ===================== Свайп между днями (мобильные) ===================== */
let touchStartX = 0, touchStartY = 0, touchStartTarget = null;
const content = document.getElementById('content');
content.addEventListener('touchstart', e => {
  if (window.innerWidth > 768) return;
  const t = e.touches[0];
  touchStartX = t.clientX;
  touchStartY = t.clientY;
  touchStartTarget = e.target;
}, { passive: true });

content.addEventListener('touchend', e => {
  if (window.innerWidth > 768) return;
  if (touchStartTarget && touchStartTarget.closest('.table-scroll')) return;
  const t = e.changedTouches[0];
  const dx = t.clientX - touchStartX;
  const dy = t.clientY - touchStartY;
  if (Math.abs(dx) > 70 && Math.abs(dx) > Math.abs(dy) * 1.5) {
    const idx = currentIndex();
    if (dx < 0) goToDay(idx + 1);
    else goToDay(idx - 1);
  }
}, { passive: true });

/* Инициализация: подгружаем первый видимый день сразу */
if (sections[0]) loadSection(sections[0]);
setActiveById(DAY_IDS[0]);

/* Старт: ссылка #day-N имеет приоритет, иначе открываем день, закреплённый на сегодня */
const hashId = decodeURIComponent(location.hash.slice(1));
const hashSection = hashId ? document.getElementById(hashId) : null;
const pinned = getPinned();
const startSection = hashSection && hashSection.classList.contains('day-section')
  ? hashSection
  : (pinned && document.getElementById(pinned.day));
if (startSection && startSection !== sections[0]) revealSection(startSection);

/* PWA: офлайн-режим */
if ('serviceWorker' in navigator) {
  const register = () => navigator.serviceWorker.register('service-worker.js').catch(console.error);
  if (document.readyState === 'complete') register();
  else window.addEventListener('load', register);
}