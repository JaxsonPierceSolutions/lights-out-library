# Design: Lights Out Library

Read this before changing any page in `site/`. The `site-polish` loop
(screenshots at 390, 768 and 1440 px, critique, fix, repeat) checks pages
against it.

## Who uses it, and where

Someone whose power or internet is out. They are probably holding a phone or
sitting at a laptop in a dark room, maybe tired, maybe scared, maybe with a
hurt person next to them. They are not browsing. They want one answer, fast,
and they want to trust it.

Everything below follows from that.

## The idea: a lantern on a workbench

A warm light in a dark room. Dark, quiet, flat surfaces; one signal color
(the shared JPS accent) marks the thing to press; photographs lit low and warm
from one side. Calm and capable, like a well-kept field manual. Not tactical,
not doomsday, not a dashboard.

## The look comes from the shared JPS tokens

Colors, type sizes, spacing, corners and focus come from the shared Jaxson
Pierce Solutions design tokens, the same file the JPS Console uses (modeled
on IBM Carbon). Lights Out doesn't keep its own copy of the look:

- `site/css/tokens.css` is copied from the Console by
  `scripts/sync_tokens.py` and never edited by hand. Its header names the
  source commit; `tests/test_tokens.py` fails if it was changed.
- `site/css/lightsout-tokens.css` holds only what the shared set lacks (see
  "Gaps" below). Each item is something to raise with the Console so it can
  move into the shared file.
- `site/css/app.css` writes no raw color, font size or radius. It uses
  `var(--...)` only, and `tests/test_tokens.py` checks every line.

## Rules that don't bend

1. **No outside requests, ever.** No CDN, no web fonts, no analytics, no
   remote images. Fonts, icons and pictures ship in this repo. A browser test
   fails on any request that leaves `127.0.0.1`.
2. **Dark by default.** The page opens dark even if the device is set to
   light. Light and Night (red) are choices the reader makes.
3. **Readable at arm's length in the dark.** Body text 17 px or larger, line
   height 1.5 or more. Contrast at least 7:1 for body text and 4.5:1 for
   everything else, in Dark and Light; Night keeps 4.5:1 for body text, as it is dim on purpose.
4. **Thumb-sized targets.** Anything you can press is at least 48 px tall.
5. **The search box is the most prominent thing on the home page.** Then the
   quick answers. Then the shelves.
6. **Safety text is never decoration.** A warning is plain words in a plain
   box. No red unless something can hurt you.
7. **Works with JavaScript slow or failing.** Links are real links. The page
   says so plainly when the book server isn't answering.

## Themes

Set by `data-theme` on `<html>`; the choice is kept in `localStorage`.

| Theme | Where it comes from | What it is |
|---|---|---|
| Dark (default) | shared tokens, `:root` | Near-black canvas, opaque panels, cyan signal |
| Light | shared tokens, `[data-theme="light"]` | IBM Carbon g10 grays, blue signal. Paper always prints in Light. |
| Night (red) | `lightsout-tokens.css` | Black ground, dim red text, pictures turned to dim red-grey. Nothing white is on screen. |

A reader who picked "Day" before the shared tokens gets Light.

Token names are the shared ones: `--bg`, `--surface`, `--surface-2`,
`--surface-3`, `--line`, `--line-strong`, `--text`, `--muted`, `--accent`,
`--on-accent`, `--accent-soft`, `--accent-line`, `--focus`, and the status
sets `--high`/`--high-bg`/`--high-line`, `--ok`/`--ok-bg`/`--ok-line` and the
`--mark-*` colors. Older names (`--accent-ink`, `--danger`, `--img`,
`--shade`) still work for add-on layers written before the change.

## Gaps: what Lights Out adds to the shared tokens

| Token | Value | Why the shared set doesn't cover it |
|---|---|---|
| `--fs-read` | 17 px | Body text read at arm's length; the shared body sizes are 14 and 16 px |
| `--fs-title` | 40 px | Page title from 768 px; the shared largest heading is 28 px |
| `--touch-h` | 48 px | Thumb-sized targets; the shared control height is 32 px |
| `--control-h-lg` | 56 px | The search box and its button |
| `--sp-7` | 48 px | One spacing step past the shared 32 px |
| `--read-max` | 1080 px | A reading column; the shared page width is 1600 px |
| `--img-filter` | none (Night: dim red-grey) | Pictures in Night |
| Night theme | red set | The shared set has Dark and Light only |

