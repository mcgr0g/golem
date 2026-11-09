# AI-агенты

Читать, когда: подключаешь omp, pi или ccs к relay и к LLM (cliproxyapi) на VPS.

Файлы из `clients/generated/<host>/` (роль `client_artifacts`, содержат секреты):
- `vless-link.txt` / `mihomo-node.yaml` — узел VLESS для mihomo (туннель);
- `omp-env.txt` — relay и веб-клиент omp, LLM по секретному пути Caddy;
- `cpa-access.txt` — адреса cliproxyapi: `direct_base_url`, при включённом `xray_cpa_route_enabled` ещё `local_base_url`, `local_base_url_v1`, `management_key`;
- `cpa-keys.txt` — именованные ключи доступа `имя = ключ` (`home-`/`work-` + `pi|omp|ccs|oc`, `cell`, `nas-01`…`nas-05`); везде ниже `api_key` — ключ из этого файла (своё имя на каждого клиента). Метка ключа в журнале cpa не видна (проверено на Lima), отчёта по ключам нет.

Три способа дойти до LLM:
- **прямой** — `https://<domain>/<llm_path>/v1` через Caddy, прокси не нужен; наружу только `/v1/*` (`components/caddy.md`);
- **локальный порт** — `local_base_url` из `cpa-access.txt` (`http://127.0.0.1:<GOLEM_CPA_LLM_PORT>`, по умолчанию 18317): клиент VLESS пробрасывает порт на VPS (mihomo, секция `tunnels:` из `cpa-access.txt`, проверено; v2rayN — Не проверено). Агенту прокси-настройки не нужны. Порт на VPS наружу не открывается (`research/llm-access/via-xray.md`).
- **прокси-режим** — `http://cpa.golem:8317` через mihomo (правило `DOMAIN,cpa.golem,<узел>`): имя резолвит только Xray; агенту нужны `HTTP(S)_PROXY`/`PI_PROXY_*`/`pi-proxy-router`.

## omp

### Встроенный провайдер (`models.yml`)
- Транспорт: прямой — `base_url` и `api_key` из `omp-env.txt` (или `direct_base_url` и `api_key` из `cpa-keys.txt`); локальный порт — `local_base_url_v1` и `api_key` из `cpa-keys.txt`, узел и правило из `vless-link.txt` / `mihomo-node.yaml`.
- Особенности: провайдер OpenAI-совместимый (`api: openai-completions`), в описании модели обязательны `cost.cacheRead` и `cost.cacheWrite`; ключ лучше брать из переменной окружения. Прокси нужен только в прокси-режиме: `PI_PROXY_<ПРОВАЙДЕР>` (только LLM) или `HTTP(S)_PROXY`; `cpa.golem` не добавлять в `NO_PROXY`. Без прокси на туннельный адрес omp бесконечно повторяет DNS-ошибку.
- Запуск неинтерактивно требует `< /dev/null`. Проверено: через локальный порт работает без прокси. Если клиент VLESS остановлен, omp получает `connection refused` и повторяет попытки циклами (~30 с), быстрого завершения нет.

### Relay и веб-клиент (`collab`)
- Транспорт: прямой WSS на домен; значения `collab.relayUrl`, `collab.webUrl` и `NO_PROXY` — из `omp-env.txt`. Домен VPS держать в `NO_PROXY`, иначе relay пойдёт через собственный туннель.

## pi

### `pi-cliproxyapi-provider`
https://pi.dev/packages/@router-for-me/pi-cliproxyapi-provider

- Транспорт: локальный порт — `CLIPROXYAPI_BASE_URL=local_base_url_v1` и `CLIPROXYAPI_API_KEY=api_key` из `cpa-access.txt`. Прямой по секретному пути Caddy — Не проверено.
- Особенности: с локальным портом прокси агенту не нужен (проверено); нужен `CLIPROXYAPI_PROVIDER_NAME=cliproxyapi` (по умолчанию провайдер регистрируется как `cpa`), а правило `cliproxyapi/*` в `pi-proxy-router` на время работы через локальный порт отключить, иначе запрос уйдёт в прокси. `baseUrl` нужен с `/v1` (без него 404); список моделей появляется после `/cliproxyapi refresh models`; чат идёт на `/v1/chat/completions`. Конфиг провайдера — `~/.pi/agent/pi-cliproxyapi-provider/config.json` или переменные `CLIPROXYAPI_*`.

