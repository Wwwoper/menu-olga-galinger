// Единый набор контурных SVG-иконок приложения. Имена и SVG — только из этого списка.
const PATHS = Object.freeze({
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  'chevron-left': '<path d="m15 18-6-6 6-6"/>',
  'chevron-right': '<path d="m9 18 6-6-6-6"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/>',
  moon: '<path d="M20.9 13A9 9 0 0 1 11 3.1 9 9 0 1 0 20.9 13Z"/>',
  pin: '<path d="M16 3H8l1 6-3 3v2h12v-2l-3-3 1-6ZM12 14v7"/>',
  star: '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9L12 3Z"/>',
  'eye-off': '<path d="m3 3 18 18M10.6 10.6a2 2 0 0 0 2.8 2.8"/><path d="M9.9 5.2A10.8 10.8 0 0 1 12 5c5 0 8.5 4.5 9 7-.2 1.1-1.1 2.5-2.5 3.7M6.2 6.2C3.8 7.8 2.3 10.3 2 12c.5 2.5 4 7 10 7 1.2 0 2.3-.2 3.3-.6"/>',
  'list-days': '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  search: '<circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/>',
  x: '<path d="m18 6-12 12M6 6l12 12"/>',
  chart: '<path d="M4 19V5m0 14h17M8 16v-5m5 5V7m5 9v-8"/>',
  'arrow-up': '<path d="m5 12 7-7 7 7M12 19V5"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6m4 4v6m6-6v6"/>',
  'sunrise': '<path d="M3 18h18M5 14a7 7 0 0 1 14 0M12 2v3m-7 1 2 2m12-2-2 2m-7 3h4"/>',
  utensils: '<path d="M7 3v7m-3-7v4a3 3 0 0 0 6 0V3m-3 7v11M17 3v18m0-18c3 2 3 7 0 9"/>',
  'moon-star': '<path d="M20.5 14A8.5 8.5 0 0 1 10 3.5 8.5 8.5 0 1 0 20.5 14Z"/><path d="m17 3 .7 1.3L19 5l-1.3.7L17 7l-.7-1.3L15 5l1.3-.7L17 3Z"/>',
  'apple': '<path d="M12 8c-2-3-7-2-7 3 0 5 4 10 7 8 3 2 7-3 7-8 0-5-5-6-7-3Zm0 0c0-3 2-5 5-5"/>',
});

export const ICON_NAMES = Object.freeze(Object.keys(PATHS));

export function createIcon(name, { className = 'icon', size = 20 } = {}) {
  const paths = PATHS[name];
  if (!paths) throw new RangeError(`Неизвестная иконка: ${name}`);
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', className);
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('width', String(size));
  svg.setAttribute('height', String(size));
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '1.8');
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('stroke-linejoin', 'round');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('focusable', 'false');
  // SVG-фрагменты берутся исключительно из статического доверенного словаря выше.
  svg.innerHTML = paths;
  return svg;
}
