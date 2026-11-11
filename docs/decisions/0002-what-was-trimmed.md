# 0002: What is left out, and why

**Date:** 2026-11-10 · **Decided by:** Jaxson Pierce Solutions

| Left out | Why |
|---|---|
| Stock lists, photos, equipment notes, a family's own home page | Personal. They belong in a private layer (`docs/layers.md`). |
| Regional street maps, nautical charts, a local plants page | They depend on where you live. A build-your-own-region map is on the roadmap. Plant pages also need an expert's check. |
| Movies and music | Personal files. People add their own on the Your own files page. |
| TruePrepper, Low-Tech Magazine | License not confirmed. Low-Tech's mixed languages also break search across books. |
| Old medical books (Gutenberg class R) | Outdated treatments, easy to mistake for advice. |
| Video sets, Wikipedia with pictures | Kept as opt-in extras, outside the four sets. The videos have no confirmed license and search can't read them. |

Kept, but pushed to the largest set: the 220 GB scanned-book collection.
Search can only match its titles, so it is a shelf to browse, not
something the search box or the AI can read. It is two thirds of the
Archive set's size.

Added: an About page that shows every book's size and license, a red
Night theme, pictures, a first-run message when no books are loaded, a
Host-header check on the server, and a size limit in the fetch script.
