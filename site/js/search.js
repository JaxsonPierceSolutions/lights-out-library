// The search page. The book server ranks every book's hits in one list, so one
// textbook that repeats a chapter can fill the page. We pull a deep batch, drop
// repeats and junk, and cap how many results one book gets per page.
'use strict';

const FETCH = 150;      // results pulled from the book server per search
const PER_PAGE = 20;
const PER_BOOK = 4;     // most results from one book on a page, when several books are searched

const u = new URLSearchParams(location.search);
const q = (u.get('q') || '').trim();
const page = Math.max(1, parseInt(u.get('page') || '1', 10));
const $ = function (id) { return document.getElementById(id); };

// Words that mean the question is medical, so the medical books should lead.
const MEDICAL = /\b(deep cut|cut off|amputat\w*|severed|stab\w*|gunshot|shot|artery|injur\w*|hurt|bone|cut (my|his|her|your|a|the) (finger|hand|arm|leg|foot|head|face)|laceration|wound|bleed|bleeding|burned|burnt|burn treatment|scald|fever|pain|bite|bitten|sting|stung|infect|infection|infected|broken|fracture|sprain|rash|cough|vomit|vomiting|diarrhea|tooth|toothache|abscess|poison|poisoning|choking|choke|pregnan\w*|birth|labor|seizure|stroke|heart attack|chest pain|allerg\w*|asthma|diabet\w*|insulin|antibiotic\w*|medicine|medication|dose|dosage|stitch|stitches|suture|splint|concussion|frostbite|hypothermia|dehydrat\w*|swollen|swelling|blister|headache|nausea|sick|illness|disease|symptom\w*|tick|lyme|snakebite|overdose|unconscious|cpr)\b/i;
const STOP = new Set('how what when where why which who whom is are was were am do does did i you we my our your the a an to of for in on at it its be been should would could will shall good long much many best way there this that these those with and or if from by as about'.split(' '));

