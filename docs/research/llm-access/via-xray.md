# Доступ к cliproxyapi через Xray (без внешнего порта хостера)

Читать, когда: выбираешь способ доступа клиентов (omp, pi, ccs) к cliproxyapi: секретный путь Caddy, порт хостера или Xray.

Статус: анализ, реализации нет. Дополняет `clients-context-path.md`.

## Идея
Клиент на Mac ходит на виртуальное имя (`cpa.golem`, не резолвится в DNS) по HTTP через прокси mihomo (mixed-port). Правило mihomo `DOMAIN,cpa.golem → узел VPS`. На VPS Xray по специальному правилу направляет это имя в `freedom` с `redirect: 127.0.0.1:8317`. Снаружи нужен только 443 (VLESS+WS+TLS уже есть). Шифрование — VLESS поверх TLS Caddy.

## Серверная часть (Xray)
- Сейчас `geoip:private → blackhole` блокирует 127.0.0.1. Нужны outbound `cpa` (freedom, settings.redirect `127.0.0.1:8317`) и правило routing `domain: full:cpa.golem` (+ при желании `user: <email владельца>`) выше правила private.
- Не проверено: срабатывает ли domain-правило до блокировки private и корректно ли redirect в freedom для VLESS-входа; проверять в Lima.
- Безопасность: запрос приходит в cpa с 127.0.0.1 без X-Forwarded-For → считается локальным (как SSH-туннель). Значит через этот путь доступна и панель /management.html (нужен management-ключ). Ограничить правилом по `user`, чтобы чужие uuid не ходили в cpa; белый список /v1 тут не применяется. Нужен Bearer `api-keys`.

## Клиентская часть
- mihomo: правило `DOMAIN,cpa.golem,<узел>` выше остальных; mixed-port 7897.
- omp/pi: `HTTPS_PROXY/HTTP_PROXY=http://127.0.0.1:7897`, base URL `http://cpa.golem:8317/v1` (pi-provider: `http://cpa.golem:8317`). `cpa.golem` не должно попадать в NO_PROXY. Path-префикс не нужен, `/backend-api/codex/*` доступен без правок Caddy.
- ccs: `cliproxy_server.remote {host: cpa.golem, port: 8317, protocol: http}`. Код ccs: собственный fetch (undici) уважает HTTP(S)_PROXY/ALL_PROXY и обходит прокси для loopback — `cpa.golem` не loopback, значит пойдёт через прокси. Сам Claude Code, запускаемый ccs, по документации читает HTTP(S)_PROXY. Не проверено: локальные промежуточные прокси ccs (codex-reasoning, tool-sanitization) могут ходить к удалённому хосту напрямую без прокси; при protocol=https ccs поднимает свой HttpsTunnelProxy (https.request), прокси-переменные там не найдены — использовать protocol=http.

## Плюсы / минусы
+ Порт хостера не нужен, всё в 443; 8317 остаётся loopback; нет overhead SSH и его нестабильности; панель CPA доступна тем же путём (замена `cpa:panel`).
+ Fail-closed: без mihomo имя не резолвится.
− LLM зависит от запущенного mihomo; каждому клиенту нужны proxy-переменные; на VM/другой машине — настройка прокси.
− Любой, у кого uuid без ограничения по user, получает доступ на 8317 (митигируется routing по user).
− Нестандартный путь в Xray, не из ADR 0006 (нужен ADR при внедрении).

## Проверить в Lima до решения
1. Xray: правило + redirect, `curl -x` через mihomo к `http://cpa.golem:8317/v1/models` → 401 без ключа, 200 с ключом; SSE/WS `/backend-api/codex/responses`.
2. Что `127.0.0.1:8317` и прочие private по-прежнему блокируются для других имён/IP.
3. omp, pi (provider), ccs реально с proxy env; в ccs — трафик локальных промежуточных прокси.

## Результаты проверок (2026-10-27, Lima golem-test)
Прямой VLESS (клиентский Xray в VM, CONNECT): `cpa.golem:8317/v1/models` 401 без ключа / 200 с ключом; `/backend-api/codex/responses` POST и WS-апгрейд без ключа — 401; `127.0.0.1`, `127.0.0.2` заблокированы; `/management.html` без ключа — 200 (панель доступна по этому пути). Повторный прогон `changed=0`, флаг выключен — конфиг прежний.
Через mihomo (`mihomo-experiment.sh`, mixed-порт, правило `DOMAIN,cpa.golem`): plain HTTP `http://cpa.golem:8317/v1/models` — 401/200. 503 на plain HTTP был особенностью самодельного клиентского Xray, не схемы.
`localhost:8317` через VLESS отдаёт 200 (правило `geoip:private` не видит имя; `freedom` резолвит само). Решение владельца: uuid приравнен к ключу, риском пренебрегаем.
Клиенты по исходникам: omp — `PI_PROXY_<ПРОВАЙДЕР>` > `PI_PROXY` > `HTTP(S)_PROXY` > `ALL_PROXY`; pi — `pi-proxy-router` (`"cliproxyapi/*": "socks5h://127.0.0.1:<порт>"`); ccs — `remote.protocol: http`, при remote встроенный cliproxyapi не стартует.
Не проверено: запуск pi/omp/ccs против стенда (в cpa Lima нет провайдеров — ожидается фиктивный), SSE/WS-стриминг.

