"""Checks on the pages that need no browser: nothing points outside this computer,
every local file a page asks for exists, and the design rules that can be read
from the files hold. The browser test (test_browser.py) proves the same thing
by actually loading the pages."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PAGES = sorted(SITE.glob("*.html"))
TEXT_FILES = [p for p in SITE.rglob("*") if p.suffix in {".html", ".css", ".js"}]

# A URL with a scheme, or a protocol-relative //host. The SVG namespace is the one
# string that looks like a URL but is never fetched.
OUTSIDE = re.compile(r"""(?:https?:|wss?:|ftp:)//|["'(=]\s*//[a-z0-9]""", re.I)
ALLOWED = ("http://www.w3.org/2000/svg",)


def test_there_are_pages():
    names = {p.name for p in PAGES}
    assert {"index.html", "search.html", "answers.html", "books.html", "skills.html", "ask.html", "about.html", "files.html"} <= names


def test_no_outside_urls_in_site_files():
    bad = []
    for path in TEXT_FILES:
        text = path.read_text(encoding="utf-8")
        for allowed in ALLOWED:
            text = text.replace(allowed, "")
        for n, line in enumerate(text.splitlines(), 1):
            if OUTSIDE.search(line):
                bad.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()[:100]}")
    assert not bad, "pages must not point at another host:\n" + "\n".join(bad)


def test_every_local_file_a_page_asks_for_exists():
    missing = []
    for page in PAGES:
        html = page.read_text(encoding="utf-8")
        for ref in re.findall(r"""(?:src|href)=["'](/[^"'#?]*)""", html):
            if ref.startswith(("/kiwix/", "/api/", "/ask/")) or ref == "/":
                continue
            if not (SITE / ref.lstrip("/")).is_file():
                missing.append(f"{page.name}: {ref}")
    css = (SITE / "css" / "app.css").read_text(encoding="utf-8")
    for ref in re.findall(r"url\(([^)]+)\)", css):
        if not (SITE / "css" / ref.strip("\"'")).resolve().is_file():
            missing.append(f"app.css: {ref}")
    assert not missing, missing


def test_pages_open_dark_and_set_the_theme_before_painting():
    for page in PAGES:
        html = page.read_text(encoding="utf-8")
        assert '<html lang="en" data-theme="dark">' in html, page.name
        head = html.split("</head>")[0]
        assert head.index("/js/theme.js") < head.index("/css/app.css"), page.name
        assert 'name="viewport"' in head, page.name


def test_three_themes_are_defined_with_every_token():
    css = (SITE / "css" / "app.css").read_text(encoding="utf-8")
    tokens = ["--bg", "--surface", "--surface-2", "--line", "--text", "--muted", "--accent", "--accent-ink", "--ok", "--danger"]
    for theme in ("dark", "day", "night"):
        block = re.search(r"\[data-theme=%s\]\{([^}]*)\}" % theme, css)
        assert block, theme
        for token in tokens:
            assert token + ":" in block.group(1), f"{theme} is missing {token}"


def _luminance(hex_color):
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a, b):
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_text_contrast_meets_the_design_floor():
    """DESIGN.md: 7:1 for body text, 4.5:1 for everything else, in Dark and Day.
    Night (red) is deliberately dim to protect night vision, so it has a lower floor."""
    css = (SITE / "css" / "app.css").read_text(encoding="utf-8")
    for theme, body_floor, other_floor in (("dark", 7, 4.5), ("day", 7, 4.5), ("night", 4.5, 3)):
        block = re.search(r"\[data-theme=%s\]\{([^}]*)\}" % theme, css).group(1)
        tok = dict(re.findall(r"(--[a-z0-9-]+):(#[0-9a-f]{6})", block))
        for bg in ("--bg", "--surface"):
            assert _contrast(tok["--text"], tok[bg]) >= body_floor, (theme, bg, "text")
            assert _contrast(tok["--muted"], tok[bg]) >= other_floor, (theme, bg, "muted")
            assert _contrast(tok["--accent"], tok[bg]) >= other_floor, (theme, bg, "accent")
        assert _contrast(tok["--accent-ink"], tok["--accent"]) >= 4.5, (theme, "button text")


def test_fonts_ship_with_their_license():
    fonts = SITE / "fonts"
    assert list(fonts.glob("*.woff2")), "fonts must be in the repo"
    assert "SIL OPEN FONT LICENSE" in (fonts / "LICENSE-Geist.txt").read_text(encoding="utf-8").upper()


def test_pictures_are_small_and_each_has_its_prompt_on_record():
    pics = list((SITE / "img").glob("*.jpg"))
    assert pics, "no pictures"
    assert sum(p.stat().st_size for p in pics) < 2_000_000, "site/img must stay under 2 MB"
    for pic in pics:
        for letter in ("a", "b"):
            side = ROOT / "art" / f"{pic.stem}-{letter}.json"
            assert side.is_file(), f"missing {side.name}"
            assert json.loads(side.read_text(encoding="utf-8")).get("prompt"), side.name
            assert (ROOT / "art" / f"{pic.stem}-{letter}.jpg").is_file()


def test_nothing_personal_came_across():
    """No home-network addresses in the pages or manifest. A maintainer can also keep a private
    list of words that must never appear (names, places, equipment) in tests/private-words.txt,
    one regular expression per line; that file is git-ignored so the list itself stays private."""
    patterns = [r"\b192\.168\.\d", r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", r"\b172\.(1[6-9]|2\d|3[01])\.\d"]
    private = ROOT / "tests" / "private-words.txt"
    if private.is_file():
        patterns += [w.strip() for w in private.read_text(encoding="utf-8").splitlines() if w.strip() and not w.startswith("#")]
    words = re.compile("|".join("(?:%s)" % p for p in patterns), re.I)
    hits = []
    for path in list(TEXT_FILES) + [ROOT / "manifest" / "content.json"]:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if words.search(line):
                hits.append(f"{path.relative_to(ROOT)}:{n}")
    assert not hits, hits


def test_quick_answers_all_name_a_source():
    js = (SITE / "js" / "answers.js").read_text(encoding="utf-8")
    ids = re.findall(r"\{ id: '([a-z-]+)'", js)
    assert len(ids) >= 10 and len(ids) == len(set(ids))
    assert js.count("src: '") == len(ids)
