# cliproxyapi

Читать, когда: настраиваешь прокси LLM-API, ключи, апстримы, вход в аккаунты.

## Установка и конфигурация

- Роль: `cliproxyapi`. Репозиторий `router-for-me/CLIProxyAPI`, версия и sha256 пинятся в `infra/ansible/group_vars/all/versions.yml`.
- Релиз: `CLIProxyAPI_<ver>_linux_<arch>.tar.gz`, `<ver>` без `v`, `<arch>` = `amd64` | `aarch64`. Обычная сборка (glibc 2.17+) подходит для Debian 12.
- Конфиг v8 (`config-version: 8`): `server.host: 127.0.0.1`, `server.port: 8317`, `server.trusted-proxies: ["127.0.0.1"]`, `access.api-keys`, `management.secret-key: <bcrypt-хэш>`, `management.allow-remote: false`, `oauth.auth-dir: /var/lib/cliproxyapi/auth`, `requests.proxy-url` — пусто или static ISP прокси.
- **Конфиг создаётся один раз** при bootstrap (`/var/lib/cliproxyapi/config.yaml`, owner `cliproxyapi`, 0600). Ansible не перезаписывает его при последующих прогонах. Изменения через панель CPA сохраняются.
- Каталог `auth` создаётся заранее с правами 0700 (приложение само создаёт его с 0755). Новые auth-файлы подхватываются без рестарта; класть атомарно (`mv` из того же ФС).
- RAM: RSS в покое ~51 MB (cgroup ~22 MB), `MemoryMax=128M` достаточно.
- При старте ходит наружу (каталоги моделей, версии antigravity/npm) с IP VPS или через `proxy-url`.

## Панель управления

Панель доступна двумя способами:

- **SSH-туннель:** `mise run cpa:panel` — поднимает туннель и открывает `http://127.0.0.1:8317/management.html`. Требует `GOLEM_SSH_HOST`, `GOLEM_SSH_PORT`, `GOLEM_SSH_USER` в `mise.local.toml` (`operations/tunnel.md`).
- **Через Xray (`cpa.golem:8317`, ADR 0012):** если включён маршрут Xray, запрос приходит с 127.0.0.1 и считается локальным. `/management.html` отдаётся без ключа; API требует `management_key` (он в `cpa-access.txt`).

Включение: непустой `management.secret-key` (bcrypt-хэш, cost 10). Ключ — в `Authorization: Bearer` или `X-Management-Key`. 5 неверных попыток подряд = бан IP на ~30 мин (в памяти).

**Безопасность (проверено):** запрос от Caddy приходит с 127.0.0.1 — `allow-remote: false` не защищает от внешних клиентов. Защита двойная: (1) Caddy пропускает только `/<llm_path>/v1/*`; (2) `server.trusted-proxies: ["127.0.0.1"]` — без этого внешний перебор ключей банит и владельца.

Статика панели: роль кладёт `management.html` в `/var/lib/cliproxyapi/static/` (проверка sha256, до первого старта), `management.disable-auto-update-panel: true`. Без `MANAGEMENT_STATIC_PATH` панель отвечает 404.

## Экстренная смена ключа management

Открытый ключ лежит в нескольких местах, а конфиг CPA принадлежит панели (ADR 0014): после смены ключа в панели SOPS и сервер расходятся.

| Где | Что | Как меняется |
| :--- | :--- | :--- |
| SOPS хоста: `cliproxyapi_management_key` (+ `cliproxyapi_management_key_hash`) | источник для Ansible | `mise run secrets:edit <host>` |
| `/var/lib/cliproxyapi/config.yaml`, `management.secret-key` | bcrypt-хэш, по нему CPA проверяет ключ | панель CPA |
| `/etc/golem/cpa-monitor.env` (0600) | открытый ключ для `cpa-quota-alert` | `mise run ansible:site <host> --tags cpa_quota_alert` |
| `clients/generated/<host>/cpa-access.txt` | открытый ключ у владельца | `mise run ansible:site <host> --tags client_artifacts` |

Порядок после смены в панели: записать новый открытый ключ в `cliproxyapi_management_key` (`secrets:edit <host>`), выполнить `ansible:site <host> --tags cpa_quota_alert,client_artifacts`. Если `cpa-quota-alert` уже получил 401/403, он остановил опрос после одной неверной попытки: `sudo rm /var/lib/private/golem-cpa-quota/auth-failed`, затем `sudo systemctl start cpa-quota-alert.service` (`components/cpa-quota-alert.md`).

Не проверено: позволяет ли панель менять ключ management; принимает ли CPA в `management.secret-key` открытое значение и хэширует ли его сам. Если ключ нужно сменить не из панели (компрометация), хэш в `config.yaml` заменяется вручную (хэш для `secrets:rotate <host> mgmt` считает `scripts/secrets.sh`), затем `systemctl restart cliproxyapi`; порядок не проверялся.

## Управление ключами доступа

При bootstrap конфиг содержит начальный набор ключей из SOPS; они доступны в `cpa-keys.txt`. После этого ключи управляются через панель:

- **Добавить:** `mise run cpa:genkey` — выводит 48 hex-символов; ввести в поле ключа в панели.
- **Отозвать:** удалить ключ в панели CPA.

⚠️ Пустой список ключей = **fail-open**: запросы без авторизации проходят. При отзыве последнего ключа сначала добавить новый, только потом удалять старый.

Панель сохраняет изменения в `/var/lib/cliproxyapi/config.yaml`; они переживают рестарт сервиса. Ansible конфиг не перезаписывает.

## Мониторинг и лимиты

- `/healthz` без ключа — для Gatus.
- `/v0/management/auth-files` — cooldowns, status OAuth-аккаунтов.
- `/v0/management/api-key-usage` — счётчики по upstream-ключам провайдеров (не по клиентским); `failed` включает 429.
- Статистика запросов: `observability.usage.usage-statistics-enabled: true` (включено по умолчанию в конфиге). Очередь `/v8/management/observability/usage/queue` читается деструктивно — использовать только один потребитель.
- RSS с панелью и статистикой 56–64 MB; `MemoryMax=128M` достаточно.
- Read-only ключа нет: любой ключ даёт полный доступ к Management API, включая OAuth-токены.

## Входы OAuth

Вход без браузера: флаги `-no-browser`, `-oauth-callback-port N`, `-codex-device-login`. Порты по умолчанию: codex 1455, claude 54545, antigravity 51121. Пробросить callback-порт через SSH-туннель или вставить в stdin callback-URL из адресной строки браузера (окно ~15 с). Логиниться на VPS при заданном `requests.proxy-url` на static ISP.

Не проверено: refresh перенесённого токена, приём вставленного URL всеми провайдерами.

## Фиктивный апстрим (только Lima)

Переменная `cliproxyapi_openai_compatibility` (по умолчанию пусто, значение только в `inventories/lima`) + заглушка `tests/fake-llm/lima.sh start`; модели `fake-chat-a`/`fake-chat-b`. SSE через cliproxyapi и Caddy приходит по частям; `FAKE_LLM_FIRST_TOKEN_DELAY` имитирует задержку первого токена.

## SSE heartbeat

`cliproxyapi_keepalive_seconds` (по умолчанию 0 — выключено) и `cliproxyapi_keepalive_before_first_token`. Без них клиент не получает ни байта до первого токена; рассуждающие модели могут упереться в таймаут клиента. Включать значением меньше таймаута клиента (оценка: 10–15 с).
