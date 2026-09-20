#!/usr/bin/env bash
# Bridge в Cyber Galaxy: показать находки последнего прогона AI-Рейдера для импорта.
# Импорт делается в приватной админке платформы: /admin/pentest → «Импорт прогона».
set -euo pipefail
cd "$(dirname "$0")/.."
RUNS="ai-raider_runs"
[ -d "$RUNS" ] || { echo "Нет каталога $RUNS — сначала запусти скан (./run-scan.sh …)."; exit 1; }
LATEST="$(ls -1dt "$RUNS"/*/ 2>/dev/null | head -1 || true)"
[ -n "${LATEST:-}" ] || { echo "Прогонов не найдено."; exit 1; }
echo "Последний прогон: $LATEST"
echo "  находки: ${LATEST}vulnerabilities.json"
echo "  отчёт:   ${LATEST}penetration_test_report.md"
echo
echo "Загрузи vulnerabilities.json в Cyber Galaxy: Админка → «Пентест-находки» → «Импорт прогона»."
