# 0001: Why this project, and its limits

**Date:** 2026-11-10 · **Decided by:** Jaxson Pierce Solutions

When the power or the internet is out, people still need simple answers:
how to stop bleeding, make water safe, keep food. This project puts a
searchable library of that material on one laptop ahead of time. The one
hard requirement: it runs on someone's laptop with no internet, given the
downloads made beforehand, in 500 GB or less.

What follows from that:

- **One laptop, one folder.** Python (standard library only) starts the
  book server and a small page server. No Docker, no web server to
  install, no database.
- **127.0.0.1 only.** A stranger's laptop on a strange network should
  expose nothing. Sharing to phones on home Wi-Fi is a later, opt-in step.
- **No content in git.** A manifest and a fetch script instead, so the
  repo is small and nobody receives a book from us.
- **Four sets, all under the limit.** 8, 34, 116 and 336 GB. The limit
  covers books, tools and the optional AI model.
- **Generic.** Nothing about any one household is in the repo. People add
  their own pages in a layer of their own (`docs/layers.md`).
- **AI optional, off, no default model.** Which models are acceptable is
  an open question, so the project doesn't choose one.

Risk: several of the most useful books are non-commercial or have no
clear license (see `docs/licenses.md`). That doesn't affect people
downloading for themselves. It does limit any plan to hand out or sell
loaded drives.
