#!/usr/bin/env bash
# AI-Raider via a LOCAL model (Ollama/LM Studio) - no cloud key, no data leaving your machine.
# Requires a running Ollama (`ollama serve`) with the model, e.g.: ollama pull qwen2.5:32b
# Usage: ./run-scan-local.sh <url|path> [quick|standard|deep]
set -euo pipefail
cd "$(dirname "$0")"
# load settings from .env if present (model/base can be set there)
[ -f .env ] && { set -a; . ./.env; set +a; }
TARGET="${1:?Specify a target: ./run-scan-local.sh <url|path> [quick|standard|deep]}"
MODE="${2:-quick}"
export AIRAIDER_LLM="${AIRAIDER_LLM:-ollama/qwen2.5:32b}"
export LLM_API_BASE="${LLM_API_BASE:-http://localhost:11434}"
exec .venv/bin/ai-raider -n -t "$TARGET" --scan-mode "$MODE"
