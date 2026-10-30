/* Khulaasaa shared icon registry. Use KhulaasaaIcons.svg(name, className). */
(function (root) {
  'use strict';
  const paths = {
    home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-6v-7H10v7H4a1 1 0 0 1-1-1z"/>',
    bookmark: '<path d="M6 4h12v17l-6-4-6 4z"/>',
    bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    filter: '<path d="M4 5h16l-6 7v6l-4 2v-8z"/>',
    'chevron-down': '<path d="m6 9 6 6 6-6"/>',
    'chevron-up': '<path d="m6 15 6-6 6 6"/>',
    search: '<circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
    'external-link': '<path d="M14 3h7v7M10 14 21 3"/><path d="M19 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h6"/>',
    close: '<path d="m6 6 12 12M18 6 6 18"/>'
  };
  function svg(name, className) {
    const body = paths[name];
    if (!body) return '';
    const cls = className ? ' class="' + String(className).replace(/[&"<>]/g, '') + '"' : '';
    return '<svg' + cls + ' viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' + body + '</svg>';
  }
  root.KhulaasaaIcons = Object.freeze({ svg, names: Object.freeze(Object.keys(paths)) });
})(window);
