#!/usr/bin/env bash
# Сборка sandbox-образа AI-Рейдер.
#   ./containers/build-sandbox.sh          # быстрый брендированный образ (на базе upstream)
#   ./containers/build-sandbox.sh --full   # полностью независимый образ из Kali-Dockerfile (долго)
set -euo pipefail
cd "$(dirname "$0")/.."
TAG="${TAG:-ai-raider-sandbox:0.1.0}"
if [ "${1:-}" = "--full" ]; then
  echo "Полная сборка из containers/Dockerfile (несколько ГБ, долго)…"
  docker build -f containers/Dockerfile -t "$TAG" .
else
  echo "Быстрая брендированная сборка на базе upstream-песочницы…"
  docker build -f containers/Dockerfile.airaider -t "$TAG" containers/
fi
echo "Готово: $TAG"
