#!/usr/bin/env bash
# Проверка туннеля через контейнер: внешний IP через прокси должен совпасть с IP VPS.
set -euo pipefail
: "${GOLEM_SSH_HOST:?задайте GOLEM_SSH_HOST (mise.local.toml)}"
port="${MIHOMO_TEST_PORT:-17890}"
via="$(curl --fail --silent --show-error --max-time 30 -x "http://127.0.0.1:$port" https://api.ipify.org 2>&1)" || { echo "через туннель не прошло: $via" >&2; exit 1; }
via_ip="$via"
echo "IP через туннель: $via_ip; IP VPS: $GOLEM_SSH_HOST"
[ "$via_ip" = "$GOLEM_SSH_HOST" ] || { echo "ПРОВАЛ: выход не через VPS" >&2; exit 1; }
echo "OK: трафик идёт через VPS"
