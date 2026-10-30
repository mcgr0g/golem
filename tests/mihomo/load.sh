#!/usr/bin/env bash
# Нагрузка через локальный прокси: N параллельных скачиваний × R раундов + 20 коротких запросов за раунд.
# Прокси — MIHOMO_TEST_PORT (по умолчанию 17890). Кому-то отвечает 429 сам speed.cloudflare.com при больших N.
set -u
N=${N:-8}; R=${R:-3}; BYTES=${BYTES:-50000000}   # speed.cloudflare.com отдаёт 403 на 100 МБ
p="http://127.0.0.1:${MIHOMO_TEST_PORT:-17890}"
for r in $(seq "$R"); do
  for i in $(seq "$N"); do
    curl -s -x "$p" --max-time 120 -o /dev/null -w "r$r s$i %{http_code} %{size_download} %{speed_download}\n" "https://speed.cloudflare.com/__down?bytes=$BYTES" &
  done
  for _ in $(seq 20); do curl -s -x "$p" --max-time 20 -o /dev/null -w "short %{http_code}\n" https://www.cloudflare.com/cdn-cgi/trace & done
  wait
done
