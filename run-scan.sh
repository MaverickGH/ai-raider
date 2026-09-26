#!/usr/bin/env bash
# AI-Raider - run an autonomous scan against an AUTHORIZED target ONLY (your own site/stand).
# Usage: ./run-scan.sh <url|path> [quick|standard|deep]
set -euo pipefail
cd "$(dirname "$0")"
# load model/key from .env (self-host), then from Keychain (macOS)
[ -f .env ] && { set -a; . ./.env; set +a; }
[ -f scripts/keychain-env.sh ] && . scripts/keychain-env.sh
TARGET="${1:?Specify a target: ./run-scan.sh <url|path> [quick|standard|deep]}"
MODE="${2:-quick}"
if [ -z "${AIRAIDER_LLM:-}" ]; then
  echo "Set a model in .env (AIRAIDER_LLM=...) or: export AIRAIDER_LLM=openai/gpt-5.4"; exit 1
fi
# The provider key is taken from the environment (e.g. ANTHROPIC_API_KEY) - not hardcoded.
exec .venv/bin/ai-raider -n -t "$TARGET" --scan-mode "$MODE"
