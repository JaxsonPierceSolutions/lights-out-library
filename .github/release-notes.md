An offline survival and reference library that runs on one laptop with no internet.

**Download** `lights-out-library-<version>.zip` below and unzip it anywhere, an external drive included.

**You need:** Python 3.9 or newer and any browser. Nothing else; the fetch script gets the book server for you.

**While you still have internet**, in the unzipped folder:

```
fetch --list            show the four sets and their sizes (Linux/macOS: ./fetch.sh --list)
fetch --tier pocket     download the smallest set (8 GB) and the book server
```

**Then, any time, with or without internet:** double-click `start.cmd` (Linux/macOS: `./start.sh`). It opens `http://127.0.0.1:8600/` in your browser.

| Set | Size | What it's for |
|---|---|---|
| Pocket | 8.2 GB | First aid, medicines, safe water, food storage, knots |
| Essentials | 33.9 GB | Adds field manuals, repair guides, an illustrated encyclopedia, gardening, off-grid power |
| Full | 115.5 GB | Adds every Wikipedia article (text), textbooks, electronics, old how-to books |
| Archive | 335.8 GB | Adds 220 GB of scanned pre-1930s books, browsed by title |

The books are downloaded from Kiwix by you and keep their own licenses (see `docs/licenses.md`). The code is MIT.

Not medical advice and no warranty. The Quick answers name their sources, but no doctor or nurse has reviewed them.
