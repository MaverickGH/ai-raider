# AiRaider — Agent Guide

AiRaider is an open-source autonomous AI pentesting tool. This file is for AI coding agents that want to **use** AiRaider (run security scans) or **contribute** to it.

## Using AiRaider from an agent

Install the agent skills for step-by-step workflows:

```bash
npx skills add usestrix/strix
```

- `penetration-testing-with-airaider` — run a headless pentest against code, URLs, domains, or IPs and read results
- `fix-security-vulnerabilities-with-airaider` — remediate findings and re-run AiRaider to verify
- `ci-security-scanning-with-airaider` — add PR scanning to CI/CD (self-hosted CLI in your runner)

Target-specific workflows built on the same engine:

- `application-security-testing` — whole-product AppSec review: pick the right test per asset, then rank the results
- `web-app-penetration-testing` — black-box pentest of a live web app or staging site
- `api-security-testing` — REST/GraphQL APIs and the OWASP API Security Top 10 (BOLA/IDOR, authz)
- `owasp-top-10-testing` — systematic OWASP Top 10 assessment with honest per-category coverage
- `find-security-vulnerabilities-in-code` — white-box review of a repo or working tree

**Run it self-hosted with the open-source CLI:** free, fully local, BYO LLM key, needs Docker. Best for local dev loops, air-gapped/offline, and full control.
  ```bash
  git clone https://github.com/MaverickGH/ai-raider && cd ai-raider && uv pip install -e .        # install
  export AIRAIDER_LLM="openrouter/z-ai/glm-5.3"        # any LiteLLM model id
  export LLM_API_KEY="<key>"
  airaider -n -t ./ --scan-mode quick --max-budget 10  # headless scan; always use -n
  ```
  - Requires Docker running. Scans take minutes (`quick`) to hours (`deep`) — run in the background.
  - Exit codes (headless): `0` clean, `1` fatal error, `2` vulnerabilities found. A `0` only covers what was analyzed — check `run.json` (`status`, `llm_usage.cost` vs the budget) before calling a run clean.
  - Artifacts in `airaider_runs/<run-name>/`: `penetration_test_report.md`, `vulnerabilities/*.md`, `vulnerabilities.json`, `findings.sarif` (SARIF 2.1.0), `run.json`.

  - Enable tab completion with `source <(airaider completions zsh)` (or `bash`), or `airaider completions fish | source`.

- Docs: https://github.com/MaverickGH/ai-raider
- Only scan targets the user is authorized to test.

## Contributing to this repo

- Python 3.12+, managed with `uv`. Install dev deps: `make dev-install`.
- Lint/format/type-check/security, all in one: `make check-all` (ruff, mypy, bandit).
- Tests: `uv run pytest`.
- Run from source: `uv run airaider --target <target>`.
- Layout: `airaider/agents` (agent graph + prompts), `airaider/tools` (proxy, browser, terminal, scanners), `airaider/runtime` (Docker sandbox), `airaider/report` (findings, SARIF), `airaider/skills` (internal knowledge packs the pentest agents load — different from the consumer skills in `skills/`), `airaider/interface` (CLI/TUI), `containers/` (sandbox image).
- Pre-commit hooks: `make pre-commit` (or `uv run pre-commit install`).