### `pi-proxy-router`
- Транспорт: прокси mihomo (`socks5h://127.0.0.1:<mixed-порт>`), узел и правило — из `vless-link.txt` / `mihomo-node.yaml`.
- Особенности: правило `"cliproxyapi/*": "socks5h://…"` в `~/.pi/agent/proxy-router.json`; `socks5h` резолвит имя на стороне mihomo, нужно для `cpa.golem`. Альтернатива — `HTTP_PROXY`.

### `better-custom-provider`
https://pi.dev/packages/better-custom-provider
- Транспорт: прямой — `direct_base_url` и `api_key` из `cpa-keys.txt` (мастер `/custom-provider`, стиль OpenAI Chat Completions). Секретный путь сохраняется как есть. Не проверено запуском (по исходникам префикс не срезается).

## ccs

### API-профиль (`ccs api create`)
- Транспорт: локальный порт — `local_base_url` (без `/v1`) и `api_key` из `cpa-keys.txt`: `ccs api create <имя> --preset anthropic --base-url <local_base_url> --api-key <api_key> --model <модель>`; запуск `ccs <имя>` (при прокси-режиме с именем `cpa.golem` — с `HTTP(S)_PROXY`/`ALL_PROXY` на mixed-порт mihomo). Прямой по секретному пути Caddy — нет: ccs не поддерживает префикс пути.
- Особенности: через локальный порт (`--base-url <local_base_url>`, без `/v1`) прокси не нужен (проверено). Если клиент VLESS остановлен, ccs долго ждёт (`Still running…`) вместо быстрого отказа. Claude Code получает `ANTHROPIC_BASE_URL` напрямую, на cliproxyapi идёт `POST /v1/messages`. В `NO_PROXY` — только loopback. Предупреждение «auth readiness» (`/v0/management/*` → 401/403) безвредно. Ключ виден в `ps` на время запуска. Версия конфига ccs — 14 (первая строка `version: 14`).

### Режим `remote` и OAuth-профили (`ccs cliproxy`)
- Транспорт: локальный порт; `management_key` из `cpa-access.txt` нужен для `/v0/management/*`.
- Особенности: рассчитан на OAuth-провайдеров; с провайдерами `openai-compatibility` не работает (`Authentication failed`). Промежуточные прокси ccs по коду ходят к upstream без `HTTP_PROXY` — Не проверено.

## Панель и management
`management_key` и `/management.html` доступны только по туннельному адресу или через SSH-туннель (`operations/tunnel.md`); Caddy их наружу не отдаёт.

### Вход провайдеров по OAuth через панель
Нужен SSH-туннель `mise run tunnel:up` (не туннель mihomo): в `redirect_uri` стоит `http://localhost:<порт>/` (например 54545), после авторизации браузер идёт на этот порт на Mac, и он должен вести на тот же порт loopback VPS. Для этого порт колбэка добавляют в `GOLEM_TUNNEL_FORWARDS` (например `54545:127.0.0.1:54545`); порт у каждого провайдера свой, он виден в `redirect_uri` ссылки входа.

В браузере может потребоваться отключить https://addons.mozilla.org/ru/firefox/addon/canvasblocker/ с ним не работает формирование redirect url.

Порядок: `tunnel:up` → панель `http://127.0.0.1:18317/management.html` → запуск входа → ссылка в браузер → авторизация. Проверено: вход прошёл через `tunnel:up`; через туннель mihomo (`GOLEM_CPA_LLM_PORT`) не прошёл (возврат на страницу выбора аккаунта). Какие именно порты были проброшены в успешном входе — Не проверено.

Через mihomo `tunnels:` порт колбэка пробрасывается так же, как 18317: при `GOLEM_CPA_ROUTE` фрагмент `mihomo-uni-fragment.yaml` содержит строки для `xray_cpa_extra_ports` (по умолчанию 54545 - claude, 1455 - codex, 3002 - Gatus). Проверена цепочка порт Mac -> mihomo -> Xray -> loopback VPS (Lima). Не проверено: реальный OAuth-вход через эти туннели (Q19); колбэк antigravity (51121) не проброшен. Пока Q19 открыт, для входа используйте SSH-туннель.

