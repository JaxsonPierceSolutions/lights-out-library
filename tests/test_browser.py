"""A real browser opens every page. The test fails if any page asks for anything
that is not on 127.0.0.1, logs an error, or scrolls sideways on a phone.

It runs against a stand-in book server (fake_kiwix.py), so it needs no books.
It skips when Playwright isn't installed, except in CI, where
LIGHTSOUT_REQUIRE_BROWSER=1 turns a skip into a failure. To run it here:
  pip install pytest playwright && playwright install chromium
  python -m pytest tests/test_browser.py
Playwright is a test tool only. The library itself doesn't use it.
"""
import os
import threading
from urllib.parse import urlsplit

import pytest

import fake_kiwix
from helpers import make_cfg
from lightsout import server as srvmod

REQUIRED = os.environ.get("LIGHTSOUT_REQUIRE_BROWSER") == "1"
try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    if REQUIRED:
        raise
    pytest.skip("Playwright is not installed", allow_module_level=True)

PAGES = [
    "/",
    "/search.html",
    "/search.html?q=how+do+I+stop+bleeding",
    "/search.html?q=water&shelf=water",
    "/search.html?shelf=medical",
    "/search.html?q=zzzznothing",
    "/answers.html",
    "/books.html",
    "/skills.html",
    "/ask.html",
    "/about.html",
    "/files.html",
]
SIZES = {"phone": (390, 844), "tablet": (768, 1024), "desktop": (1440, 900)}


def serve(tmp_path, empty=False, kiwix_up=True):
    kiwix, kiwix_url = fake_kiwix.start(empty=empty)
    if not kiwix_up:
        kiwix.shutdown()
        kiwix.server_close()
    cfg = make_cfg(tmp_path, kiwix_url=kiwix_url)
    srv = srvmod.make_server(cfg)          # the real site/ and the real manifest
    threading.Thread(target=srv.serve_forever, args=(0.05,), daemon=True).start()
    return srv, kiwix, "http://127.0.0.1:%d" % srv.server_address[1]


@pytest.fixture(scope="module")
def chromium():
    with sync_playwright() as play:
        try:
            browser = play.chromium.launch()
        except PlaywrightError:
            if REQUIRED:
                raise
            pytest.skip("Chromium for Playwright is not installed")
        yield browser
        browser.close()


class Watch:
    """Opens pages and records every request, console error and page error."""

    def __init__(self, browser, base, size="phone"):
        self.base = base
        self.outside, self.errors, self.local = [], [], []
        self.ctx = browser.new_context(viewport={"width": SIZES[size][0], "height": SIZES[size][1]})
        self.page = self.ctx.new_page()
        self.ctx.route("**/*", self._route)
        self.page.on("console", lambda m: self.errors.append(m.text) if m.type == "error" else None)
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))

    def _route(self, route):
        url = route.request.url
        host = urlsplit(url).hostname
        if url.startswith(("data:", "blob:", "about:")) or host == "127.0.0.1":
            self.local.append(url)
            return route.continue_()
        self.outside.append(url)       # anything else never leaves the machine, and fails the test
        route.abort()

    def open(self, path):
        self.page.goto(self.base + path, wait_until="networkidle")
        return self.page

    def close(self):
        self.ctx.close()


@pytest.fixture()
def site(tmp_path):
    srv, kiwix, base = serve(tmp_path)
    yield base
    srv.shutdown()
    srv.server_close()
    kiwix.shutdown()
    kiwix.server_close()


@pytest.mark.parametrize("size", list(SIZES))
def test_no_page_makes_an_outside_request(chromium, site, size):
    w = Watch(chromium, site, size)
    for path in PAGES:
        page = w.open(path)
        assert page.title().endswith("Lights Out Library"), path
        wide = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert wide <= 1, "%s scrolls sideways by %dpx at %s" % (path, wide, size)
    assert not w.outside, "pages asked for something outside this computer: %s" % w.outside
    assert not w.errors, "browser errors: %s" % w.errors
    assert any(u.endswith(".woff2") for u in w.local), "the fonts should load from the repo"
    w.close()


