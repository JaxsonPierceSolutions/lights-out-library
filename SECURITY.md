# Security

## What the library exposes

- The local server (`start`) answers on **127.0.0.1 only**, so nothing else on a network can
  reach it, and it refuses requests addressed to any other host name.
- Pages load nothing from the internet; a Content-Security-Policy header blocks it, and a test
  fails if any page tries.
- Ask (optional) talks only to an Ollama on the same computer; the settings check refuses any
  other address.
- The library has **no logins**. If you serve a build on your own network with a web server
  (`docs/layers.md`), anyone on that network can read it. Only do that on a network you trust.

## Reporting a problem

Please report security problems privately through GitHub's
**Security → Report a vulnerability** on this repository, not in a public issue.
Say what you found, how to reproduce it, and what it lets someone do. We'll reply there.
