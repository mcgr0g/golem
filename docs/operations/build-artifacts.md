# Сборка артефактов на Mac

Читать, когда: обновляешь Caddy, веб-клиент или relay.

| Артефакт | Команда (ориентир) | Результат |
| :--- | :--- | :--- |
| Caddy с плагинами и NaïveProxy | клон Caddy `<ver>` + патчи форка forwardproxy, затем `GOOS=linux GOARCH=<arch> xcaddy build <ver> --replace github.com/caddyserver/caddy/v2=<клон> --with github.com/caddyserver/forwardproxy=<форк@SHA> --with github.com/mholt/caddy-ratelimit --with github.com/caddy-dns/duckdns` (рецепт klzgrad, ADR 0015) | `build/<arch>/caddy` |
| Веб-клиент omp | в `packages/collab-web`: `bun install && bun run build` (+ пост-обработка, `components/omp-relay.md`) | `build/omp-web/` |
| Relay | `bun build --compile --target=bun-linux-x64-baseline scripts/local-relay.ts --outfile build/omp-relay` | `build/omp-relay` |
| Gatus (опц.) | клон тега `GATUS_VERSION`, `CGO_ENABLED=0 GOOS=linux GOARCH=<arch> go build -ldflags "-s -w"` (готовых релизов нет, ADR 0011) | `build/<arch>/gatus` |
| Xray, cliproxyapi | не собираются: скачиваются из релизов ролью с проверкой sha256 | — |

Запуск: `mise run build:artifacts [caddy|web|relay|gatus|all]` (или `scripts/build-artifacts.sh`). Переменные: `TARGET_ARCH` (`amd64` по умолчанию, `arm64`), `CADDY_VERSION`, `GATUS_VERSION` (значения по умолчанию — в `scripts/build-artifacts.sh`), `XCADDY_VERSION` (`latest`, оценка: стоит запинить), `OMP_TAG` (по умолчанию `v<omp --version>` с Mac), `OMP_SRC` (готовый checkout; иначе shallow clone в `build/src/oh-my-pi`), `BUN_RETRIES` (3).

Результат: `build/<arch>/{caddy,omp-relay,gatus}`, `build/omp-web/` (не зависит от arch), `build/manifest.json` (версии, плагины Caddy, тег omp, bun, sha256; для `omp-web` — хэш списка хэшей файлов). Роли сверяют хэши до копирования.

Проверено на Mac (arm64) для `amd64`: Caddy с ratelimit и duckdns (ELF x86-64, статический), relay (ELF x86-64, bun-linux-x64-baseline), веб-клиент; полный прогон ~50 с; Gatus собран для amd64 и arm64 (ELF, статический). Версии — в `scripts/build-artifacts.sh`.

Сборка Caddy с forwardproxy по рецепту klzgrad проверена на Mac (arm64) для `amd64` и `arm64` (2026-11-09, ~15–25 с каждая). Исходники форка и патченого Caddy клонируются заново при каждой сборке в `build/src/forwardproxy` и `build/src/caddy-patched`. Переменная `FORWARDPROXY_REF` — полный SHA форка (короткий для shallow fetch не подходит).

Пост-обработка веб-клиента (скрипт падает, если формат изменился): удаляется тег `um.can.ac` и `canonical`/`og:url`; в `manifest.webmanifest` пути стали относительными (`./`), `sitemap.xml` удалён, `robots.txt` = `Disallow: /`. В `index.html` остаются только неисполняемые метаданные (`og:image`, JSON-LD со ссылками на `my.omp.sh`/`omp.sh`) — браузер их не загружает. Не проверено: установка PWA под префиксом с относительным манифестом.
