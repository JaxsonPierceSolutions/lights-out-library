"""Add-on layers: your own pages and home-page cards on top of the library, kept in a folder of
your own instead of in this repo.

A layer is a folder with a ``layer.json`` and, optionally, a ``site/`` folder:

    my-layer/
      layer.json      name, home-page cards, word changes (all optional)
      site/           extra pages and files; a file here with the same path as one in the
                      library's site/ replaces it

Several layers can be stacked. Later layers win: their files replace earlier ones, their name
replaces the earlier name, and their cards are added after the earlier cards (a card with
the same "id" as an earlier one replaces it in place). See docs/layers.md.

Used by both the local server (server.py) and the static build (build.py), so a layer looks the
same either way.
"""
import html
import json
import re
from pathlib import Path

DEFAULT_NAME = "Lights Out Library"
ICON_NAMES = ("home", "bolt", "check", "chat", "books", "info", "box", "map", "leaf", "anchor",
              "music", "film", "folder", "power", "drop", "wrench", "heart", "print")


class LayerError(ValueError):
    """A layer is set up wrong; the message is written for the person running the library."""


def _href(href, where):
    """Links may be paths on this site, #anchors, or http(s) addresses. Nothing that runs code."""
    href = str(href).strip()
    plain = re.sub(r"[\x00-\x20]", "", href).lower()  # browsers ignore tabs and newlines in a scheme
    scheme = re.match(r"([a-z][a-z0-9+.-]*):", plain)
    if scheme and scheme.group(1) not in ("http", "https"):
        raise LayerError("%s: links must be paths on this site or http(s) addresses, not %r. Links can't run scripts." % (where, scheme.group(1)))
    return href


def _card(c, where):
    if not isinstance(c, dict) or not c.get("title") or not c.get("href"):
        raise LayerError("%s: every card needs a \"title\" and an \"href\"." % where)
    href = _href(c["href"], where)
    icon = c.get("icon", "info")
    if icon not in ICON_NAMES:
        raise LayerError("%s: unknown icon %r. Use one of: %s." % (where, icon, ", ".join(ICON_NAMES)))
    return {"title": str(c["title"]), "blurb": str(c.get("blurb", "")), "href": href, "icon": icon,
            "id": str(c.get("id", "")), "wide": bool(c.get("wide", False))}


def load(paths):
    """Read and merge the layers in order. Returns a dict that is safe to send to the browser."""
    merged = {"name": DEFAULT_NAME, "lede": None, "section": None, "cards": [], "footer": [],
              "scripts": [], "replace": {}, "layers": [], "dirs": []}
    for p in paths or []:
        p = Path(p).resolve()
        meta = p / "layer.json"
        if not meta.is_file():
            raise LayerError("%s is not a layer: it has no layer.json." % p)
        try:
            data = json.loads(meta.read_text(encoding="utf-8-sig"))
        except ValueError as e:
            raise LayerError("%s is not valid JSON (%s)." % (meta, e))
        if not isinstance(data, dict):
            raise LayerError("%s must contain a JSON object." % meta)
        for key in ("name", "lede", "section"):
            if data.get(key):
                merged[key] = str(data[key])
        for c in data.get("cards", []):
            c = _card(c, meta.name)
            same = [i for i, x in enumerate(merged["cards"]) if c["id"] and x["id"] == c["id"]]
            if same:
                merged["cards"][same[0]] = c   # a later layer's card with the same id replaces it in place
            else:
                merged["cards"].append(c)
        for f in data.get("footer", []):
            if not isinstance(f, dict) or not f.get("text"):
                raise LayerError("%s: every footer entry needs \"text\"." % meta)
            merged["footer"].append({"text": str(f["text"]), "href": _href(f.get("href", ""), meta.name) if f.get("href") else ""})
        for s in data.get("scripts", []):
            if not str(s).startswith("/") or "//" in str(s):
                raise LayerError("%s: scripts must be paths on this site, like /layer/home.js." % meta)
            merged["scripts"].append(str(s))
        rep = data.get("replace", {})
        if not isinstance(rep, dict):
            raise LayerError("%s: \"replace\" must be an object of {\"old words\": \"new words\"}." % meta)
        merged["replace"].update({str(k): str(v) for k, v in rep.items()})
        merged["layers"].append(str(data.get("id") or p.name))
        merged["dirs"].append(p)
    return merged


def public(layer):
    """The part of a merged layer the pages may read (no folder paths)."""
    return {k: v for k, v in layer.items() if k != "dirs"}


def find_file(layer, site_dir, parts):
    """The file to serve for a path: the last layer that has it, else the library's own site/."""
    for d in reversed(layer.get("dirs", [])):
        f = (d / "site").joinpath(*parts)
        if f.is_file() or (f / "index.html").is_file():
            return f, (d / "site").resolve()
    return Path(site_dir).joinpath(*parts), Path(site_dir).resolve()


def _esc(s):
    return html.escape(s, quote=True)


def _cards_html(layer):
    out = []
    for c in layer["cards"]:
        cid = ' id="%s"' % _esc(c["id"]) if c["id"] else ""
        cls = "card wide" if c["wide"] else "card"
        out.append('<a class="%s"%s href="%s"><span class="ic" data-ic="%s"></span><span><b>%s</b><small>%s</small></span></a>'
                   % (cls, cid, _esc(c["href"]), c["icon"], _esc(c["title"]), _esc(c["blurb"])))
    return "\n    ".join(out)


def render(text, layer, name=""):
    """Apply a layer to one HTML page: the name, the word changes and (home page) the cards."""
    if not layer or not layer.get("dirs"):
        return text
    for old, new in layer["replace"].items():
        text = text.replace(old, new)
    if layer["name"] != DEFAULT_NAME:
        text = text.replace(" · " + DEFAULT_NAME + "</title>", " · " + _esc(layer["name"]) + "</title>")
        text = text.replace("<title>" + DEFAULT_NAME + "</title>", "<title>" + _esc(layer["name"]) + "</title>")
        text = re.sub(r'(<h1 data-layer="name">)[^<]*(</h1>)', lambda m: m.group(1) + _esc(layer["name"]) + m.group(2), text)
    if layer["lede"]:
        text = re.sub(r'(<p class="lede" data-layer="lede">)[^<]*(</p>)', lambda m: m.group(1) + _esc(layer["lede"]) + m.group(2), text)
    if name == "index.html":
        if any(c["href"].split("?")[0] == "/files.html" for c in layer["cards"]):
            # The layer has its own files card, so drop the built-in one.
            text = re.sub(r'\n\s*<a class="card" href="/files.html" id="files-card" hidden>.*?</a>', "", text)
        if layer["cards"]:
            block = ('<h2>%s</h2>\n  <div class="start layer" id="layer-cards">\n    %s\n  </div>'
                     % (_esc(layer["section"] or "This home"), _cards_html(layer)))
            text = text.replace("<!--layer:cards-->", block)
        if layer["footer"]:
            items = "".join(('<a href="%s">%s</a>' % (_esc(f["href"]), _esc(f["text"]))) if f["href"]
                            else "<span>%s</span>" % _esc(f["text"]) for f in layer["footer"])
            text = text.replace("<!--layer:footer-->", items)
    if layer["scripts"]:
        tags = "".join('<script src="%s"></script>' % _esc(s) for s in layer["scripts"])
        text = text.replace("</body>", tags + "\n</body>", 1) if name == "index.html" else text
    return text
