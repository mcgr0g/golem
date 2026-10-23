# Роль gatus

Опциональная (`gatus_enabled: false` по умолчанию, ADR 0011): веб-UI мониторинга на `127.0.0.1:gatus_port` (3002), доступ только через SSH-туннель. Бинарник собирается на Mac (`mise run build:artifacts gatus`) и сверяется с `manifest.json`. Проверки: CPA `/healthz`, TCP Xray и relay, ответ и срок сертификата Caddy (кроме `tls_mode: internal`); алерты в Telegram при заданных токене и чате. Описание: `docs/components/ops-timers.md`.