function keywords(text) {
  const w = text.toLowerCase().replace(/[^a-z0-9\s'-]/g, ' ').split(/\s+/).filter(function (x) { return x && !STOP.has(x); });
  return w.length ? w.join(' ') : text;
}
function snippet(d) {
  let h = '';
  if (!d) return h;
  d.childNodes.forEach(function (n) { h += n.nodeName === 'b' ? '<b>' + esc(n.textContent) + '</b>' : esc(n.textContent); });
  return h.replace(/^[.\s]+/, '').trim();
}
// "7.1: Foodborne Illness" and "15.5: Foodborne Illness" are one chapter reused by different courses.
function titleKey(t) { return t.toLowerCase().replace(/^\s*[\d.]+\s*[:.)-]\s*/, '').replace(/\s+/g, ' ').trim(); }
function isJunk(t) { return /^questions\/tagged\/|_page=\d+$|^(highest voted|newest|hot|active) .* questions$|\/[a-z]{2}(-[a-z]+)?$|^(category|template|user|file|talk):|editing instructions$/i.test(t); }
// Some documents have a web address for a title; show their first words instead.
function niceTitle(t, snipText) {
  if (!/^www\.|^https?:|\.html?$/i.test(t)) return t;
  const w = (snipText || '').replace(/\s+/g, ' ').trim().split(' ').slice(0, 9).join(' ');
  return w ? w + '…' : 'Untitled document';
}
function tidy(items, manyBooks) {
  const seen = new Set();
  const clean = [];
  items.forEach(function (it) {
    if (isJunk(it.title)) return;
    const k = titleKey(it.title);
    if (seen.has(k)) return;
    seen.add(k);
    clean.push(it);
  });
  if (!manyBooks) return clean;
  const out = [];
  let rest = clean;
  while (rest.length) {
    const count = {};
    const later = [];
    let taken = 0;
    rest.forEach(function (it) {
      if (taken < PER_PAGE && (count[it.bookId] || 0) < PER_BOOK) { count[it.bookId] = (count[it.bookId] || 0) + 1; out.push(it); taken++; }
      else later.push(it);
    });
    if (!taken) break;
    rest = later;
  }
  return out;
}
function card(it) {
  return '<a class="row" href="/kiwix/viewer#' + it.link + '"><b>' + esc(it.title) + '</b>' + (it.snip ? '<p>' + it.snip + '</p>' : '') +
    '<span class="src">' + esc(it.book) + '</span></a>';
}

async function run() {
  const out = $('out');
  const lib = await library();
  const names = { all: 'Everything practical' };
  lib.shelves.forEach(function (s) { names[s.id] = s.name; });
  const shelf = names[u.get('shelf')] ? u.get('shelf') : 'all';
  const shelfName = names[shelf];

  $('q').value = q;
  $('title').textContent = shelf === 'all' ? 'Search' : shelfName;
  $('barname').textContent = shelf === 'all' ? 'Search' : shelfName;
  document.title = (shelf === 'all' ? 'Search' : shelfName) + ' · Lights Out Library';
  $('q').placeholder = shelf === 'all' ? 'Search the library' : 'Search ' + shelfName;
  $('f').onsubmit = function (e) {
    e.preventDefault();
    const v = $('q').value.trim();
    if (v) location.search = '?q=' + encodeURIComponent(v) + (shelf !== 'all' ? '&shelf=' + shelf : '');
  };
  $('scope').innerHTML = Object.keys(names).map(function (k) {
    return '<a class="chip' + (k === shelf ? ' on' : '') + '" href="?' + (q ? 'q=' + encodeURIComponent(q) + '&amp;' : '') + 'shelf=' + k + '"' +
      (k === shelf ? ' aria-current="true"' : '') + '>' + esc(names[k]) + '</a>';
  }).join('');

  const quick = q ? findAnswers(q).map(answerCard).join('') : '';
  if (!lib.up) {
    $('sub').textContent = '';
    out.innerHTML = quick + '<div class="notice"><b class="tag">The book server is not running</b><p>Close the library and start it again with the start script. Quick answers still work.</p></div>';
    return;
  }
  if (!lib.books.length) { $('sub').textContent = ''; out.innerHTML = quick + emptyNotice(); return; }

  const bs = shelfBooks(lib, shelf);
  const titleOf = {};
  lib.books.forEach(function (b) { titleOf[b.id] = b.title; });
  if (!q) {
    if (shelf === 'all') { $('sub').textContent = 'Searches ' + bs.length + ' practical books. The big archives have their own shelves.'; return; }
    $('sub').textContent = bs.length ? bs.length + (bs.length === 1 ? ' book' : ' books') + ' on this shelf. Search here, or open a book.' : '';
    out.innerHTML = bs.length ? '<h2>Books on this shelf</h2>' + bs.map(function (b) {
      return '<a class="row" href="/kiwix/viewer#' + b.id + '/"><b>' + esc(b.title) + '</b>' + (b.bytes ? '<span class="meta mono" style="margin-left:0">' + gb(b.bytes) + '</span>' : '') + '</a>';
    }).join('') : '<div class="notice"><b class="tag">Not loaded</b><p>No books from this shelf are on this computer. <a href="/about.html">See what can be added</a>.</p></div>';
    return;
  }
  if (!bs.length) { $('sub').textContent = ''; out.innerHTML = quick + '<div class="notice"><b class="tag">Not loaded</b><p>No books from this shelf are on this computer. Try <a href="?q=' + encodeURIComponent(q) + '">searching everything</a>.</p></div>'; return; }

  const askLink = lib.status.ask && lib.status.ask.enabled && /\s/.test(q)
    ? '<p class="muted small">Want a direct answer? <a class="chip" href="/ask.html?q=' + encodeURIComponent(q) + '">Ask this question</a></p>' : '';
  out.innerHTML = quick + askLink + '<p class="muted">Searching…</p>';

  const fetchItems = async function (books, n) {
    // The book server needs books.name repeated once per book for a search across several.
    const url = '/kiwix/search?format=xml&pageLength=' + n + '&start=1&pattern=' + encodeURIComponent(keywords(q)) +
      books.map(function (b) { return '&books.name=' + encodeURIComponent(b.id); }).join('');
    const r = await fetch(url);
    if (!r.ok) throw new Error('search ' + r.status);
    const x = new DOMParser().parseFromString(await r.text(), 'text/xml');
    return Array.from(x.querySelectorAll('item')).map(function (i) {
      const link = i.querySelector('link').textContent.replace(/^.*\/content\//, '');
      const bk = i.querySelector('book > title');
      const wc = i.querySelector('wordCount');
      const bookId = link.split('/')[0];
      const d = i.querySelector('description');
      return { title: niceTitle(i.querySelector('title').textContent, d ? d.textContent.replace(/^[.\s]+/, '') : ''), link: link, bookId: bookId,
        book: titleOf[bookId] || (bk ? bk.textContent : ''), snip: snippet(d), words: wc ? wc.textContent : '' };
    });
  };

  try {
    // A medical question typed into the main search: lead with the medical books.
    let medBlock = '';
    const medLinks = new Set();
    if (shelf === 'all' && page === 1 && MEDICAL.test(q)) {
      const mb = shelfBooks(lib, 'medical');
      const med = mb.length ? tidy(await fetchItems(mb, 40), true).slice(0, 5) : [];
      if (med.length) {
        med.forEach(function (it) { medLinks.add(it.link); });
        medBlock = '<h2>From the medical books</h2>' + med.map(card).join('') +
          '<p class="small"><a href="?q=' + encodeURIComponent(q) + '&amp;shelf=medical">More medical results</a></p>';
      }
    }
    const raw = (await fetchItems(bs, FETCH)).filter(function (it) { return !medLinks.has(it.link); });
    const items = tidy(raw, bs.length > 1);
    if (!items.length && !medBlock) {
      $('sub').textContent = '';
      out.innerHTML = quick + askLink + '<div class="notice"><b class="tag">Nothing found</b><p>No page matches “' + esc(q) + '”. Try fewer or simpler words' + (shelf !== 'all' ? ', or <a href="?q=' + encodeURIComponent(q) + '">search everything</a>' : '') + '.</p></div>' +
        (quick ? '' : '<h2>Quick answers</h2><div class="chips">' + ANSWERS.map(function (x) {
          return '<a class="chip" href="/answers.html#a-' + x.id + '">' + esc(x.q.replace(/\?$/, '')) + '</a>';
        }).join('') + '</div>');
      return;
    }
    const pages = Math.max(1, Math.ceil(items.length / PER_PAGE));
    const p = Math.min(page, pages);
    const show = items.slice((p - 1) * PER_PAGE, p * PER_PAGE);
    const found = items.length + medLinks.size;
    $('sub').textContent = (found === 1 ? '1 result' : 'Best ' + found + ' results') + ' for “' + q + '”' + (pages > 1 ? ', page ' + p + ' of ' + pages : '');
    out.innerHTML = (p === 1 ? quick + askLink + medBlock : '') + ((quick || medBlock) && p === 1 && show.length ? '<h2>From the library</h2>' : '') + show.map(card).join('');
    if (pages > 1) {
      const base = '?q=' + encodeURIComponent(q) + (shelf !== 'all' ? '&shelf=' + shelf : '') + '&page=';
      $('pager').hidden = false;
      $('prev').href = base + Math.max(1, p - 1);
      $('prev').setAttribute('aria-disabled', p <= 1);
      $('next').href = base + (p + 1);
      $('next').setAttribute('aria-disabled', p >= pages);
    }
  } catch (e) {
    $('sub').textContent = '';
    out.innerHTML = quick + '<div class="notice"><b class="tag">The search did not come back</b><p>The book server stopped answering. Close the library and start it again.</p></div>';
  }
}
run();
