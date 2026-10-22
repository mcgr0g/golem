# Структура Ansible

Читать, когда: создаёшь роль/плейбук или добавляешь хост.

```
infra/ansible/
  ansible.cfg
  requirements.yml            # коллекции (ansible.posix, community.general)
  inventories/
    lima/{hosts.yml,group_vars/,host_vars/}
    prod/{hosts.yml,group_vars/,host_vars/<host>.yml}
  group_vars/all/{versions.yml,main.yml}
  playbooks/{bootstrap.yml,site.yml,rotate-secrets.yml}
  roles/
    base  ssh_hardening  firewall  fail2ban
    caddy  xray  cliproxyapi  omp_relay
    ops_timers  client_artifacts
```

- `bootstrap.yml`: `raw` — установка python3, пользователь `ronnie`, ключ, затем смена порта SSH.
- `site.yml`: все роли в порядке: base → ssh_hardening → firewall → caddy → xray → cliproxyapi → omp_relay → fail2ban → ops_timers → client_artifacts.
- Новый VPS: добавить запись в `inventories/prod/hosts.yml`, создать `host_vars/<host>.yml` (минимум `domain`, `duckdns_subdomain`), запустить `bootstrap.yml`, `site.yml`. Секреты (UUID, пути, ключи) генерируются при первом запуске и сохраняются в sops-файл хоста (`infra/ansible/secrets/<host>.sops.yml`) (`operations/secrets.md`).
- Идемпотентность: повторный `site.yml` не даёт изменений (`changed=0`) — критерий приёмки роли.
- Теги по ролям (`--tags caddy`). Переменные — `reference/variables.md`.