def test_the_watcher_really_catches_an_outside_request(chromium, site):
    """Proves the check above can fail: a page that reaches for another host is caught."""
    w = Watch(chromium, site)
    # A bare page, because the server's own security header would stop this before the watcher saw it.
    w.page.set_content('<img src="https://example.com/pixel.png"><link rel="stylesheet" href="https://fonts.example.com/a.css">',
                       wait_until="networkidle")
    assert sorted(w.outside) == ["https://example.com/pixel.png", "https://fonts.example.com/a.css"]
    w.close()


def test_the_server_tells_the_browser_to_refuse_outside_requests(chromium, site):
    """Second line of defence: the Content-Security-Policy header blocks them even without this test's watcher."""
    ctx = chromium.new_context()
    page = ctx.new_page()
    resp = page.goto(site + "/", wait_until="networkidle")
    csp = resp.headers.get("content-security-policy", "")
    assert "default-src 'self'" in csp and "connect-src 'self'" in csp
    blocked = page.evaluate("fetch('https://example.com/').then(() => false).catch(() => true)")
    assert blocked
    ctx.close()


def test_home_shows_shelves_search_and_book_count(chromium, site):
    w = Watch(chromium, site)
    page = w.open("/")
    assert page.locator("form.search input").is_visible()
    assert page.locator("#shelves .tile").count() == 6
    assert "books loaded" in page.locator("#state").inner_text()
    assert page.locator("#ask-card").is_hidden(), "Ask is off by default, so its card stays hidden"
    assert page.evaluate("[...document.images].every(i => i.complete && i.naturalWidth > 0)")
    w.close()


def test_search_shows_a_quick_answer_then_results(chromium, site):
    w = Watch(chromium, site)
    page = w.open("/search.html?q=how+do+I+stop+bleeding")
    assert page.locator(".answer h3").first.inner_text() == "How do I stop serious bleeding?"
    assert page.locator("a.row").count() >= 1
    href = page.locator("a.row").first.get_attribute("href")
    assert href.startswith("/kiwix/viewer#")
    w.close()


def test_theme_button_cycles_and_is_remembered(chromium, site):
    w = Watch(chromium, site)
    page = w.open("/answers.html")
    theme = lambda: page.evaluate("document.documentElement.dataset.theme")
    assert theme() == "dark"
    page.locator("button.theme").click()
    assert theme() == "day"
    page.locator("button.theme").click()
    assert theme() == "night"
    page = w.open("/books.html")
    assert theme() == "night", "the choice carries to the next page"
    # Night (red): nothing bright is on screen.
    bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
    assert bg == "rgb(5, 0, 0)"
    w.close()


def test_touch_targets_are_thumb_sized(chromium, site):
    w = Watch(chromium, site)
    for path in ("/", "/search.html?q=water", "/answers.html"):
        page = w.open(path)
        small = page.evaluate("""() => [...document.querySelectorAll('a.chip, a.tile, a.card, a.row, button, form.search input, .bar a.home')]
            .filter(e => e.offsetParent !== null && e.getBoundingClientRect().height < 44)
            .map(e => e.className + ':' + Math.round(e.getBoundingClientRect().height))""")
        assert not small, "%s has targets under 44px: %s" % (path, small)
    w.close()


def test_first_run_with_no_books_says_what_to_do(chromium, tmp_path):
    srv, kiwix, base = serve(tmp_path, empty=True)
    w = Watch(chromium, base)
    page = w.open("/")
    assert "No books loaded yet" in page.locator("#empty").text_content()
    assert "fetch --tier pocket" in page.locator("#empty").text_content()
    page = w.open("/answers.html")
    assert page.locator(".answer").count() >= 10, "quick answers work with no books"
    assert not w.outside
    w.close()
    srv.shutdown()
    srv.server_close()
    kiwix.shutdown()
    kiwix.server_close()


def test_book_server_down_is_said_plainly(chromium, tmp_path):
    srv, _, base = serve(tmp_path, kiwix_up=False)
    w = Watch(chromium, base)
    page = w.open("/")
    assert "not running" in page.locator("#state").inner_text()
    page = w.open("/search.html?q=burn")
    assert "book server is not running" in page.locator("#out").inner_text().lower()
    assert page.locator(".answer").count() == 1, "the quick answer still shows"
    assert not w.outside
    w.close()
    srv.shutdown()
    srv.server_close()
