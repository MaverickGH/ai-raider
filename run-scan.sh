#!/usr/bin/env bash
# AI-Рейдер — запуск автономного скана ТОЛЬКО по разрешённой цели (свой сайт/стенд).
# Использование: ./run-scan.sh <url|путь> [quick|standard|deep]
set -euo pipefail
cd "$(dirname "$0")"
# подтянуть модель/ключ из .env (самостоятельное развёртывание), затем из Keychain (macOS)
[ -f .env ] && { set -a; . ./.env; set +a; }
[ -f scripts/keychain-env.sh ] && . scripts/keychain-env.sh
TARGET="${1:?Укажи цель: ./run-scan.sh <url|путь> [quick|standard|deep]}"
MODE="${2:-quick}"
if [ -z "${AIRAIDER_LLM:-}" ]; then
  echo "Задай модель в .env (AIRAIDER_LLM=…) или: export AIRAIDER_LLM=openai/gpt-5.4"; exit 1
fi
# Ключ провайдера берётся из окружения (напр. ANTHROPIC_API_KEY) — в скрипт не зашит.
exec .venv/bin/ai-raider -n -t "$TARGET" --scan-mode "$MODE"
