// Shared by every page: icons, theme button, the list of books and which shelf each is on.
// Nothing here talks to anything but this computer.
'use strict';

const ICONS = {
  home: '<path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1z"/>',
  bolt: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
  check: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/>',
  chat: '<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9h8M8 12h5"/>',
  books: '<path d="M3 4h4v16H3zM9 4h4v16H9zM15 6l4-1 3 14-4 1z"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
  moon: '<path d="M20 14.5A8 8 0 0 1 9.500 4 8 8 0 1 0 20 14.500z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.500 1.500M17.500 17.500 19 19M19 5l-1.500 1.500M6.500 17.500 5 19"/>',
  eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  box: '<path d="M3 7l9-4 9 4v10l-9 4-9-4z"/><path d="M3 7l9 4 9-4M12 11v10"/>',
  map: '<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/>',
  leaf: '<path d="M5 19c0-8 5-14 15-15-1 10-7 15-15 15z"/><path d="M5 19 13 11"/>',
  anchor: '<circle cx="12" cy="5" r="2"/><path d="M12 7v14M8 11h8M4 14a8 8 0 0 0 16 0"/>',
  music: '<path d="M9 18V5l11-2v13"/><circle cx="6.500" cy="18" r="2.500"/><circle cx="17.500" cy="16" r="2.500"/>',
  film: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>',
  folder: '<path d="M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/>',
  power: '<path d="M12 3v9"/><path d="M6.300 7a8 8 0 1 0 11.400 0"/>',
  drop: '<path d="M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z"/>',
  wrench: '<path d="M14.500 6.500a4 4 0 0 0 5 5L12 19a2.100 2.100 0 0 1-3-3l7.500-7.500a4 4 0 0 0-2-2z"/>',
  heart: '<path d="M12 20s-7-4.500-7-10a4 4 0 0 1 7-2.500A4 4 0 0 1 19 10c0 5.500-7 10-7 10z"/>',
  print: '<path d="M7 9V3h10v6"/><rect x="3" y="9" width="18" height="8" rx="1"/><path d="M7 14h10v7H7z"/>'
};
function icon(name) {
  return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (ICONS[name] || '') + '</svg>';
}
document.querySelectorAll('[data-ic]').forEach(function (e) { e.innerHTML = icon(e.dataset.ic); });

const esc = function (s) {
  return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; });
};
const gb = function (n) { return n >= 1e9 ? (n / 1e9).toFixed(1) + ' GB' : Math.max(1, Math.round(n / 1e6)) + ' MB'; };

// Theme button: Dark -> Day -> Night (red) -> Dark.
const THEMES = [['dark', 'Dark', 'moon'], ['day', 'Day', 'sun'], ['night', 'Night', 'eye']];
function paintTheme(btn) {
  const cur = document.documentElement.getAttribute('data-theme') || 'dark';
  const t = THEMES.find(function (x) { return x[0] === cur; }) || THEMES[0];
  btn.innerHTML = icon(t[2]) + '<span>' + t[1] + '</span>';
  btn.setAttribute('aria-label', 'Theme: ' + t[1] + '. Press to change.');
}
document.querySelectorAll('.theme').forEach(function (btn) {
  paintTheme(btn);
  btn.addEventListener('click', function () {
    const cur = document.documentElement.getAttribute('data-theme') || 'dark';
    const i = THEMES.findIndex(function (x) { return x[0] === cur; });
    const next = THEMES[(i + 1) % THEMES.length][0];
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem('lo-theme', next); } catch (e) {}
    document.querySelectorAll('.theme').forEach(paintTheme);
  });
});

// The manifest says which shelf each known book belongs on. A book the user
// added themselves lands on "Other" and is still searched.
const ARCHIVE_SHELVES = ['archive', 'skills'];   // big collections kept out of the main search
let _lib = null;
async function library() {
  if (_lib) return _lib;
  let manifest = { items: [], shelves: [], tiers: [] };
  let status = { books: 0, kiwix: false, ask: { enabled: false } };
  try { manifest = await (await fetch('/api/manifest')).json(); } catch (e) {}
  try { status = await (await fetch('/api/status')).json(); } catch (e) {}
  let books = [];
  let up = false;
  try {
    const r = await fetch('/kiwix/catalog/v2/entries?count=-1');
    if (r.ok) {
      up = true;
      const x = new DOMParser().parseFromString(await r.text(), 'text/xml');
      books = Array.from(x.querySelectorAll('entry')).map(function (e) {
        const ls = Array.from(e.querySelectorAll('link'));
        const h = ls.find(function (l) { return (l.getAttribute('type') || '') === 'text/html'; });
        const z = ls.find(function (l) { return l.getAttribute('length'); });
        const s = e.querySelector('summary');
        const id = h ? h.getAttribute('href').replace(/^.*\/content\//, '').replace(/\/$/, '') : '';
        const item = manifest.items.find(function (it) { return id.indexOf(it.id + '_') === 0 || id === it.id; });
        return {
          id: id,
          title: item ? item.title : e.querySelector('title').textContent,
          summary: s ? s.textContent : '',
          bytes: z ? +z.getAttribute('length') : (item ? item.bytes : 0),
          shelf: item ? item.shelf : 'other',
          item: item || null
        };
      }).filter(function (b) { return b.id; });
    }
  } catch (e) {}
  const shelves = manifest.shelves.slice();
  if (books.some(function (b) { return b.shelf === 'other'; })) shelves.push({ id: 'other', name: 'Other', blurb: 'Books you added yourself' });
  _lib = { manifest: manifest, status: status, books: books, shelves: shelves, up: up };
  return _lib;
}
function shelfBooks(lib, shelf) {
  if (shelf === 'all') return lib.books.filter(function (b) { return ARCHIVE_SHELVES.indexOf(b.shelf) < 0; });
  return lib.books.filter(function (b) { return b.shelf === shelf; });
}
// Your own files: the folders under /files/ (music, films, documents the reader added).
// The listing is JSON in the shape nginx's autoindex_format json gives, so it works behind either server.
async function listFiles(dir) {
  try {
    const r = await fetch('/files/' + (dir ? dir.split('/').map(encodeURIComponent).join('/') + '/' : ''));
    if (!r.ok) return [];
    const items = await r.json();
    return Array.isArray(items) ? items.filter(function (i) { return i && i.name && i.name[0] !== '.'; }) : [];
  } catch (e) { return []; }
}
async function ownFiles() {
  return (await listFiles('')).filter(function (i) { return i.type === 'directory'; });
}
function emptyNotice() {
  return '<div class="notice"><b class="tag">No books loaded yet</b>' +
    '<p>The pages work, but the shelves are empty. While you still have internet, run the fetch script in the project folder to download a set of books:</p>' +
    '<p><code>fetch --list</code> shows the sets and their sizes. <code>fetch --tier pocket</code> downloads the smallest one.</p>' +
    '<p class="muted small">Then start the library again. See <a href="/about.html">About this library</a>.</p></div>';
}
