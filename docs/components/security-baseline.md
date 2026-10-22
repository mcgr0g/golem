# Базовая безопасность: SSH, UFW, fail2ban

Читать, когда: правишь доступ к хосту, баны, фаервол.

## SSH (роль `ssh_hardening`)
Порт `ssh_port` (не 22), только ключи (основной — Secretive/Secure Enclave с Touch ID, резервный — ed25519 с парольной фразой; `decisions/0010-secrets-sops-age.md`), `PermitRootLogin no`, `PasswordAuthentication no`, `MaxAuthTries 3`, отдельный пользователь `ronnie` с sudo. Смену порта делать так: сначала открыть новый порт в UFW, проверить вход новой сессией, затем закрыть старый — иначе потеря доступа.

## UFW (роль `firewall`)
`default deny incoming`, `allow outgoing`; allow `443/tcp`, `<ssh_port>/tcp`. Docker не ставим (ADR 0001), поэтому обхода правил нет. IPv6: правила дублировать (`IPV6=yes`).

## fail2ban (роль `fail2ban`)
Джейлы: `sshd` (3 попытки, бан 72h); `caddy-ratelimit` — ответы 429 из access-лога; `caddy-scan` — серии 404 на неизвестные пути. `banaction = ufw`. Фильтры читают JSON-лог Caddy (поле `status`, `request.remote_ip`). Белый список: свой IP владельца в `fail2ban_ignoreip` (не фиксировать в git).
Бан по VLESS-пути не делаем: клиент с легитимным UUID не должен банить сам себя при реконнектах; защита — rate limit.

## Проверка
`ufw status verbose`, `fail2ban-client status`, `ss -tlnp` — вне 127.0.0.1 слушают только Caddy и sshd.
