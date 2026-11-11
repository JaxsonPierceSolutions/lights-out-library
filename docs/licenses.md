# Licenses: what you can and can't do with the books

Researched 2026-11-10 from each source's own pages where they could be
opened. This is a working summary, not legal advice. Before selling
anything, have a lawyer read the Stack Exchange, NHS and Project Gutenberg
points.

## The short version

- **Downloading for yourself is fine for every book in the manifest.** This
  repo ships no books. Each person fetches their own copy from Kiwix, and
  each book stays under its own license.
- **Handing out or selling a loaded drive makes you the distributor.** Then
  every license applies to you, and several books can't go on that drive.

## If a loaded drive were ever given away or sold

| Group | Books | What it takes |
|---|---|---|
| **Open, with ordinary duties** | Wikipedia (all editions), Wikibooks, MDWiki, the Stack Exchange sites, Appropedia, energypedia | Credit the authors, ship the license text, keep share-alike on anything you change. Stack Exchange's 2024 dump terms try to bar commercial use, which critics say conflicts with CC BY-SA: contested. energypedia bars promotional use. |
| **Likely fine as US government works; confirm first** | Army field manuals, Ready.gov, the military medicine manuals, the USDA canning guide | No reuse statement was found on the agencies' own pages. Don't imply endorsement. |
| **Allowed, with a catch** | NHS medicines A to Z | Open Government Licence, but you may not charge for access to it, must credit the NHS with the date, and are meant to refresh it weekly, which an offline copy can't. |
| **Allowed, with a cost** | Project Gutenberg collections | Public domain in the US, but selling copies that keep the Project Gutenberg name owes them a 20% royalty. The other route is removing the name from every book. |
| **Not without written permission** | iFixit, both LibreTexts collections, WikiVet | Non-commercial licenses. |
| **Not confirmed: treat as no** | Survivor Library, CD3WD, the five Kiwix "zimgit" document collections, ScoutWiki, Gardenology, the five video sets | No clear license statement was found. |

A drive built only from the first group is the safe one to share.

## Left out of the manifest entirely

| What | Why |
|---|---|
| TruePrepper | "All rights reserved", and Kiwix's own request tracker shows the request closed for lack of permission. |
| Low-Tech Magazine | Only a copyright line was found. Its mixed languages also break search across books. |
| Movies and music | Personal copies. |

## Software, fonts and pictures

| Part | License | Note |
|---|---|---|
| kiwix-serve (book server) | GPL 3.0 or later | Downloaded by the fetch script, not stored here. |
| Geist and Geist Mono fonts | SIL Open Font License 1.1 | In `site/fonts/` with the license text. |
| Ollama (optional) | MIT | Installed by the user. |
| Llama 3.1 (optional) | Llama 3.1 Community License | Putting it on a drive for someone else needs a copy of the agreement and a "Built with Llama" notice. |
| Granite 3.3, Mistral 7B, nomic-embed-text (optional) | Apache-2.0 | |
| Pictures in `site/img/` and `art/` | Made for this project with FLUX.1 Schnell (Apache-2.0) on our own hardware | Prompts are in the `.json` file beside each. |
| This repo's own code and pages | Proprietary, see `LICENSE` | |

## Names and logos

"Kiwix", "Wikipedia", "Project Gutenberg", "NHS" and the rest are their
owners' names. The pages use them only to say where a book came from. Don't
use their logos, and don't suggest any of them endorse this project.

## Where each finding came from

The per-book license line is in `manifest/content.json` (`license`,
`redistribution`, `note`). `redistribution` is one of:

- `open`: free licenses that allow sharing and selling, with duties.
- `conditions`: allowed, with a condition that matters (NHS, Gutenberg).
- `noncommercial`: fine to download; not for sale.
- `unconfirmed`: no clear statement found. Fine to download from Kiwix for
  yourself; don't pass it on.
