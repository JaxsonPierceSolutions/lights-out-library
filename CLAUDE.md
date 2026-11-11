# Rules for Claude in this repo

This is an open-source project from Jaxson Pierce Solutions. Several
people work here, each with their own Claude account. Follow these rules
for everyone.

- **Never** add classified information, CUI, or anything from a real
  government or employer network. If you see any, stop and say so.
- **No third-party content in git.** No books, ZIM files, videos, music
  or scans. Content is listed in `manifest/content.json` (source, exact
  size, license) and downloaded by `fetch` from the official source.
- **Nothing about a real household, person or place.** This is the
  generic, public version. Don't copy stock lists, photos,
  addresses, equipment or regional maps into it, and don't ask for them.
- **Household details go in a layer, never here.** A real household's pages (stock lists,
  maps of their area, their media) live in a private add-on layer outside this repo
  (`docs/layers.md`). Improve the layer system here; never copy a layer's pages in.
- **Pages make no outside requests.** Fonts, icons and pictures ship in
  the repo. `tests/test_browser.py` fails on any request that leaves
  `127.0.0.1`. Never weaken that test.
- **The server binds 127.0.0.1 only.** Sharing on a network is a roadmap
  item that needs a maintainer's yes.
- **AI is optional and off by default.** No default model. No DeepSeek.
  Don't add a Chinese-origin model to the suggested list without
  a maintainer's yes.
- **`src/` uses the Python standard library only,** so a stranger needs
  nothing but Python. Test tools (pytest, Playwright) are fine in `tests/`.
- **Read `DESIGN.md` before touching `site/`.** After a page change, look
  at it at 390, 768 and 1440 px in all three themes.
- **Pictures come from a local image generator** (FLUX.1 Schnell), never drawn by hand as a
  stand-in. Keep each picture's `.json` sidecar in `art/`. Show the
  maintainers the best two for a slot; they pick.
- **Medical quick answers** change only with the named source open. Never
  invent a dose, time or quantity. Say plainly that no clinician has
  reviewed them until one has.
- **Green checks are the bar for merging.** Never weaken or skip a check.
- **No secrets** in git.
- Keep `README.md`, `ROADMAP.md`, `docs/licenses.md` and
  `docs/decisions/` current when the plan changes. Write for a reader
  who is new to the project.