## Прогон клиентов (2026-10-27, Lima + fake-llm, mihomo → Xray → `cpa.golem:8317`; субагент, не перепроверено)
Трафик подтверждён строками `cpa.golem:8317 match Domain(cpa.golem)` в логе mihomo. Ключ стенда (заглушка), не секрет.
| Клиент | Прокси | Результат |
|---|---|---|
| pi 1.4.0 + pi-cliproxyapi-provider 0.15.58 | `pi-proxy-router` (`cliproxyapi/*` → `socks5h://…`) | ответ заглушки получен; без прокси — `Connection error` |
| pi | `HTTP_PROXY` | ответ получен |
| omp 18.12.6 (`models.yml`, `openai-completions`, baseUrl `…/v1`) | `PI_PROXY_CLIPROXYAPI` | ответ получен |
| omp | `HTTP_PROXY`+`HTTPS_PROXY` | ответ получен; без прокси — бесконечные ретраи DNS (`ENOTFOUND`), не выходит |
| ccs 8.10.0 (`remote`, `protocol: http`) | `HTTP(S)/ALL_PROXY` | «Connected to remote proxy at cpa.golem:8317» (проверка шла через mihomo), далее «Authentication failed»; Claude ходит на локальный tool-sanitization-прокси (DIRECT), upstream до cpa не наблюдался. **Не доведено** |
Нюансы pi: конфиг провайдера — `~/.pi/agent/pi-cliproxyapi-provider/config.json` или `CLIPROXYAPI_*`; baseUrl нужен с `/v1` (иначе 404); модели появляются после `/cliproxyapi refresh models` (до этого `login-required`); chat идёт на `/v1/chat/completions`, а не `/backend-api/codex/responses`. Нюансы omp: `models.yml` требует `cost.cacheRead/cacheWrite`; без `< /dev/null` висит на stdin. Нюансы ccs: в `config.yaml` первой строкой `version: 14`; `ccs cliproxy status` «Running» — ложное (порт 8317 занят пробросом Lima).
Не проверено: ccs end-to-end (причина ошибки авторизации), тайминги SSE через VLESS, WebSocket, контроль ccs без прокси.

## ccs до конца (2026-10-27, ccs 8.10.0, config version 14; субагент, не перепроверено)
Рабочий путь — **API-профиль**, не remote-OAuth:
1. `ccs api create <имя> --preset anthropic --base-url http://cpa.golem:8317 --api-key <ключ> --model <модель> --yes`
2. `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY=http://127.0.0.1:<mixed-порт> NO_PROXY=127.0.0.1,localhost ccs <имя> -p "…"` → ответ fake-llm (SSE), exit 0.
- Claude Code получает `ANTHROPIC_BASE_URL=http://cpa.golem:8317` напрямую (без промежуточных прокси ccs), `ANTHROPIC_AUTH_TOKEN` = api-key. Трафик идёт через mihomo (3 соединения: `GET /`, `GET /v0/management/auth-files`, `POST /v1/messages?beta=true`). ccs ставит undici-dispatcher, уважающий `HTTP(S)_PROXY` (loopback в обход).
- Модели `openai-compatibility` cpa отдаёт и на `/v1/messages` (ccs-запрос 200, 3 с).
- Без прокси: `cpa.golem` не резолвится, ccs зависает до таймаута.
- Предупреждение «auth readiness» из-за `GET /v0/management/auth-files` → 401/403: нужен `management_key`, на ответ не влияет (в профиле API он не требуется).
- Режим `cliproxy_server.remote` (`ccs claude`) и `ccs cliproxy create --provider claude`: OAuth-only; fake-провайдер не подключить, `Authentication failed`/`OAuth start failed 403`. По чтению кода промежуточный `tool-sanitization-proxy` ходит к upstream через `http.request` без `HTTP_PROXY` — в remote-цепочке с `cpa.golem` не сработает (не проверено).
- Ключ передаётся в argv `ccs` (виден в `ps`).
Не проверено: `management_key`, тайминги SSE на уровне ccs, remote-OAuth end-to-end.
