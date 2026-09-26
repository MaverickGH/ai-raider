# Self-host AI-Raider (your own key, any LLM)

[Русский](SELF-HOST.ru.md) · **English**

AI-Raider is a fully self-hosted tool: it runs on your machine, in its own Docker
sandbox, with **your** model and **your** key. No sign-up and no server of ours is
needed. Data never leaves your machine (and with a local model it never leaves your
computer at all).

> **Authorized testing only.** Only scan your own systems or targets you have written
> permission to test.

## What you need

- **Docker** — the sandbox the agents run in. [How to install](https://docs.docker.com/get-docker/)
- **Python 3.12+**
- **A model**: a key for any provider (OpenAI, Anthropic, Google Gemini, OpenRouter,
  etc.) **or** a local model via Ollama — no key, no data leaving your machine.

## One-step install

```bash
git clone https://github.com/MaverickGH/ai-raider && cd ai-raider
./setup.sh
```

`setup.sh` checks Docker and Python, installs the tool into `.venv`, and creates `.env`
from the template. All that is left is to fill in your model and key.

<details>
<summary>Manual, without setup.sh</summary>

```bash
uv venv && uv pip install -e .      # or: python3 -m venv .venv && ./.venv/bin/pip install -e .
cp env.example .env
```
</details>

## Choosing a model — any LLM

Open `.env` and uncomment **one** provider block (remove the `#`):

| Provider | In `.env` |
|---|---|
| OpenAI | `AIRAIDER_LLM=openai/gpt-5.4` + `OPENAI_API_KEY=…` |
| Anthropic (Claude) | `AIRAIDER_LLM=anthropic/claude-sonnet-5` + `ANTHROPIC_API_KEY=…` |
| Google Gemini (has a free tier) | `AIRAIDER_LLM=gemini/gemini-2.5-pro` + `GEMINI_API_KEY=…` |
| OpenRouter (many models, one key) | `AIRAIDER_LLM=openrouter/z-ai/glm-5.3` + `OPENROUTER_API_KEY=…` |
| Local (Ollama), no key | `AIRAIDER_LLM=ollama/qwen2.5:32b` + `LLM_API_BASE=http://localhost:11434` |
| Any OpenAI-compatible (LM Studio, vLLM, gateway) | `AIRAIDER_LLM=openai/<model>` + `LLM_API_KEY=…` + `LLM_API_BASE=…` |

The model is any [LiteLLM](https://docs.litellm.ai/docs/providers) id. Your key and your
model budget stay under your control, not ours.

> **A note on cost.** The agent loop makes hundreds of model calls. Free tiers (e.g. the
> Gemini limit) hit their quota quickly. A completed scan needs a model with a real
> limit, or a local Ollama.

## Running a scan

Only against your own / authorized target:

```bash
./run-scan.sh https://your-staging quick        # cloud model from .env
./run-scan-local.sh https://your-staging        # local model (Ollama)
```

Modes: `quick` (minutes), `standard`, `deep` (can run for hours — run it in the
background). The target is a URL, domain, IP, or a path to code (`./`).

## Results

Everything is written to `ai-raider_runs/<run-name>/`:

| File | What |
|---|---|
| `penetration_test_report.md` | The report — read this first |
| `vulnerabilities/*.md` | One file per finding: PoC and how to fix |
| `vulnerabilities.json` / `.csv` | Findings, structured |
| `findings.sarif` | SARIF 2.1.0 for GitHub code scanning |

View them in the browser with `ai-raider view`.

> Report template labels are English by default. For Russian labels, add
> `--report-lang ru` (or set `AIRAIDER_REPORT_LANG=ru`). Model-produced content is left
> as-is either way. A Russian **PDF** (`ai-raider view` export) needs a Cyrillic system
> font (DejaVu Sans, or Arial); without one the PDF labels fall back to English.

## Local, with no data leaving your machine

If data must not leave the machine — use a model via Ollama:

```bash
ollama serve
ollama pull qwen2.5:32b
./run-scan-local.sh ./ quick
```

No key, no cloud — the whole pipeline runs on your hardware.

## Responsibility

This is an offensive tool. By running it, you are responsible for having the right to
test the target. By default, test code and staging; treat production with care.
