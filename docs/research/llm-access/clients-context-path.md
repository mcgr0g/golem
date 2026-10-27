# Клиенты LLM и секретный context path (`llm_path`)

Читать, когда: выбираешь способ доступа клиентов (omp, pi, ccs) к cliproxyapi: секретный путь Caddy, порт хостера или Xray.

Статус: анализ исходников, реализации нет. Запусков клиентов не было — выводы из кода (репозитории в `<каталог недоверенных репозиториев>`, недоверенный каталог, код не запускался).

## Контекст
Caddy отдаёт LLM только по `https://<domain>/<llm_path>/v1/*` (`strip_prefix` → `127.0.0.1:8317`), остальное под `/<llm_path>/` — 404. До сих пор клиентом был только omp.

## Результаты

| Клиент | Префикс пути | Нужные пути | Работает с текущим Caddy |
|---|---|---|---|
| pi + `pi-cliproxyapi-provider` (991f87c) | Да: `resolveEndpoints` сохраняет `url.pathname`, `/v1` в конце заменяет на `/backend-api` | `GET {root}/v1/models?client_version=pi`, `POST/GET(WS) {root}/backend-api/codex/responses` (+`/compact`) | Нет: `/backend-api/codex/*` под `llm_path` отдаёт 404 |
| omp/pi + `better-custom-provider` (1.6.0) | Да: `src/url.ts` срезает только `/chat/completions`, `/responses`, `/completions`, `/models`, `/messages`; остальной путь сохраняется | `GET {base}/models`, затем запросы нативного провайдера pi/omp (`{base}/chat/completions` и т.п.) | Да, при `base = https://<domain>/<llm_path>/v1` (зондирование сначала без `/v1`, затем с `/v1`) |
| ccs remote proxy (f45fa92) | Нет: `buildProxyUrl` = `protocol://host:port` + фиксированный путь, поля path/prefix нет | root `/v1/messages`, `/v1/models`, `/health`; `/v0/management/*` (usage, OAuth), `/api/provider/codex` (codex-прокси) | Нет |

CLIProxyAPI v8.0.35: маршрут `/backend-api/codex` существует (`server_routes.go`: `GET /responses` — WebSocket, `POST /responses`, `/responses/compact`, `/alpha/search`), за `AuthMiddleware`.

## Выводы
1. pi + provider — лечится в Caddy: добавить в белый список `/<llm_path>/backend-api/codex/*` (та же зона `llm`, `strip_prefix`). Учесть WebSocket на `GET /responses`: `reverse_proxy` его проксирует, но каждое апгрейд-подключение считается в rate limit.
2. omp/pi + better-custom-provider — Caddy менять не надо; это мастер записи `models.json`/`models.yml`.
3. ccs — префикс не поддерживается совсем. Пути: (а) отдельный порт; (б) корневые `/v1/*` на домене (ломает секретный путь: публичный известный URL, только Bearer). Предпочтительно (а).
4. Внешний порт от хостера → внутренний порт VPS. Нельзя вести его на 8317 напрямую: cpa без TLS, без rate limit, без белого списка (management при `trusted-proxies` для внешних клиентов закрыт, но защиты Caddy нет). Вести на отдельный TLS-listener Caddy (`<domain>:<порт>`), в котором только `/v1/*` и `/backend-api/codex/*`, Bearer, rate limit. Сертификат домена Caddy уже имеет. Порт добавить в UFW; fail2ban `caddy-*` читает тот же access-лог.
5. ccs по этому порту: `/v0/management/*` не откроем (функции usage/OAuth-логин через remote недоступны — это штатно, логин через туннель).

## Не проверено
- Реальные запуски pi/ccs/omp против нашего стенда (только чтение кода).
- Стриминг SSE и WebSocket `/backend-api/codex/responses` через Caddy.
- Поведение ccs-туннеля с нестандартным портом HTTPS; токен ccs в заголовке (Bearer / x-api-key).
- Формат omp-env.txt.j2 (`base_url`, `api_key`) относительно текущего omp.
- Какой внутренний порт готов дать хостер и можно ли сразу на 443-совместимый listener.
