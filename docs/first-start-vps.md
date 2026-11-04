# Первый запуск: VPS (stage и prod)

Читать, когда: разворачиваешь реальный VPS. Общий порядок, список переменных и сбои — `first-start.md`.

## Отличия stage и prod

| | stage (`golem-dev`) | prod (`golem01`) |
| :--- | :--- | :--- |
| Инвентори | `inventories/stage` | `inventories/prod` |
| Сертификат | боевой Let's Encrypt (`caddy_acme_ca: ""`); для отладки выпуска можно поставить staging CA | боевой Let's Encrypt |
| Gatus | включён (`gatus_enabled: true`) | по умолчанию выключен (`gatus_enabled` не задан) |
| RAM | 4 ГБ (замеры не для 1 ГБ) | 1 ГБ — лимиты `MemoryHigh/Max` проверять |
| Сеть | прямой адрес, SSH на своём порту | возможен серый IP: DNAT для SSH (`GOLEM_SSH_PORT_INTERNAL`), SNAT + PROXY protocol для 443 (`GOLEM_PROXY_PROTOCOL_FROM`); Q14 |
| `ssh_keys.yml` | `inventories/stage/group_vars/all/ssh_keys.yml` | `inventories/prod/group_vars/all/ssh_keys.yml` |

## Порядок

### A. Подготовка на Mac (человек, секреты вносит владелец)

1. Инструменты и `mise install` — `first-start.md`.
2. Публичный ключ SSH: скопируйте `ssh_keys.yml.example` в `ssh_keys.yml` нужного инвентори и впишите публичные ключи (основной — Secretive или обычный ed25519; резервный ed25519 с парольной фразой). Файл в `.gitignore`.
3. `mise.local.toml` из образца: `GOLEM_SSH_HOST`, `GOLEM_SSH_PORT`, `GOLEM_DOMAIN`, `GOLEM_DUCKDNS_SUBDOMAIN`; при DNAT добавьте `GOLEM_SSH_PORT_INTERNAL` (обычно `22`). Переменные читаются на каждый запуск `mise`, один файл — один активный стенд за раз; при переключении stage ↔ prod меняйте значения.
4. DuckDNS: создать поддомен и взять токен в аккаунте DuckDNS.
5. Telegram (необязательно): бот и `chat_id` — `operations/telegram.md`.
6. Секреты: `mise run secrets:init <host>` (`golem-dev` или `golem01`), затем `mise run secrets:edit common` — внести `duckdns_token` и, если нужно, `telegram_bot_token`, `telegram_chat_id`. Бэкап `keys.txt` в менеджер паролей.
7. Сборка: `TARGET_ARCH=amd64 mise run build:artifacts`.
8. Проверки без сети: `mise run ansible:lint`; `mise run ansible:site <env> --syntax-check`.

### B. Первый вход и bootstrap

1. У провайдера на свежем VPS обычно root с паролем. Один раз вручную: `ssh-copy-id -o PubkeyAuthentication=no root@<host>` (при нестандартном внешнем порту — `-p <порт>`); пароль спросит `ssh`. Ключ берётся из агента.
2. `mise run ansible:bootstrap <stage|prod>`. Задача ходит под root на порт 22, а при заданном `GOLEM_SSH_PORT_INTERNAL` — на внешний `GOLEM_SSH_PORT` (при DNAT на 22 снаружи доступа нет). Результат: пакеты, пользователь `ronnie` с вашими ключами и sudo, sshd на время перехода слушает 22 и `ssh_port`.
3. Проверить вход: `ssh -p <внешний порт> ronnie@<host>`.

### C. Развёртывание

1. `mise run ansible:site <stage|prod> --check --diff` — осмотреть изменения. На свежем хосте `--check` частично падает (роль зависит от результата предыдущей) — это ожидаемо, переходите к реальному прогону.
2. `mise run ansible:site <stage|prod>`: firewall открывает порт SSH до смены порта sshd; sshd оставляет только `ssh_port`, root и пароли отключены.
3. Повторный прогон — `changed=0`.
4. Клиентские конфиги появятся в `clients/generated/<host>/`: ссылка VLESS, узел mihomo, `cpa-access.txt`, `omp-env.txt`.

### D. Проверка

1. `operations/smoke-checklist.md`: общий раздел; на prod — также «Только прод».
2. Сертификат: `curl -I https://<домен>/` без `-k` → 200.
3. DuckDNS: запись A (и AAAA, если у хоста есть глобальный IPv6) совпадает с адресом VPS. За NAT входящий и исходящий адреса могут не совпасть — Не проверено (Q14).
4. LLM: ключи cliproxyapi — в `cpa-access.txt`; реальные провайдеры вводятся входом OAuth на VPS (`components/cliproxyapi.md`).
5. Трафик через туннель с Mac: `operations/testing-mihomo.md`.

## Особенности prod

- Серый IP: SSH — DNAT (реальный IP виден sshd), 443 — SNAT через шлюз с PROXY protocol: задайте `GOLEM_PROXY_PROTOCOL_FROM="<адрес шлюза>"` в `mise.local.toml` (ADR 0013) — без этого бан шлюза закроет 443 для всех. 80 шлюз не доводит и он не нужен; входящий и исходящий адреса различаются — `GOLEM_PUBLIC_IP`. Не проверено: постоянный ли адрес шлюза — Q14.
- Смена порта SSH на уже работающем хосте — только через `site.yml --tags firewall,ssh_hardening` с `ansible_port` старого порта (`-e ansible_port=<старый>`); порядок «сначала открыть новый, затем закрыть старый» — `components/security-baseline.md`.
- До покупки узнать, есть ли у провайдера консоль или rescue — Q11.
- Лимиты памяти и реакция на 1 ГБ — Q8; автопродление сертификата — Q13.
