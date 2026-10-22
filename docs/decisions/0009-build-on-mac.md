# 0009 — Артефакты собираются на Mac

Статус: принято.

## Контекст
1 GB RAM не вытягивает `xcaddy build` (Go-линковка) и `vite build`. Caddy нужен с плагинами (`caddy-ratelimit`, опц. `caddy-dns/duckdns`), веб-клиенту omp нужна сборка.

## Решение
На Mac: `xcaddy build` с `GOOS=linux GOARCH=amd64`, сборка collab-web (`bun run build`), опц. `bun build --compile` для relay. Результат в `build/` (вне git) + файл `build/manifest.json` с версиями и sha256. Ansible копирует артефакты и сверяет хэш. Версии пинятся в `group_vars/all/versions.yml`.

## Последствия
Для Apple Silicon — кросс-компиляция Go тривиальна; бинарник x86_64 в Lima aarch64 не запустится, поэтому в Lima собираем под `arm64` (переменная `target_arch`).
