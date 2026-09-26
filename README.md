# AI-Raider

[Русский](README.ru.md) · **English**

> Autonomous AI pentesting. A fork of [usestrix/strix](https://github.com/usestrix/strix) (Apache-2.0), adapted for our needs.

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
- **Russian reports**: the markdown pentest report and vulnerability cards are in Russian (model-produced values as-is).
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

## Cyber Galaxy integration

Findings from a run can be imported into the private admin section of the Cyber Galaxy platform (the "Pentest findings" area, owners only). Two ways:

**Direct push (no manual file upload).** Set the platform URL and findings are sent automatically:

```bash
export CG_PLATFORM_URL=http://localhost:3000   # platform address
export CG_AUTH_COOKIE=<owner cg_auth cookie>   # in production; not needed in dev with ADMIN_DEV_BYPASS=1
./scripts/export-findings.sh                   # builds the payload and pushes the latest run's findings
```

Fine-grained control — directly via the bridge script:

```bash
python3 scripts/push_findings.py               # latest run
python3 scripts/push_findings.py --run <dir>   # a specific run
python3 scripts/push_findings.py --dry-run     # build and show the payload without sending
```

**Manually.** Without `CG_PLATFORM_URL` the script only prints the path to `vulnerabilities.json`; then in the admin: **Pentest findings → Import run** — upload `vulnerabilities.json` (and optionally `penetration_test_report.md`).

Findings are sensitive and never reach public content.

## Self-serve mode (letting people use it)

A separate scenario — opening autonomous pentesting to **platform users**, so each one scans only their own resources and the service is not tied to the owner account. It is an offensive tool, so two barriers are required:

1. **Target ownership verification** — the user proves the domain/repository is theirs (DNS TXT, a `/.well-known/…` file, or a file in the repository).
2. **Sandbox network scope** — the running agent physically cannot reach anything but the proven target and the model endpoint (egress default-deny outside the container, because the sandbox has `NET_ADMIN` and confining it from inside is pointless).

Full design spec (multi-tenancy without owner binding, verification, network scope, queue, cabinet, code integration points): **[SELF-SERVE-DESIGN.md](SELF-SERVE-DESIGN.md)**.

The design/contract lives here; the platform-side implementation (verification, queue, cabinet) lives in the Cyber Galaxy repo. MVP to "safely open it to people" = sandbox scope + verification + queue-worker.

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). Based on Strix (© Strix), with attribution preserved per the license terms.
