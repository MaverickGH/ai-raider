# Security Policy

## Reporting a vulnerability in AI-Raider

If you find a security issue **in AI-Raider itself** (the tool, its sandbox, or this
repository — not in a target you scanned), please report it privately:

- Open a [private security advisory](https://github.com/MaverickGH/ai-raider/security/advisories/new) on GitHub, **or**
- email the maintainers (see `NOTICE`).

Please do **not** open a public issue for a security vulnerability. Include steps to
reproduce, affected version/commit, and impact. We aim to acknowledge within a few days
and will credit reporters who want it.

## Supported versions

This is an evolving project; security fixes land on `main`. Run a recent commit or
release.

## Scope and responsible use

AI-Raider is an **offensive security tool**. By running it you are responsible for having
authorization to test the target:

- Only scan systems you own or have **written permission** to test.
- Default to code and staging; treat production with care.
- The sandbox runs arbitrary code and network requests against the target — keep it on a
  host you control.

Reports about using AI-Raider against third-party systems without authorization are out
of scope and are not a vulnerability in the tool.
