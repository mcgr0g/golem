# Таймеры эксплуатации: DuckDNS и алерт RAM

Читать, когда: настраиваешь обновление DNS или мониторинг.

Роль `ops_timers`. Вместо cron с подавленным выводом — systemd timers (логи в journald, ошибки видны). Скрипты — `/usr/local/lib/golem/*.sh`, службы `DynamicUser`, интервал `ops_timers_interval` (5 мин).

- `duckdns-update.timer` (каждые 5 мин): `curl --ipv4 --fail --silent --show-error "https://www.duckdns.org/update?domains=<sub>&token=$TOKEN&ip=<ipv4>&ipv6=<addr>"` (A — `GOLEM_PUBLIC_IP`, если задан, иначе адрес запроса; за NAT они могут различаться; AAAA — первый глобальный IPv6 хоста, если есть, иначе параметр пустой), ответ должен быть `OK`, иначе юнит падает. Токен — в `/etc/golem/duckdns.env` (0600, из sops), в curl передаётся через stdin (не виден в `ps`). Таймер ставится только при заданных `duckdns_token` и `duckdns_subdomain`. Нужен, пока IP VPS не статичен; для статичного IP — один раз при создании.
- `ram-alert.timer` (каждые 5 мин): `MemAvailable < 51200 kB` → запись в journald и, если заданы `telegram_bot_token`/`telegram_chat_id`, сообщение в Telegram (`curl --fail`); повтор не шлётся, пока память не восстановится (флаг в `/run/golem-ram-alert`). Порог — переменная `ram_alert_kb`.
- `health-check.timer` (`ops_timers_health_check_enabled`, по умолчанию вкл.): TCP 10000 и 7466, `/healthz` CPA, ответ Caddy на `/` (через `--resolve` на 127.0.0.1); любая неудача — юнит failed, виден в `systemctl --failed`.

Web-мониторинг (опционально) — Gatus, `decisions/0011-monitoring-gatus.md`. Таймеры выше остаются как минимальный вариант без UI.

## Gatus (роль `gatus`, `gatus_enabled: false` по умолчанию)
Бинарник собирается на Mac (`mise run build:artifacts gatus`, `GATUS_VERSION`, по умолчанию v5.37.0), сверяется с `manifest.json`. Слушает `127.0.0.1:3002` (`gatus_port`), `DynamicUser`, `MemoryMax=64M`, sqlite в `/var/lib/gatus`. Проверки: `/healthz` CPA, TCP Xray и relay, Caddy (200 + срок сертификата > 7 суток, кроме `tls_mode: internal`: домен стенда с самой VM не резолвится). Алерты Telegram — при заданных токене и чате. Токен лежит в `/etc/gatus/env` (0600).
Проверено на Lima: служба active, UI отвечает 200 на 127.0.0.1:3002, cgroup ~10 MB. Не проверено: проверка Caddy и отправка в Telegram (нужен прод).
