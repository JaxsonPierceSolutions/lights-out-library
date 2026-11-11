# Roadmap: Lights Out Library

## Now: first working version (Nov 2026)

- [x] Pages: home, search, quick answers, shelves, all books, old-time skills, about
- [x] One start script and one fetch script for Windows, and for Linux and macOS
- [x] Manifest with every book's source, exact size and license; four sets under 500 GB
- [x] Three themes (Dark, Day, red Night), fonts and pictures in the repo
- [x] Test that fails on any request leaving the computer
- [x] Run on Windows with real books (three small ones)
- [ ] Run the Pocket set end to end on a second Windows laptop that has never seen the project
- [ ] Run on Linux and on a Mac (scripts are written, not yet run there)
- [ ] Pick the final picture for each slot from the two in `art/`

## Open source (2026-11-10)

- [x] Public under MIT, with checks, contributor guide, security note and disclaimer ([decision 0003](docs/decisions/0003-open-source.md))

## Next

- [x] "Your own files": a folder and a page for music, films and documents people add themselves. The project ships none
- [x] Add-on layers: people's own pages and cards in a folder outside the repo ([docs/layers.md](docs/layers.md))
- [x] Static build and Ask on its own, for a home server behind nginx

- [ ] Ask: run it end to end with a real model. Try `granite3.3:8b` and `mistral:7b` on the test questions used for `llama3.1:8b`, and write down which sticks to its sources
- [ ] A nurse or doctor reads the six medical quick answers
- [ ] More quick answers: splinting, choking, hypothermia, heat illness, fever in a child (each from a named source)
- [ ] Share on your own Wi-Fi so a phone can use the laptop's library. Off by default, with a clear warning; today it answers on `127.0.0.1` only
- [ ] Build-your-own-region offline map (an OpenStreetMap extract for a box the user picks, with the viewer stored in the repo)
- [ ] "Open drive" set: only the books whose licenses allow sharing, for a drive that can be handed to someone

## Later, if people want it

- [ ] A printable one-page quick start
- [ ] Phone-only version (the Kiwix app plus these pages)
- [ ] Other languages
- [ ] An "open drive" guide: which sets can legally be copied onto a drive for someone else (read `docs/licenses.md` first)
