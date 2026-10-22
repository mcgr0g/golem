# Таймеры эксплуатации: DuckDNS и алерт RAM

Читать, когда: настраиваешь обновление DNS или мониторинг.

Вместо cron с подавленным выводом — systemd timers (логи в journald, ошибки видны).

- `duckdns-update.timer` (каждые 5 мин): `curl --fail --silent --show-error "https://www.duckdns.org/update?domains=<sub>&token=$TOKEN&ip="`, ответ должен быть `OK`, иначе юнит падает. Токен — в `EnvironmentFile` 0600 из sops. Нужен, пока IP VPS не статичен; для статичного IP — один раз при создании.
- `ram-alert.timer` (каждые 5 мин): `MemAvailable < 51200 kB` → уведомление (Telegram Bot API через `curl --fail`, токен в sops) и запись в journald. Порог — переменная `ram_alert_kb`.
- `health-check.timer` (опц., 5 мин): локальные пробы 7466/10000/8317 и ответ Caddy 200 на `/`; падение юнита видно в `systemctl --failed`.

Web-мониторинг (опционально) — Gatus, `decisions/0011-monitoring-gatus.md`. Таймеры выше остаются как минимальный вариант без UI.
