# Первый запуск: общий порядок

Читать, когда: поднимаешь стенд с нуля (Lima, stage или prod) и нужно знать, что задать и в каком порядке. Детали сценариев — `first-start-lima.md` и `first-start-vps.md`.

Стенды (имя в инвентори = имя файла секретов = `inventory_hostname`):

| Стенд | Инвентори | Хост | Что это | Сценарий |
| :--- | :--- | :--- | :--- | :--- |
| Lima | `lima` | `golem-test` | VM на Mac, arm64, `tls_mode=internal`, домена нет | `first-start-lima.md` |
| stage | `stage` | `golem-dev` | реальный VPS (x86_64), боевой Let's Encrypt, домен DuckDNS | `first-start-vps.md` |
| prod | `prod` | `golem01` | целевой VPS, 1 ГБ RAM | `first-start-vps.md` |

## Что общего у всех стендов

Порядок шагов; каждый шаг помечен стендами, где он нужен.

| № | Шаг | Lima | stage | prod | Кто |
| :--- | :--- | :---: | :---: | :---: | :--- |
| 1 | Инструменты на Mac (раздел ниже) | да | да | да | человек |
| 2 | SSH-ключ владельца и `ssh_keys.yml` | нет (ключ ставит Lima) | да | да | человек |
| 3 | `mise.local.toml` с параметрами хоста | нет | да | да | человек |
| 4 | `mise run secrets:init <host>` | да | да | да | человек |
| 5 | Токены DuckDNS и Telegram: `mise run secrets:edit common` | нет | да | да | человек |
| 6 | Сборка: `TARGET_ARCH=<arm64\|amd64> mise run build:artifacts` | arm64 | amd64 | amd64 | человек |
| 7 | Первый вход на VPS (`ssh-copy-id` под root) и `ansible:bootstrap` | нет | да | да | человек |
| 8 | `mise run ansible:site <env>` (повторный прогон: `changed=0`) | да | да | да | человек |
| 9 | Клиентские конфиги из `clients/generated/<host>/` | да | да | да | человек |
| 10 | Смоук-чеклист (`operations/smoke-checklist.md`) | общее | общее | общее + «только прод» | человек |

Одна сборка — одна архитектура: `build/` содержит последнюю собранную. Перед прогоном на другом стенде пересоберите под его архитектуру, иначе `omp_relay` остановится на проверке `manifest.json`.

## Шаг 1. Инструменты на Mac

- `mise` — ставит Ansible, ansible-lint, yamllint, Python и uv по `mise.toml`: `mise install`.
- `age`, `sops`, `apache2-utils` (`htpasswd`), `openssl`: `brew install age sops`; `htpasswd` и `openssl` в macOS есть.
- Сборка артефактов: Go, Bun и Node нужны в `PATH` (в `mise.toml` проекта их нет — на машине владельца они из глобального mise); также `git` и доступ к GitHub. Подробности — `operations/build-artifacts.md`.
- Для Lima — `limactl`; для проверки трафика (`tests/mihomo`) — Docker Desktop, необязательно.

## Параметры в `mise.local.toml`

Файл в `.gitignore`, образец — `mise.local.toml.example`. Значения не коммитить.

| Переменная | Нужна | Смысл |
| :--- | :--- | :--- |
| `GOLEM_SSH_HOST` | stage, prod | адрес VPS (IP или домен) |
| `GOLEM_SSH_PORT` | stage, prod | внешний порт SSH, к которому подключается Mac |
| `GOLEM_SSH_PORT_INTERNAL` | только при DNAT | порт sshd внутри VPS (обычно 22); не задан → равен внешнему |
| `GOLEM_SSH_USER` | туннель | по умолчанию `ronnie` |
| `GOLEM_DOMAIN`, `GOLEM_DUCKDNS_SUBDOMAIN` | stage, prod | FQDN и поддомен DuckDNS |
| `GOLEM_CPA_ROUTE` | необязательно | `"true"` включает маршрут к cliproxyapi через Xray (ADR 0012) |
| `GOLEM_CPA_LLM_PORT` | необязательно | локальный порт для агентов, по умолчанию 18317 |
| `GOLEM_TUNNEL_FORWARDS` | необязательно | проброс `tunnel:up` |

Полный список и связь с переменными Ansible — `reference/variables.md`.

## Секреты (кратко)

`secrets:init <host>` создаёт age-ключ (если нет), `.sops.yaml`, `common.sops.yml` и файл хоста со случайными UUID, путями, ключами. Бэкап `~/.config/sops/age/keys.txt` в менеджер паролей — до первого `ansible:site`. Значения вносит владелец сам; в чат и документы они не попадают. Подробности и ротация — `operations/secrets.md`.

## Что делать при сбое

- `Connection closed` / `kex_exchange_identification` / таймаут SSH на VPS: сеть до VPS бывает нестабильна, повторите команду. Если не проходит — `nc -zv <host> <порт>`, затем журнал sshd на сервере.
- `omp_relay`: «build/ отсутствует или не совпадает с manifest.json» — пересоберите под архитектуру стенда (`build:artifacts`).
- `--check` на свежем стенде может падать там, где задача зависит от результата предыдущей (например, каталог версии ещё не создан): для первого прогона запускайте без `--check`.
- Потеря доступа по SSH после смены порта или фаервола: нужна консоль провайдера (веб-VNC/rescue); у целевого провайдера это не выяснено — `open-questions.md`, Q11.
