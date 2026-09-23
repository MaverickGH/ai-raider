#!/usr/bin/env bash
# AI-Рейдер через ЛОКАЛЬНУЮ модель (Ollama/LM Studio) — без облачного ключа и утечки данных.
# Требуется запущенный Ollama (`ollama serve`) с нужной моделью, напр.: ollama pull qwen2.5:32b
# Использование: ./run-scan-local.sh <url|путь> [quick|standard|deep]
set -euo pipefail
cd "$(dirname "$0")"
# подтянуть настройки из .env, если есть (модель/база можно задать там)
[ -f .env ] && { set -a; . ./.env; set +a; }
TARGET="${1:?Укажи цель: ./run-scan-local.sh <url|путь> [quick|standard|deep]}"
MODE="${2:-quick}"
export AIRAIDER_LLM="${AIRAIDER_LLM:-ollama/qwen2.5:32b}"
export LLM_API_BASE="${LLM_API_BASE:-http://localhost:11434}"
exec .venv/bin/ai-raider -n -t "$TARGET" --scan-mode "$MODE"
