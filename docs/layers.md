# Add-on layers: your own pages on top of the library

The library is the same for everyone. A **layer** is where your own things go: a stock list,
a page of local plants, a map of your area, a printed sheet for your family. It lives in a
folder of your own, outside this repo, so you can keep it private and still update the library.

## What a layer is

```
my-layer/
  layer.json      the name, home-page cards and word changes (all optional)
  site/           your pages and files
```

A file in `site/` is served at the same path, so `my-layer/site/stock.html` opens at
`/stock.html`. A file with the same path as one of the library's own replaces it, so use
new names unless you mean to.

`layer.json`:

```json
{
  "name": "Our House",
  "lede": "Our family library. Works with no internet.",
  "section": "This house",
  "cards": [
    {"title": "Stock list", "blurb": "Food, water and fuel", "href": "/stock.html", "icon": "box"},
    {"id": "files", "title": "Music", "blurb": "Our own files", "href": "/files.html", "icon": "music", "wide": true}
  ],
  "footer": [{"text": "Printed sheet", "href": "/sheet.html"}],
  "replace": {"on this computer": "in this house"},
  "scripts": ["/layer/home.js"]
}
```

| Key | What it does |
|---|---|
| `name` | Replaces "Lights Out Library" on the home page and in every page title. |
| `lede` | The line under the name on the home page. |
| `section` | Heading over your cards (default "This home"). |
| `cards` | Cards on the home page, between "Start here" and the shelves. `icon` is one of `home bolt check chat books info box map leaf anchor music film folder power drop wrench heart print`. `wide` spans the row. |
| `footer` | Extra links in the home page footer. |
| `replace` | Word changes on every page, applied in order, so put longer phrases first. The new words go into the page as HTML, so only put in text you trust. |
| `scripts` | Extra scripts on the home page. Paths on this site only. |

Card and footer links can be paths on this site, `#anchors` or `http(s)` addresses; anything
else is refused. Files and folders whose names start with a dot are never served.

Your pages should look like the rest: copy the head and the top bar from `site/answers.html`,
and use the parts and colors in [DESIGN.md](../DESIGN.md): load `/css/tokens.css`, `/css/lightsout-tokens.css`
and `/css/app.css` in that order, and use the token names (`var(--surface)`, `var(--accent)`, ...) rather
than writing colors. The themes are `dark`, `light` and `night`; older layers that use `--accent-ink`,
`--danger` or `--img` keep working. Pages must not load anything from
the internet. The browser test only checks the library's own pages, so check yours the same way.

## Stacking layers

Give several, in order. Later layers win: their name and words replace earlier ones, their
cards are added after the earlier cards, and a card with the same `id` as an earlier card
replaces it. That is how one shared layer can carry a small per-machine layer on top:

```
start --layer ../our-house --layer ../our-house/machines/laptop
```

## Using one

- **On a laptop:** `start --layer DIR` (repeatable), or `"layers": ["../our-house"]` in
  `config.json` (paths are relative to the project folder).
- **On a server:** build plain files and let a web server serve them:

  ```
  python -m lightsout.build --out dist --layer ../our-house --ask-model llama3.1:8b
  ```

  [deploy/nginx.example.conf](../deploy/nginx.example.conf) shows the web server settings.
  Ask then runs on its own with `python -m lightsout.askserve` (127.0.0.1 only; the web server
  passes `/ask/api/` to it). `ask.kiwix_urls` in `config.json` can list more than one book
  server; Ask uses the first that answers.

## Your own files

Separate from layers: anything in the `files/` folder (music, films, documents) shows on the
**Your own files** page, `/files.html`, one folder per kind. On a server, point `/files/` at the
folder as a JSON listing (nginx: `autoindex on; autoindex_format json;`).
