#!/usr/bin/env bash
# ПРОТОТИП. Снести per-scan шлюз и сеть, созданные setup-scan-network.sh.
# Использование: ./teardown-scan-network.sh <scan_id>
set -euo pipefail

SCAN_ID="${1:?scan_id обязателен}"
NET="airaider-egress-${SCAN_ID}"
GW="airaider-gw-${SCAN_ID}"

docker rm -f "$GW" >/dev/null 2>&1 || true
# Сеть удалится только когда от неё отключены все контейнеры (в т.ч. песочница).
docker network rm "$NET" >/dev/null 2>&1 || true
echo "снесено: $GW, $NET"
