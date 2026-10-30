# Проверка туннеля через mihomo в Docker

Читать, когда: нужно проверить реальный трафик через VPS, не трогая clash-verge-rev на хосте.

Каталог `tests/mihomo/`: `compose.yaml` (образ `metacubex/mihomo`, версия закреплена), `base.yaml` (общая часть), `render.sh` (собирает `config.yaml` из `clients/generated/<host>/mihomo-node.yaml`; файл с секретами, 0600, в `.gitignore`), `check.sh` (внешний IP через прокси должен совпасть с `GOLEM_SSH_HOST`).

```
tests/mihomo/render.sh <host>            # host — имя из инвентори, например golem-dev
docker compose -f tests/mihomo/compose.yaml up -d
mise exec -- tests/mihomo/check.sh       # GOLEM_SSH_HOST берётся из mise.local.toml
docker compose -f tests/mihomo/compose.yaml down
```

Прокси слушает `127.0.0.1:17890` (меняется `MIHOMO_TEST_PORT`), чтобы не пересекаться с портом clash-verge-rev. Нужен запущенный Docker Desktop.

Проверено на stage (golem-dev, боевой Let's Encrypt): IP через туннель = IP VPS; 25 МБ через туннель ~8 МБ/с; пик RAM после этого: xray 11 МБ, caddy 26 МБ. Не проверено: UDP (в профиле `udp: false`), долгие сессии, мобильные сети.

## Нагрузка и лимиты памяти (Q8)
`tests/mihomo/load.sh` (`N` потоков × `R` раундов по `BYTES`, плюс короткие запросы). Пики памяти сервисов — `memory.peak` в cgroup (`/sys/fs/cgroup/system.slice/<юнит>.service/`, ядро ≥ 5.19), события лимитов — `memory.events` (`high`, `max`, `oom_kill`).

Проверено на Lima (1 ГБ RAM, arm64, 1 vCPU, своп 512 МБ), 2026-10-30: 24 потока по 50 МБ (8 параллельно) и 32 параллельных потока + 60 коротких запросов, отказов Caddy нет. Пики: caddy 27–29 МБ, xray 25–28 МБ, cliproxyapi 26 МБ, relay 3, gatus 16, fail2ban 22; `high`/`max`/`oom_kill` = 0 у всех; своп не использовался; ~620 МБ из 979 занимают кэш и буферы, `available` ≈ 630 МБ. Пики stage (xray 74, caddy 76 МБ) в этом прогоне не воспроизвелись (другая сеть и профиль соединений) — лимиты `MemoryHigh=80M`/`MemoryMax=96M` оставлены. Не проверено: упор в лимиты, мобильные клиенты, реальный x86 с 1 ГБ.
