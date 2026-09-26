# AI-Raider

[Русский](README.ru.md) · **English**

> Autonomous AI pentesting. An Apache-2.0 fork of [usestrix/strix](https://github.com/usestrix/strix), reworked to run self-hosted with any LLM.

AI-Raider is a team of autonomous AI agents that pentest like real researchers: they do recon, run code in a sandbox, find vulnerabilities and confirm them with working proof-of-concept exploits, then propose fixes.

**Authorized testing only.** Run AI-Raider strictly against your own systems or targets you have written permission to test.

**Self-host in a couple of minutes** (your own key, any LLM, nothing leaves your machine) — see **[SELF-HOST.md](SELF-HOST.md)**:

```bash
git clone https://github.com/MaverickGH/ai-raider && cd ai-raider
./setup.sh            # checks Docker/Python, installs the tool, creates .env
# put your model and key in .env (or the Ollama block — no key needed), then:
./run-scan.sh https://your-staging quick
```

## What it is

- Full pentest toolkit out of the box: recon, exploitation, validation.
- Multi-agent orchestration: teams of AI pentesters work in parallel.
- Real exploit validation, not the false positives of static scanners.
- CLI with clear findings and remediation guidance.
- Auto-fixes and reports.

## Requirements

- Python 3.12+
- Docker running (the agent sandbox)
- An LLM API key (OpenAI, Anthropic, Google, OpenRouter, etc. via LiteLLM)

## Install (from source)

```bash
uv venv && source .venv/bin/activate
uv pip install -e .
ai-raider --help
```

## Quick start

```bash
export AIRAIDER_LLM="openrouter/z-ai/glm-5.3"   # any LiteLLM model id
export LLM_API_KEY="<your key>"

# headless run against an authorized target:
ai-raider -n -t ./path-to-app --scan-mode quick
```

> The interactive TUI needs a Go toolchain to build; headless mode works without it.

## Differences from upstream (Strix)

- Rebranded to "AI-Raider", CLI command `ai-raider`, config dir `~/.ai-raider`.
- Telemetry off by default; cloud upsell removed from prompts.
- **Bilingual reports**: report template labels/headers are English by default or Russian via `--report-lang ru` (or `AIRAIDER_REPORT_LANG`); model-produced content is left as-is.
- **Own sandbox image** `ai-raider-sandbox:0.1.0` (see `containers/build-sandbox.sh`), independent of the upstream tag at runtime.
- **Local models**: the `run-scan-local.sh` preset for Ollama/LM Studio with no cloud key.

## Quick commands

```bash
./run-scan.sh https://staging.your-domain quick     # cloud model (AIRAIDER_LLM + provider key)
./run-scan-local.sh https://staging.your-domain      # local model (Ollama), no cloud

# own sandbox image:
./containers/build-sandbox.sh          # fast branded build (on top of upstream)
./containers/build-sandbox.sh --full   # fully independent from the Kali Dockerfile (slow)
```

## Config via .env or Keychain

The simplest way is a `.env` file (cross-platform) — `run-scan.sh` and `run-scan-local.sh` pick it up automatically:

```bash
cp env.example .env   # then edit: pick one provider block, add your key (or use Ollama)
```

On macOS you can instead keep the key in the Keychain so it is never exported in plain text — `run-scan.sh` reads it automatically:

```bash
./scripts/keychain-set.sh OPENAI_API_KEY            # paste the key with hidden input
./scripts/keychain-set.sh AIRAIDER_LLM openai/gpt-5.4 # model
./run-scan.sh https://authorized-target standard      # key/model taken from Keychain
```

Supported: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `AIRAIDER_LLM`, `LLM_API_BASE` (Keychain service `ai-raider.local.<NAME>`). Key values are entered hidden and never printed.

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). Based on Strix (© Strix), with attribution preserved per the license terms.
