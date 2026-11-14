"""The shared JPS tokens, and the rules that keep the look from drifting.

site/css/tokens.css is a copy of the JPS Console's tokens, made by scripts/sync_tokens.py and never
edited by hand. site/css/lightsout-tokens.css holds only what Lights Out adds (DESIGN.md, Tokens).
site/css/app.css writes no raw color, font size or radius: only var(--...). Plain regular
expressions on purpose, so there is nothing to install.
"""
import hashlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CSS_DIR = ROOT / "site" / "css"
TOKENS = (CSS_DIR / "tokens.css").read_text(encoding="utf-8").replace("\r\n", "\n")
EXTRA = (CSS_DIR / "lightsout-tokens.css").read_text(encoding="utf-8")
APP = (CSS_DIR / "app.css").read_text(encoding="utf-8")
MARK = "/* --- copied from jps-console below this line; do not edit --- */\n"


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), css, flags=re.S)


def block(css, selector):
    css = strip_comments(css)
    start = css.index(selector)
    body = css[css.index("{", start) + 1:css.index("}", start)]
    return dict(re.findall(r"--([\w-]+):\s*([^;]+);", body))


def test_the_shared_tokens_are_an_unedited_copy():
    head, _, body = TOKENS.partition(MARK)
    assert body, "tokens.css must be written by scripts/sync_tokens.py"
    recorded = re.search(r"SHA-256 of the source file: ([0-9a-f]{64})", head).group(1)
    assert re.search(r"Commit: [0-9a-f]{40}", head), "the header names the source commit"
    original = body.replace('url("../fonts/', 'url("fonts/')
    assert hashlib.sha256(original.encode("utf-8")).hexdigest() == recorded, \
        "tokens.css was edited by hand; change jps-console and run scripts/sync_tokens.py"


def test_the_shared_fonts_resolve_here():
    for ref in re.findall(r'url\("([^"]+)"\)', TOKENS):
        assert (CSS_DIR / ref).resolve().is_file(), ref


DARK = block(TOKENS, ":root {")
LIGHT = {**DARK, **block(TOKENS, ':root[data-theme="light"] {')}
NIGHT = {**DARK, **block(EXTRA, ':root[data-theme="night"] {')}
THEMES = pytest.mark.parametrize("name,t", [("dark", DARK), ("light", LIGHT), ("night", NIGHT)],
                                 ids=["dark", "light", "night"])


def test_night_defines_every_color_the_shared_themes_do():
    shared = {k for k, v in block(TOKENS, ':root[data-theme="light"] {').items() if v.startswith("#")}
    night = {k for k, v in block(EXTRA, ':root[data-theme="night"] {').items() if v.startswith("#")}
    assert shared - night == set()


def luminance(hex_color):
    def channel(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    h = hex_color.strip().lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def ratio(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@THEMES
@pytest.mark.parametrize("ground", ["bg", "surface", "surface-2"])
def test_text_contrast_meets_the_design_floor(name, t, ground):
    """DESIGN.md: 7:1 for body text and 4.5:1 for everything else. Night (red) is dim on purpose
    to keep night vision, so its body text has the 4.5:1 floor."""
    body_floor = 4.5 if name == "night" else 7
    assert ratio(t["text"], t[ground]) >= body_floor
    for ink in ("muted", "accent", "high", "ok"):
        assert ratio(t[ink], t[ground]) >= 4.5, ink


@THEMES
def test_buttons_status_boxes_and_focus(name, t):
    assert ratio(t["on-accent"], t["accent"]) >= 4.5
    assert ratio(t["high"], t["high-bg"]) >= 4.5
    assert ratio(t["ok"], t["ok-bg"]) >= 4.5
    for ui in ("line-strong", "focus", "mark-bad", "mark-good"):
        assert ratio(t[ui], t["surface"]) >= 3, ui


COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(", re.I)


def declarations(css):
    css = strip_comments(css)
    for m in re.finditer(r"([\w-]+)\s*:\s*([^;{}]+)(?=[;}])", css):
        yield css.count("\n", 0, m.start()) + 1, m.group(1).lower(), m.group(2).strip()


def test_app_css_uses_tokens_only():
    found = []
    for line, prop, value in declarations(APP):
        where = f"app.css:{line} {prop}: {value}"
        if prop.startswith("--"):
            found.append(f"{where} (tokens live in tokens.css or lightsout-tokens.css)")
        if COLOR.search(value) or "transparent" in value:
            found.append(f"{where} (a raw color; use a token)")
        if prop == "border-radius" and not re.fullmatch(r"(0|var\(--r-[\w-]+\))(\s+(0|var\(--r-[\w-]+\)))*", value):
            found.append(f"{where} (radius must be 0 or a --r- token)")
        if prop == "font-size" and not re.fullmatch(r"var\(--fs-[\w-]+\)|inherit|[\d.]+em", value):
            found.append(f"{where} (font-size must be an --fs- token)")
        if prop == "box-shadow" and value != "none":
            found.append(f"{where} (nothing casts a shadow)")
    if "@font-face" in APP:
        found.append("app.css: @font-face belongs in tokens.css")
    assert found == []


@pytest.mark.parametrize("name,css", [("app.css", APP), ("lightsout-tokens.css", EXTRA)])
def test_nothing_banned(name, css):
    for rule in (r"gradient\(", r"backdrop-filter|blur\(", r"text-shadow", r"url\("):
        assert not re.search(rule, strip_comments(css), re.I), (name, rule)


def test_lightsout_tokens_only_define_tokens():
    for line, prop, value in declarations(EXTRA):
        assert prop.startswith("--") or prop == "color-scheme", f"lightsout-tokens.css:{line} {prop}"


def test_every_page_loads_the_tokens_before_its_own_styles():
    for page in sorted((ROOT / "site").glob("*.html")):
        head = page.read_text(encoding="utf-8").split("</head>")[0]
        order = [head.index(f'href="/css/{n}"') for n in ("tokens.css", "lightsout-tokens.css", "app.css")]
        assert order == sorted(order), page.name
