# 4. Use the shared JPS design tokens

Date: 2026-11-14. Status: proposed (maintainers to review the look).

## Decision

Lights Out takes its colors, type sizes, spacing, corners and focus from the shared Jaxson Pierce
Solutions design tokens, the file the JPS Console uses (`src/jps_console/static/tokens.css`,
modeled on IBM Carbon). The file is copied in unchanged by `scripts/sync_tokens.py`, with a
header naming the source commit, and a test fails if the copy is edited. What Lights Out needs and
the shared set lacks lives in `site/css/lightsout-tokens.css`, listed as gaps (DESIGN.md).

## Why

Three copies of this library were built in November 2026 and their looks drifted apart. One
tokens file shared across JPS projects, with a test that stops hand edits, keeps them together.

## What changes for readers

- Dark is the shared near-black and cyan; "Day" becomes the shared Light theme (Carbon g10).
  The amber accent is gone; the photographs keep their warm light.
- Corners are 2 px with the shared cut corner, surfaces are flat and opaque, and the home page's
  words sit on a panel under the photograph instead of on it.
- Night (red), the 17 px body text and the 48 px targets stay, as Lights Out additions.

## What would change this

If the Console adds a reading scale, larger targets or a red night theme, the matching lines in
`lightsout-tokens.css` move there and are dropped here.
