// Личные функции: «Готовлю сегодня», порции, отметки «приготовлено», локальная статистика.
import * as S from './state.js';

export const FEATURES_VERSION = '2.2';

function h(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function initFeatures({ index, revealSection }) {
  document.documentElement.dataset.featuresVersion = FEATURES_VERSION;
  const labels = new Map(index.days.map((d) => [d.id, d.label]));
  const dayName = (id) => `день ${labels.get(id) ?? id}`;
  const banner = document.getElementById('today-banner');

  /* ---------- Закрепление дня и баннер ---------- */
  function refreshPins() {
    const pinned = S.getPinned();
    document.querySelectorAll('.day-section').forEach((sec) => {
      const btn = sec.querySelector('.pin-btn');
      if (!btn) return;
      const on = !!pinned && pinned.day === sec.id;
      btn.setAttribute('aria-pressed', String(on));
      btn.textContent = on ? '📌 Закреплён на сегодня' : '📌 Готовлю сегодня';
    });
  }

  function renderBanner() {
    const pinned = S.getPinned();
    banner.replaceChildren();

    if (pinned) {
      const a = h('a', 'today-link', `📌 Сегодня: ${dayName(pinned.day)}`);
      a.href = `#${pinned.day}`;
      a.dataset.reveal = pinned.day;
      banner.append(a);
    } else {
      banner.append(h('span', 'today-empty', 'Выберите день и нажмите «Готовлю сегодня»'));
    }

    const recents = S.summarize(S.getStats()).recentDays.filter((id) => !pinned || id !== pinned.day).slice(0, 3);
    if (recents.length) {
      const box = h('span', 'recent', 'Недавние:');
      for (const id of recents) {
        const a = h('a', 'recent-link', labels.get(id) ?? id);
        a.href = `#${id}`;
        a.dataset.reveal = id;
        box.append(a);
      }
      banner.append(box);
    }

    const stats = h('button', 'banner-btn', '📊 Статистика');
    stats.type = 'button';
    stats.id = 'stats-open';
    banner.append(stats);
  }

  /* ---------- Порции ---------- */
  function applyPortions(scope = document) {
    const k = S.getPortions();
    scope.querySelectorAll('td.grams[data-grams]').forEach((td) => {
      td.textContent = `${S.scaleGrams(Number(td.dataset.grams), k)} г`;
    });
    document.querySelectorAll('.portion-select').forEach((sel) => { sel.value = String(k); });
  }

  /* ---------- Отметки «приготовлено» ---------- */
  function restoreDone(section) {
    const done = S.getDone(section.id);
    section.querySelectorAll('.meal-card').forEach((card) => {
      const on = done.has(card.dataset.meal);
      const box = card.querySelector('.done-check');
      if (box) box.checked = on;
      card.classList.toggle('done', on);
    });
  }

  // Приводит все уже отрисованные дни в соответствие с сохранённым состоянием
  function restoreAllDone() {
    document.querySelectorAll('.day-section').forEach((s) => {
      if (s.querySelector('.meals-grid').dataset.loaded === 'true') restoreDone(s);
    });
  }

  // Прямой сброс на экране: не зависит от хранилища (используется при любом (раз)закреплении)
  function resetDoneUI() {
    document.querySelectorAll('.done-check').forEach((box) => { box.checked = false; });
    document.querySelectorAll('.meal-card.done').forEach((card) => card.classList.remove('done'));
  }

  function afterRender(section) {
    applyPortions(section);
    restoreDone(section);
  }

  /* ---------- Статистика ---------- */
  const dlg = document.createElement('dialog');
  dlg.id = 'stats-dialog';
  dlg.setAttribute('aria-label', 'Статистика выбора дней');
  document.body.append(dlg);
  dlg.addEventListener('click', (e) => { if (e.target === dlg) dlg.close(); });

  function openStats() {
    const events = S.getStats();
    const sum = S.summarize(events);
    const body = h('div', 'stats-body');
    body.append(h('h2', '', '📊 Статистика выбора дней'));
    body.append(h('p', 'stats-note',
      `Закреплений: ${sum.total} · разных дней: ${sum.distinct}. Данные хранятся только на этом устройстве.`));

    if (!sum.total) {
      body.append(h('p', '', 'Пока пусто. Нажмите «Готовлю сегодня» у любого дня.'));
    } else {
      body.append(h('h3', '', 'Чаще всего'));
      const max = sum.byDay[0].count;
      const list = h('ul', 'stats-list');
      for (const { day, count } of sum.byDay.slice(0, 10)) {
        const li = h('li');
        li.append(h('span', 'stats-day', dayName(day)));
        const bar = h('span', 'stats-bar');
        bar.style.width = `${Math.max(8, (count / max) * 100)}%`;
        li.append(bar, h('span', 'stats-count', String(count)));
        list.append(li);
      }
      body.append(list);

      body.append(h('h3', '', 'Последние закрепления'));
      const hist = h('ul', 'stats-history');
      for (const e of sum.history) hist.append(h('li', '', `${e.d} — ${dayName(e.day)}`));
      body.append(hist);
    }

    const actions = h('div', 'stats-actions');
    const copy = h('button', 'banner-btn', 'Скопировать JSON');
    copy.type = 'button';
    copy.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(JSON.stringify(events, null, 2));
        copy.textContent = 'Скопировано';
      } catch {
        copy.textContent = 'Не удалось скопировать';
      }
    });
    const clear = h('button', 'banner-btn', 'Очистить');
    clear.type = 'button';
    clear.addEventListener('click', () => {
      if (confirm('Очистить всю статистику выбора дней?')) {
        S.clearStats();
        renderBanner();
        openStats();
      }
    });
    const close = h('button', 'banner-btn', 'Закрыть');
    close.type = 'button';
    close.addEventListener('click', () => dlg.close());
    actions.append(copy, clear, close);
    body.append(actions);
    body.append(h('p', 'stats-note', `Версия интерфейса: ${FEATURES_VERSION}`));

    dlg.replaceChildren(body);
    if (!dlg.open) dlg.showModal();
  }

  /* ---------- События ---------- */
  document.addEventListener('click', (e) => {
    const pin = e.target.closest('.pin-btn');
    if (pin) {
      const id = pin.closest('.day-section').id;
      const pinned = S.getPinned();
      if (pinned && pinned.day === id) S.unpinDay(); // сбрасывает отметки в хранилище
      else S.pinDay(id);                              // сбрасывает отметки в хранилище
      refreshPins();
      renderBanner();
      resetDoneUI(); // и на экране, во всех уже открытых днях
      return;
    }
    if (e.target.closest('#stats-open')) { openStats(); return; }
    const link = e.target.closest('[data-reveal]');
    if (link) {
      e.preventDefault();
      const section = document.getElementById(link.dataset.reveal);
      if (section) revealSection(section);
    }
  });

  document.addEventListener('change', (e) => {
    if (e.target.matches('.portion-select')) {
      S.setPortions(Number(e.target.value));
      applyPortions();
    } else if (e.target.matches('.done-check')) {
      const card = e.target.closest('.meal-card');
      const section = e.target.closest('.day-section');
      S.setDone(section.id, e.target.dataset.meal, e.target.checked);
      card.classList.toggle('done', e.target.checked);
    }
  });

  // Другая вкладка, возврат в приложение или наступивший новый день: обновляем состояние
  const refreshAll = () => {
    refreshPins();
    renderBanner();
    applyPortions();
    restoreAllDone();
  };
  let knownDate = S.todayStr();
  const checkDateChange = () => {
    const now = S.todayStr();
    if (now !== knownDate) {
      knownDate = now;
      refreshAll();
    }
  };
  window.addEventListener('storage', refreshAll);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) { knownDate = S.todayStr(); refreshAll(); }
  });
  setInterval(checkDateChange, 60000);

  refreshPins();
  renderBanner();
  applyPortions();

  return { afterRender };
}