## Type

- **Geist** for everything, **Geist Mono** for sizes, counts, file names and
  section labels (shared `--sans` and `--mono`). Both are in `site/fonts/`
  under the SIL Open Font License, the same files the Console ships.
- Sizes, all tokens: page title `--fs-xl` (28 px), `--fs-title` (40 px) from
  768 px; body `--fs-read` (17 px); search and answer headings `--fs-lg`
  (20 px); snippets and chips `--fs-md` (16 px); labels and small text
  `--fs-base` (14 px). Nothing smaller than 14 px, so the shared `--fs-sm`
  and `--fs-xs` aren't used.
- Weights: shared `--w-body` for body, 600 for links and tile names, 700 for
  titles.

## Layout

- One column, max width `--read-max`, `--sp-4` side padding on phones,
  `--sp-5` from 768 px.
- Spacing steps: the shared `--sp-1` to `--sp-6` (4 to 32 px) and `--sp-7`.
- Corners: the shared `--r-sm` / `--r-md` (2 px) on everything, and the
  shared cut corner (`--cut`) on cards, tiles, quick answers and the hero.
- Flat and opaque: no gradients, no blur, no shadows, no text on a picture.
  Elevation is a 1 px line and a step in surface color.
- Shelf grid: 2 columns on phones, 3 from 640 px.
- A sticky top bar on every page except Home: back to Home, page name, theme button.

## Parts

- **Hero (home only).** The photograph as a band across the top, then the
  name, one line of what it is and the search box on an opaque panel under
  it. The theme button sits on its own panel at the top right.
- **Search box.** 56 px tall, `--fs-lg` text, accent button. Focus is a 2 px
  `--focus` line.
- **Chips.** Common questions as one-tap searches. 44 px tall, wrap on phones.
- **Shelf tile.** Picture on top (3:2), name, one line of what's inside. The
  whole tile is the link. A shelf with no books loaded yet is shown dimmed
  with "Not loaded".
- **Quick answer card.** `--accent-line` border with a 2 px accent rail on
  the left, label "Quick answer", the question as a heading, steps as a
  list, then the source in small text.
- **Result row.** Title, two lines of snippet, the book it came from.
- **Notice.** A plain bordered box for things like "No books loaded yet".
- **Danger box.** The shared "high" status colors with a red rail and its
  label, used only for things that can hurt you.

## Pictures

- Made with a local image generator (FLUX.1 Schnell), never stock and never drawn by hand
  as a stand-in. Each picture's prompt is kept beside it in `art/` as a
  `.json` sidecar.
- One look for all of them: real objects on a table or bench, lit by a
  lantern or a low window, dark background, shallow depth, no people's faces,
  **no words, labels, logos or numbers in the picture**.
- Stored as JPEG, at most 1600 px wide for the hero and 720 px for tiles, so
  the whole `site/img/` folder stays under 2 MB.
- Every picture has `alt=""` when it's decoration (tiles, hero) and real alt
  text when it carries meaning.
- In Night (red) the pictures are greyscale and dimmed by CSS.

## Icons

Inline SVG, 24 px grid, 1.8 px stroke, round caps, drawn in `site/js/app.js`.
No icon fonts.

## Words

- Plain words, short sentences, no jargon. Say "book server", not "kiwix-serve".
- Say what a thing is and what to do. "No books loaded yet. Run the fetch
  script while you still have internet."
- Never promise more than is true. Quick answers name their source. The AI
  page says it can be wrong.

## Banned

- Any request to another host (fonts, scripts, images, maps, trackers).
- Pure white backgrounds in the Dark or Night themes.
- Text over a picture. Gradients, blur, glows and shadows.
- Raw colors, font sizes or radii in `app.css` (use a token).
- Light grey text on dark grey below the contrast floor.
- Skulls, gas masks, weapons, camouflage, biohazard signs, flames-as-decoration.
- Emoji as icons.
- Carousels, auto-playing anything, pop-ups, toasts that vanish.
- Anything about a particular household, place or person.
