#!/usr/bin/env bash
# Сохранить секрет/настройку AI-Рейдера в macOS Keychain.
#   ./scripts/keychain-set.sh OPENAI_API_KEY            # значение вводится СКРЫТО (для ключей)
#   ./scripts/keychain-set.sh STRIX_LLM openai/gpt-5.4  # значение строкой (для не-секретов)
set -euo pipefail
[ "$(uname -s)" = "Darwin" ] || { echo "Нужен macOS Keychain."; exit 1; }
NAME="${1:?Имя: OPENAI_API_KEY | ANTHROPIC_API_KEY | OPENROUTER_API_KEY | STRIX_LLM | LLM_API_BASE}"
ACCOUNT="${USER:-$(id -un)}"
SERVICE="ai-raider.local.$NAME"
if [ "$#" -ge 2 ]; then
  security add-generic-password -U -a "$ACCOUNT" -s "$SERVICE" -w "$2"
else
  # -w без значения → скрытый интерактивный ввод (значение не отображается)
  security add-generic-password -U -a "$ACCOUNT" -s "$SERVICE" -w
fi
echo "Сохранено в Keychain: $SERVICE"
