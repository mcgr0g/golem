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
