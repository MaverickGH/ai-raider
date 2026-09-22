#!/usr/bin/env bash
# Bridge в Cyber Galaxy: показать находки последнего прогона и, если настроено,
# запушить их прямо в приватную админку платформы (без ручной загрузки файла).
#
# Прямой пуш включается, когда задан CG_PLATFORM_URL (плюс CG_AUTH_COOKIE в
# production). Без него скрипт лишь показывает путь к файлу для ручного импорта.
#
#   CG_PLATFORM_URL   базовый URL платформы (напр. http://localhost:3000)
#   CG_AUTH_COOKIE    owner-cookie cg_auth (JWT). Не нужен при ADMIN_DEV_BYPASS=1.
#
# Флаги пробрасываются в scripts/push_findings.py (--run <каталог>, --dry-run).
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

if [ -n "${CG_PLATFORM_URL:-}" ]; then
  echo "CG_PLATFORM_URL задан — пушу находки в платформу напрямую."
  echo
  exec python3 scripts/push_findings.py "$@"
fi

echo "Прямой пуш выключен (не задан CG_PLATFORM_URL)."
echo "Варианты:"
echo "  • Автопуш: export CG_PLATFORM_URL=http://localhost:3000 (+ CG_AUTH_COOKIE в prod), затем запусти скрипт снова."
echo "  • Вручную: загрузи vulnerabilities.json в Cyber Galaxy → Админка → «Пентест-находки» → «Импорт прогона»."
