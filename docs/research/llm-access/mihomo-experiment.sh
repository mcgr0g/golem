#!/usr/bin/env bash
# Эксперимент cpa.golem через mihomo → Xray (Lima). Запуск: run.sh start|test|stop. Секреты: config.yaml (0600, в local/).
set -euo pipefail
d="$(cd "$(dirname "$0")" && pwd)"
bin="/Applications/Clash Verge.app/Contents/MacOS/verge-mihomo"
case "${1:?start|test|stop}" in
  start) nohup "$bin" -d "$d" -f "$d/config.yaml" > "$d/mihomo.log" 2>&1 & echo $! > "$d/pid"; sleep 2; tail -3 "$d/mihomo.log";;
  stop) kill "$(cat "$d/pid")"; rm "$d/pid";;
  test)
    p=http://127.0.0.1:17891
    for u in "$@"; do :; done
    curl -sS -o /dev/null -w "plain /v1/models no key: %{http_code}\n" --max-time 15 -x $p http://cpa.golem:8317/v1/models
    curl -sS -o /dev/null -w "plain /v1/models key: %{http_code}\n" --max-time 15 -x $p -H "Authorization: Bearer $CPA_KEY" http://cpa.golem:8317/v1/models
    curl -sS -o /dev/null -w "plain localhost:8317: %{http_code}\n" --max-time 15 -x $p http://localhost:8317/
    ;;
esac
