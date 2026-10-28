# Структура Ansible

Читать, когда: создаёшь роль/плейбук или добавляешь хост.

```
infra/ansible/
  ansible.cfg
  requirements.yml            # коллекции (ansible.posix, community.general)
  inventories/
    lima/{hosts.yml,group_vars/,host_vars/}
    stage/{hosts.yml,group_vars/}   # реальный x86_64 VPS для обкатки: хост golem-dev, staging CA
    prod/{hosts.yml,group_vars/,host_vars/<host>.yml}
  group_vars/all/versions.yml # пины версий; подключается через vars_files (каталог не рядом с плейбуками)
  secrets/                    # sops-файлы (в .gitignore)
  playbooks/{bootstrap.yml,site.yml}
  .yamllint  .ansible-lint
  roles/
    base  ssh_hardening  firewall  fail2ban
    caddy  xray  cliproxyapi  omp_relay
    ops_timers  gatus  client_artifacts
```

- `bootstrap.yml` (под root): `raw` — python3, пользователь `ronnie`, ключи, sudo; sshd на время перехода слушает 22 и `ssh_port` (`00-bootstrap.conf`; при `ssh_port == 22` одна строка `Port 22`), роль `ssh_hardening` оставляет только `ssh_port`. Порт входа задаёт `mise run ansible:bootstrap`: 22, а при заданном `GOLEM_SSH_PORT_INTERNAL` (DNAT) — внешний `GOLEM_SSH_PORT`. Для Lima не нужен (`ssh_port: 22`, порт пробрасывает сама Lima).
- Порты SSH: `ssh_external_port` (`GOLEM_SSH_PORT`) — куда подключается Mac (`ansible_port`, туннель); `ssh_port` (`GOLEM_SSH_PORT_INTERNAL`, по умолчанию равен внешнему) — порт sshd, UFW и fail2ban на VPS. Различаются только при DNAT у провайдера (внешний порт → 22 внутри). Lima: внешний 60022, внутренний 22.
- `site.yml`: все роли в порядке: base → firewall → ssh_hardening → caddy → xray → cliproxyapi → omp_relay → fail2ban → ops_timers → gatus (при `gatus_enabled`) → client_artifacts. Все роли реализованы; `client_artifacts` рендерит на Mac `clients/generated/<host>/`. Firewall раньше ssh_hardening: новый порт открывается до смены порта sshd.
- Новый VPS: добавить запись в `inventories/prod/hosts.yml`, создать `host_vars/<host>.yml` (минимум `domain`, `duckdns_subdomain`), запустить `bootstrap.yml`, `site.yml`. Секреты (UUID, пути, ключи) генерируются при первом запуске и сохраняются в sops-файл хоста (`infra/ansible/secrets/<host>.sops.yml`) (`operations/secrets.md`).
- Идемпотентность: повторный `site.yml` не даёт изменений (`changed=0`) — критерий приёмки роли.
- Теги по ролям (`--tags caddy`). Ротация секретов: `mise run secrets:rotate ...`, затем `mise run ansible:site prod --tags caddy,xray,cliproxyapi`. Запуск: `mise run ansible:site <lima|prod> [args]`, проверки: `mise run ansible:lint`. Параметры прод-хоста — из окружения (`mise.local.toml`: `GOLEM_SSH_HOST/PORT`, `GOLEM_DOMAIN`, `GOLEM_DUCKDNS_SUBDOMAIN`). Артефакты из `build/` сверяются с `manifest.json` до копирования. Переменные — `reference/variables.md`.
- Первый вход на свежий VPS (у провайдера обычно root с паролем; `sshpass` не нужен): один раз вручную `ssh-copy-id -o PubkeyAuthentication=no root@<ip>` (спросит пароль; ключ берётся из агента, Secretive) — затем `mise run ansible:bootstrap <stage|prod>` идёт по ключу, `mise run ansible:site <stage|prod>` — под `ronnie` на `ssh_external_port`. Стенд `stage` использует `tls_mode: acme` со staging CA (`caddy_acme_ca`), для боевого сертификата значение очистить.
