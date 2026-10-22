# 0011 — Мониторинг: Gatus

Статус: принято (опционально включаемая роль `gatus`).

## Контекст
Нужен веб-UI мониторинга без облака. Измерено (aarch64, Lima, 10 проверок/30 с):

| | Gatus v5.37.0 | Uptime Kuma 2.5.6 |
| :--- | :--- | :--- |
| RSS | 35 MB (cgroup 17) | 175–181 MB |
| Диск | 36 MB | ~580 MB с Node 22 |
| Конфиг | один YAML, `${ENV}` для секретов | UI/sqlite |
| Telegram | встроен | встроен |

## Решение
Gatus: бинарник собирается на Mac (`CGO_ENABLED=0`, готовых релизов нет, ADR 0009), systemd `DynamicUser`, `StateDirectory=gatus`, `MemoryMax=64M`, `web.address: 127.0.0.1:3002`. UI — только через SSH-туннель (`GOLEM_TUNNEL_FORWARDS="3002:127.0.0.1:3002"`): ни Gatus, ни Kuma не работают под путём-префиксом, отдельный поддомен нарушил бы «один домен». Проверки: `/healthz` CPA, TCP 7466/10000, ответ Caddy, срок сертификата; алерты — Telegram.
Uptime Kuma не используется: съедает бюджет 1 GB.

## Последствия
- Токен Telegram-бота попадает в journald при ошибке отправки (он в URL): ограничить доступ к журналу, при утечке перевыпустить токен. Отправка в Telegram не проверена (нет доступа из VM).
- Для netdata позже: `[cloud] enabled = no`; parent — `stream.conf` секция `[<API_KEY_UUID>]`, `allow from = <IP child>`, UI на 127.0.0.1; child — `[stream] enabled = yes`, `destination = <parent>:19999`, `api key = <UUID>`, `[web] mode = none`. Не проверено.
