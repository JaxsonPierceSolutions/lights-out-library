# Contributing

Thanks for helping. Changes are welcome as pull requests; for anything big,
open an issue first so we can agree on the shape before you build it.
By sending a pull request you agree your change is released under this
repo's MIT license.

## The rules (no exceptions)

- **Nothing classified, no CUI, nothing from a government or employer system.**
- **No books, videos, music or scans in git.** The repo holds pages,
  scripts and the manifest. Content is downloaded by each person from its
  official source. A new book goes in `manifest/content.json` with its
  source, exact size and license, read from the source's own page.
- **Nothing about a real household or place.** No addresses, stock lists,
  photos of someone's home, or maps centered on where anyone lives. Your
  own pages belong in a layer outside the repo (`docs/layers.md`).
- **No outside requests from the pages.** No CDN, web fonts, analytics or
  remote images. The browser test fails on any.
- **The server answers on 127.0.0.1 only.**
- **AI stays optional and off by default.** No DeepSeek models. Don't add a
  default model.
- **Medical text names its source.** Don't write or change a quick answer
  without the source open, and never invent a dose, time or quantity.
- **No secrets in git.**

## Making a change

1. Fork the repo and make a branch.
2. Changing a page? Read `DESIGN.md` first, then look at it at 390, 768
   and 1440 px wide, in all three themes, before you call it done.
3. Run the tests:

   ```
   pip install pytest playwright
   python -m playwright install chromium
   python -m pytest tests -q
   ```

   The library itself needs only Python; pytest and Playwright are test tools.
4. Open a pull request that says what you changed and how you tested it.
   The checks run on Windows, Linux and macOS. A maintainer reviews every
   change; changes to a medical quick answer, the manifest's licenses or the
   checks get an extra careful read.

Using Claude Code? It reads `CLAUDE.md` in this repo and follows the same rules.
