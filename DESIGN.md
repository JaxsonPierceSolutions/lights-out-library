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

A warm light in a dark room. Dark, quiet surfaces; one warm amber light that
marks the thing to press; photographs lit the same way (low, warm, from one
side). Calm and capable, like a well-kept field manual. Not tactical, not
doomsday, not a dashboard.

## Rules that don't bend

1. **No outside requests, ever.** No CDN, no web fonts, no analytics, no
   remote images. Fonts, icons and pictures ship in this repo. A browser test
   fails on any request that leaves `127.0.0.1`.
2. **Dark by default.** The page opens dark even if the device is set to
   light. Day and Night (red) are choices the reader makes.
3. **Readable at arm's length in the dark.** Body text 17 px or larger, line
   height 1.5 or more. Contrast at least 7:1 for body text and 4.5:1 for
   everything else, in all three themes.
4. **Thumb-sized targets.** Anything you can press is at least 48 px tall.
5. **The search box is the most prominent thing on the home page.** Then the
   quick answers. Then the shelves.
6. **Safety text is never decoration.** A warning is plain words in a plain
   box. No red unless something can hurt you.
7. **Works with JavaScript slow or failing.** Links are real links. The page
   says so plainly when the book server isn't answering.

## Themes

Set by `data-theme` on `<html>`; the choice is kept in `localStorage`.

| Token | Dark (default) | Day | Night (red) |
|---|---|---|---|
| `--bg` | `#0c0e11` | `#f3efe6` | `#050000` |
| `--surface` | `#14181d` | `#fffdf8` | `#0d0101` |
| `--surface-2` | `#1c2229` | `#ebe5d8` | `#170303` |
| `--line` | `#2a323c` | `#d5cdbd` | `#3a0a0a` |
| `--text` | `#eef1f4` | `#1a1d21` | `#ff5a4d` |
| `--muted` | `#a3b1bf` | `#515b66` | `#c23b31` |
| `--accent` | `#f2a93b` | `#955000` | `#ff3b2e` |
| `--accent-ink` | `#1b1204` | `#ffffff` | `#050000` |
| `--ok` | `#74d391` | `#1d7a3c` | `#c23b31` |
| `--danger` | `#ff7a6b` | `#b3261e` | `#ff5a4d` |

Night (red) is for keeping your night vision: black background, dim red
text, pictures turned to dim red-grey. Nothing white is on screen in that theme.

## Type

- **Geist** (variable, 400 to 700) for everything. **Geist Mono** for sizes,
  counts and file names. Both are in `site/fonts/` under the SIL Open Font
  License. System fonts are the fallback.
- Sizes: page title 30/34 px (40/44 from 768 px), section label 13 px caps
  with 0.08em tracking, body 17 px, small 14.5 px. Never smaller than 13 px.
- Weights: 400 body, 600 for links and tile names, 700 for titles. No light
  weights; thin strokes vanish on a dim screen.

## Layout

- One column, max width 1080 px, 16 px side padding on phones, 24 px from 768 px.
- Spacing steps: 4, 8, 12, 16, 24, 32, 48.
- Corners: 14 px on cards and inputs, 999 px on chips.
- Shelf grid: 2 columns on phones, 3 from 640 px, 4 from 1000 px.
- A sticky top bar on every page except Home: back to Home, page name, theme button.

## Parts

- **Hero (home only).** A wide photograph with a dark gradient over its lower
  half, the name, one line of what it is, and the search box on top. Height
  about 46% of a phone screen, 380 px on desktop.
- **Search box.** 56 px tall, 19 px text, amber button. Focus ring is a 2 px amber line.
- **Chips.** Common questions as one-tap searches. 44 px tall, wrap on phones.
- **Shelf tile.** Picture on top (3:2), name, one line of what's inside. The
  whole tile is the link. A shelf with no books loaded yet is shown dimmed
  with "Not loaded".
- **Quick answer card.** Amber border, label "Quick answer", the question as
  a heading, steps as a list, then the source in small text.
- **Result row.** Title, two lines of snippet, the book it came from.
- **Notice.** A plain bordered box for things like "No books loaded yet".
- **Danger box.** `--danger` border and label, used only for things that can hurt you.

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
- Text over a picture without the dark gradient behind it.
- Light grey text on dark grey below the contrast floor.
- Skulls, gas masks, weapons, camouflage, biohazard signs, flames-as-decoration.
- Emoji as icons.
- Carousels, auto-playing anything, pop-ups, toasts that vanish.
- Anything about a particular household, place or person.
