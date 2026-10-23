# Роль ops_timers

systemd-таймеры (каждые `ops_timers_interval`, по умолчанию 5 мин) вместо cron: `duckdns-update` (только при заданных `duckdns_token` и `duckdns_subdomain`), `ram-alert` (порог `ram_alert_kb`, Telegram при заданных токене и чате, повтор не шлётся до восстановления) и `health-check` (`ops_timers_health_check_enabled`). Токены лежат в `/etc/golem/*.env` с правами 0600, в процессах не видны (curl читает URL со stdin). Описание: `docs/components/ops-timers.md`.
