# omp relay и веб-клиент

Читать, когда: настраиваешь /collab, сборку клиента, сервис relay.

- Роль: `omp_relay`. Источник: `can1357/oh-my-pi`, тег должен совпадать с версией omp на Mac (протокол).
- **Веб-клиент** (сборка на Mac, ADR 0009): из корня монорепо `bun install --filter @oh-my-pi/collab-web --frozen-lockfile`, затем в `packages/collab-web` `bun run build` → `dist/`. Сборщик `bun build ./index.html`, vite и `--base` нет. Ассеты относительные, один `dist/` работает под любым префиксом (нужен слэш на конце).
- Пост-обработка `dist/` при сборке:
  1. Удалить тег аналитики `https://um.can.ac/script.js` из `index.html` (иначе IP посетителя уходит стороннему сервису).
  2. `manifest.webmanifest` содержит абсолютные пути (`/`, `/favicon.svg`); под префиксом иконки PWA дают 404 — либо подменить на `/<app_path>/`, либо не ставить PWA.
  3. `robots.txt`/`sitemap.xml`: удалить или `Disallow: /`; canonical/OG на `my.omp.sh` убрать.
- **Relay**: `bun build --compile --target=bun-linux-x64-baseline packages/collab-web/scripts/local-relay.ts --outfile build/omp-relay` (~82 MB, bun на VPS не нужен). Загрузка runtime иногда обрывается — в скрипте сборки retry. Запуск: `omp-relay --port 7466`, systemd `omp-relay.service`, пользователь `omp-relay`, `MemoryMax=128M`. Relay не умеет выбирать адрес привязки и слушает `*:7466` (проверено); поэтому в юните `IPAddressDeny=any` + `IPAddressAllow=localhost` (с внешнего адреса VM порт недоступен, проверено), плюс UFW. Артефакт веб-клиента роль синхронизирует в `/var/www/omp-web`.
- **RAM** (измерено на aarch64): покой ~16 MB, 1 хост + 50 гостей ~32 MB.
- Caddy: `handle /r/*` на корне домена + `handle_path /<app_path>/*` (статика) + `redir /<app_path> /<app_path>/`. Подтверждено в headless Chrome: страница под префиксом подключается к WS на корне.
- Клиентская настройка omp: `collab.relayUrl=wss://<domain>`, `collab.webUrl=https://<domain>/<app_path>/` (путь принимается, query и fragment — нет).
- Ограничения заглушки: нет auth, `/healthz`, раздачи клиента, share-блобов (`/s/*`). Браузер требует https.
- Безопасность: ссылка с ключом = полный контроль агента. Содержимое для relay непрозрачно.
- Живость: TCP-проба 7466 + WS-handshake через Caddy.
- Проверено в Lima (arm64): роль, WS-рукопожатие через Caddy (101). Идентификатор комнаты — `[A-Za-z0-9_-]{10,64}`. Не проверено: запуск x64-baseline бинарника (тест шёл на aarch64) — подтвердить на Lima x86 или проде; TLS-путь (тесты шли на http://localhost).

Проверено на реальном x86_64 VPS (Debian 12, стенд `stage`): baseline-бинарник relay запускается, WS-handshake через Caddy даёт 101, в покое ~2 MB (cgroup). Снаружи порт 7466 закрыт.
