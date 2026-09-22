#!/usr/bin/env bash
# AI-Рейдер — запуск автономного скана ТОЛЬКО по разрешённой цели (свой сайт/стенд).
# Использование: ./run-scan.sh <url|путь> [quick|standard|deep]
set -euo pipefail
cd "$(dirname "$0")"
# подтянуть ключ/модель из Keychain, если не заданы в окружении
[ -f scripts/keychain-env.sh ] && . scripts/keychain-env.sh
TARGET="${1:?Укажи цель: ./run-scan.sh <url|путь> [quick|standard|deep]}"
MODE="${2:-quick}"
if [ -z "${AIRAIDER_LLM:-}${AIRAIDER_LLM:-}" ]; then
  echo "Задай модель: ./scripts/keychain-set.sh AIRAIDER_LLM openai/gpt-5.4  (или export AIRAIDER_LLM=…)"; exit 1
fi
# Ключ провайдера берётся из окружения (напр. ANTHROPIC_API_KEY) — в скрипт не зашит.
exec .venv/bin/ai-raider -n -t "$TARGET" --scan-mode "$MODE"
