#!/usr/bin/env bash
# Bridge to Cyber Galaxy: show the latest run's findings and, if configured, push them
# straight into the platform's private admin (no manual file upload).
#
# Direct push turns on when CG_PLATFORM_URL is set (plus CG_AUTH_COOKIE in production).
# Without it, the script only prints the file path for manual import.
#
#   CG_PLATFORM_URL   platform base URL (e.g. http://localhost:3000)
#   CG_AUTH_COOKIE    owner cg_auth cookie (JWT). Not needed with ADMIN_DEV_BYPASS=1.
#
# Flags are passed through to scripts/push_findings.py (--run <dir>, --dry-run).
set -euo pipefail
cd "$(dirname "$0")/.."
RUNS="ai-raider_runs"
[ -d "$RUNS" ] || { echo "No $RUNS directory - run a scan first (./run-scan.sh ...)."; exit 1; }
LATEST="$(ls -1dt "$RUNS"/*/ 2>/dev/null | head -1 || true)"
[ -n "${LATEST:-}" ] || { echo "No runs found."; exit 1; }

echo "Latest run: $LATEST"
echo "  findings: ${LATEST}vulnerabilities.json"
echo "  report:   ${LATEST}penetration_test_report.md"
echo

if [ -n "${CG_PLATFORM_URL:-}" ]; then
  echo "CG_PLATFORM_URL is set - pushing findings to the platform directly."
  echo
  exec python3 scripts/push_findings.py "$@"
fi

echo "Direct push is off (CG_PLATFORM_URL is not set)."
echo "Options:"
echo "  - Auto push: export CG_PLATFORM_URL=http://localhost:3000 (+ CG_AUTH_COOKIE in prod), then run again."
echo "  - Manual: upload vulnerabilities.json in Cyber Galaxy -> Admin -> 'Pentest findings' -> 'Import run'."
