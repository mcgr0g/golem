# Секреты

Читать, когда: создаёшь/ротируешь секреты, добавляешь хост.

| Секрет | Где живёт | Генерация |
| :--- | :--- | :--- |
| UUID VLESS | sops-файл хоста | `uuidgen` при первом запуске |
| `app_path`, `ws_path`, `llm_path` | sops-файл хоста | случайные 16–24 символа `[a-z0-9]` |
| Bearer-ключи cliproxyapi | sops-файл хоста (начальный набор при bootstrap) | генерируются при `init`; после bootstrap управляются через панель CPA |
| OAuth-файлы cliproxyapi | sops (файлы) | вход на VPS (`components/cliproxyapi.md`); доставка атомарно, 0600, каталог 0700 |
| Ключ management CPA | sops-файл хоста | 48 символов; в конфиг — bcrypt-хэш, открытый ключ у владельца |
| DuckDNS токен | sops общий | из аккаунта DuckDNS |
| Telegram токен/чат | sops общий | опционально, см. `telegram.md` |
| SSH-ключ | Mac (`~/.ssh`) | `ssh-keygen -t ed25519` |

Решение: `decisions/0010-secrets-sops-age.md`. Правила: у каждого VPS свои UUID/пути/ключ (общий компрометирует все). Приватный age-ключ — только у владельца (`~/.config/sops/age/keys.txt`), бэкап в менеджере паролей. Ротация инфраструктурных секретов (UUID, пути, management): `secrets:rotate`, затем `ansible:site prod --tags caddy,xray`, затем перегенерация `clients/generated/`. Ключи доступа CPA управляются через панель (`components/cliproxyapi.md`).

## Инструкция для начинающих (sops + age)

Задачи `secrets:*` — обёртки над `scripts/secrets.sh` (проверены на одноразовом ключе). Ключ ищется в `~/.config/sops/age/keys.txt` (или `SOPS_AGE_KEY_FILE`), существующий не перезаписывается. Файлы: `infra/ansible/secrets/<host>.sops.yml` (хост) и `common.sops.yml` (DuckDNS, Telegram).

1. Установить: `brew install age sops` (или `mise use age sops`).
2. `mise run secrets:init <host>` (например `golem01`) создаст age-ключ при отсутствии, `.sops.yaml`, `common.sops.yml` и секреты хоста. Сделайте бэкап `keys.txt` в менеджер паролей.
3. Править секреты: `mise run secrets:edit <host|common>` (откроет расшифрованный файл в редакторе и зашифрует при сохранении).
4. Не коммитить `keys.txt`, не вставлять расшифрованные значения в чат и документы.
5. Ротация инфраструктурных секретов: `mise run secrets:rotate <host> <uuid|paths|mgmt|all>` (меняет значения; ключ management пересчитывает в bcrypt cost 10; ключи доступа CPA — через панель, не через rotate).
6. Первые входные данные от владельца: DuckDNS токен и поддомен — вносятся через `secrets:edit`.
