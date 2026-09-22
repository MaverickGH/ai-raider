#!/usr/bin/env bash
# ПРОТОТИП. Поднять per-scan сеть песочницы + egress-gateway с default-deny allowlist.
# Требует валидации на Docker-хосте (root/NET_ADMIN на шлюзе). Не для продакшена как есть.
#
# Использование:
#   ./setup-scan-network.sh <scan_id> HOST:PORT [HOST:PORT ...]
# где HOST:PORT — разрешённые назначения (цель прогона + эндпоинт модели).
#
# Печатает имя созданной сети (передать песочнице через
# AIRAIDER_DOCKER_SANDBOX_NETWORK, вместе с AIRAIDER_SELF_SERVE=1).
set -euo pipefail

SCAN_ID="${1:?scan_id обязателен}"; shift
[ "$#" -ge 1 ] || { echo "Нужен хотя бы один HOST:PORT в allowlist." >&2; exit 2; }

NET="airaider-egress-${SCAN_ID}"
GW="airaider-gw-${SCAN_ID}"
GW_IMAGE="${AIRAIDER_GATEWAY_IMAGE:-alpine:3.20}"

# Приватные/служебные диапазоны, куда выход запрещён всегда (SSRF/пивот).
BLOCK_CIDRS=(
  169.254.0.0/16   # link-local + облачная метадата 169.254.169.254
  127.0.0.0/8 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 100.64.0.0/10
)

# 1. Резолвим и пиннингуем IP каждого разрешённого хоста (матч по IP, не hostname).
declare -a ALLOW_RULES=()
for pair in "$@"; do
  host="${pair%%:*}"; port="${pair##*:}"
  [ -n "$host" ] && [ -n "$port" ] && [ "$host" != "$port" ] || { echo "Плохой HOST:PORT: $pair" >&2; exit 2; }
  ips="$(getent ahostsv4 "$host" | awk '{print $1}' | sort -u)"
  [ -n "$ips" ] || { echo "Не резолвится: $host" >&2; exit 1; }
  for ip in $ips; do
    # Отказ, если цель указывает в приватный диапазон (внутренний ресурс/обход скоупа).
    case "$ip" in
      10.*|127.*|169.254.*|192.168.*|100.64.*) echo "Цель $host → приватный $ip: отказ." >&2; exit 1;;
      172.1[6-9].*|172.2[0-9].*|172.3[0-1].*)  echo "Цель $host → приватный $ip: отказ." >&2; exit 1;;
    esac
    ALLOW_RULES+=("${ip} ${port}")
    echo "allow: ${host} → ${ip}:${port}" >&2
  done
done

# 2. Per-scan сеть БЕЗ внешнего маршрута (--internal): песочница сама наружу не выйдет.
docker network create --internal "$NET" >/dev/null
echo "network: $NET" >&2

# 3. Шлюз: подключён к internal-сети (маршрут для песочницы) и к внешней (uplink через bridge).
#    NET_ADMIN — чтобы ставить nftables; правила живут в его namespace, песочница их не трогает.
docker run -d --name "$GW" --network "$NET" \
  --cap-add NET_ADMIN --cap-add NET_RAW \
  --sysctl net.ipv4.ip_forward=1 \
  "$GW_IMAGE" sleep infinity >/dev/null
docker network connect bridge "$GW" >/dev/null   # uplink наружу
echo "gateway: $GW" >&2

# 4. Ставим nftables: default-deny forward, allow established + allowlist по IP:port, drop приватное.
RULES="apk add --no-cache nftables >/dev/null 2>&1 || true; nft -f - <<'NFT'
table inet egress {
  chain forward {
    type filter hook forward priority 0; policy drop;
    ct state established,related accept
$(for c in "${BLOCK_CIDRS[@]}"; do echo "    ip daddr ${c} drop"; done)
$(for r in "${ALLOW_RULES[@]}"; do set -- $r; echo "    ip daddr ${1} tcp dport ${2} accept"; done)
  }
}
NFT
# NAT для uplink через внешний интерфейс шлюза
iptables -t nat -A POSTROUTING -o eth1 -j MASQUERADE 2>/dev/null || true"
docker exec "$GW" sh -c "$RULES"

# 5. Имя сети — на stdout (для AIRAIDER_DOCKER_SANDBOX_NETWORK).
echo "$NET"
