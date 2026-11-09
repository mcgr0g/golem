#!/usr/bin/env bash
# Проверка NaïveProxy автономным клиентом naive: naive (SOCKS5) -> сервер -> curl к внешним сайтам.
# Использование: tests/naive/test-naive.sh <хост из inventories>
#   Ссылка и учётные данные берутся из clients/generated/<хост>/v2rayn-naive.txt (создаёт роль client_artifacts при GOLEM_NAIVE_ENABLED=true).
# Переменные: NAIVE_BIN (путь к naive; по умолчанию `naive` из PATH, релизы: https://github.com/klzgrad/naiveproxy/releases), SOCKS_PORT (11080).
# Ограничения: для хоста с tls_mode=internal (Lima) сертификат клиентом не принимается, проверять через curl --proxy-insecure.
# Включённый TUN (mihomo) отправляет трафик к серверу через цепочку: это не проверка прямого пути (docs/clients/fallbacks.md).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
host="${1:-}"
[ -n "$host" ] || { echo "использование: $0 <хост из inventories>" >&2; exit 2; }

link_file="$root/clients/generated/$host/v2rayn-naive.txt"
[ -f "$link_file" ] || { echo "нет $link_file: включите GOLEM_NAIVE_ENABLED=true и прогоните --tags client_artifacts" >&2; exit 2; }

naive_bin="${NAIVE_BIN:-naive}"
command -v "$naive_bin" >/dev/null || { echo "не найден '$naive_bin' (задайте NAIVE_BIN)" >&2; exit 2; }
socks_port="${SOCKS_PORT:-11080}"

# naive+https://user:pass@host:port?...#name -> https://user:pass@host:port
proxy="$(head -n1 "$link_file" | sed -E 's#^naive\+##; s#[?\#].*$##')"

"$naive_bin" --listen="socks://127.0.0.1:$socks_port" --proxy="$proxy" --log &
naive_pid=$!
# naive мог завершиться сам (ошибка запуска): его код возврата не должен подменять результат проверок
trap 'kill "$naive_pid" 2>/dev/null; wait "$naive_pid" 2>/dev/null; true' EXIT
sleep 2

fail=0
check() { # имя url
  local name="$1" url="$2" out
  if out="$(curl -sS --max-time 20 --socks5-hostname "127.0.0.1:$socks_port" "$url" 2>&1)"; then
    echo "OK   $name: $(printf '%s' "$out" | head -c 80 | tr '\n' ' ')"
  else
    echo "FAIL $name: $out"
    fail=1
  fi
}
echo "== $host через naive (SOCKS5 127.0.0.1:$socks_port) =="
check "внешний IP (2ip.io)" https://2ip.io/
check "HTTP" http://httpbin.org/ip
check "HTTPS" https://httpbin.org/ip
exit "$fail"
