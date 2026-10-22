# Сборка артефактов на Mac

Читать, когда: обновляешь Caddy, веб-клиент или relay.

| Артефакт | Команда (ориентир) | Результат |
| :--- | :--- | :--- |
| Caddy с плагинами | `GOOS=linux GOARCH=<arch> xcaddy build <ver> --with github.com/mholt/caddy-ratelimit [--with github.com/caddy-dns/duckdns]` | `build/caddy` |
| Веб-клиент omp | в `packages/collab-web`: `bun install && bun run build` (+ пост-обработка, `components/omp-relay.md`) | `build/omp-web/` |
| Relay | `bun build --compile --target=bun-linux-x64-baseline scripts/local-relay.ts --outfile build/omp-relay` | `build/omp-relay` |
| Xray, cliproxyapi | не собираются: скачиваются из релизов ролью с проверкой sha256 | — |

Запуск: `mise run build:artifacts [caddy|web|relay|all]` (или `scripts/build-artifacts.sh`). Переменные: `TARGET_ARCH` (`amd64` по умолчанию, `arm64`), `CADDY_VERSION` (v2.11.7), `XCADDY_VERSION` (`latest`, оценка: стоит запинить), `OMP_TAG` (по умолчанию `v<omp --version>` с Mac), `OMP_SRC` (готовый checkout; иначе shallow clone в `build/src/oh-my-pi`), `BUN_RETRIES` (3).

Результат: `build/<arch>/{caddy,omp-relay}`, `build/omp-web/` (не зависит от arch), `build/manifest.json` (версии, плагины Caddy, тег omp, bun, sha256; для `omp-web` — хэш списка хэшей файлов). Роли сверяют хэши до копирования.

Проверено на Mac (arm64) для `amd64`: Caddy v2.11.7 + ratelimit v0.1.0 + duckdns v0.5.0 (ELF x86-64, статический), relay v18.12.6 (ELF x86-64, bun-linux-x64-baseline, 1.4.0), веб-клиент v18.12.6; полный прогон ~50 с.

Пост-обработка веб-клиента (скрипт падает, если формат изменился): удаляется тег `um.can.ac` и `canonical`/`og:url`; в `manifest.webmanifest` пути стали относительными (`./`), `sitemap.xml` удалён, `robots.txt` = `Disallow: /`. В `index.html` остаются только неисполняемые метаданные (`og:image`, JSON-LD со ссылками на `my.omp.sh`/`omp.sh`) — браузер их не загружает. Не проверено: установка PWA под префиксом с относительным манифестом.
