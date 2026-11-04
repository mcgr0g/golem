# Базовая безопасность: SSH, UFW, fail2ban

Читать, когда: правишь доступ к хосту, баны, фаервол.

## SSH (роль `ssh_hardening`)
Порт `ssh_port` (не 22; при DNAT у провайдера внутренний порт может быть 22, а внешний — другим, `GOLEM_SSH_PORT_INTERNAL`), только ключи (основной — Secretive/Secure Enclave с Touch ID, резервный — ed25519 с парольной фразой; `decisions/0010-secrets-sops-age.md`), `PermitRootLogin no`, `PasswordAuthentication no`, `MaxAuthTries 3`, отдельный пользователь `ronnie` с sudo. Смену порта делать так: сначала открыть новый порт в UFW, проверить вход новой сессией, затем закрыть старый — иначе потеря доступа.

## UFW (роль `firewall`)
`default deny incoming`, `allow outgoing`; allow `443/tcp`, `<ssh_port>/tcp`. Docker не ставим (ADR 0001), поэтому обхода правил нет. IPv6: правила дублировать (`IPV6=yes`).

## fail2ban (роль `fail2ban`)
Джейлы: `sshd` (3 попытки, бан 72h, backend systemd, порт `ssh_port`); `caddy-ratelimit` — ответы 429 из access-лога (20 за 10 мин, бан 24h); `caddy-auth` — серии 401/404 (15 за 10 мин, бан 24h). `banaction = ufw`. Фильтры читают JSON-лог Caddy (`request.remote_ip`, `status`, время из `ts`). Белый список: `fail2ban_ignoreip` (не фиксировать в git); при `proxy_protocol_from` (SNAT-шлюз, ADR 0013) его адреса добавляются в `ignoreip` автоматически; `127.0.0.0/8` и адреса самого хоста fail2ban игнорирует всегда (`ignoreself`).
Почему не «404 на неизвестные пути»: неизвестные пути получают лендинг с 200 (проб не отличает, `components/caddy.md`), поэтому 404 и 401 видит только тот, кто уже знает секретный префикс (`llm_path`/`app_path`) и ошибся (неверный Bearer-ключ, закрытые подпути). Легитимный клиент их не вызывает.
Бан по VLESS-пути не делаем: клиент с легитимным UUID не должен банить сам себя при реконнектах; защита — rate limit.
Проверено на Lima: фильтры (`fail2ban-regex`), бан через UFW после 15 ответов 401 и снятие бана. Не проверено: джейл `sshd` с реальными неудачными входами, бан по 429.

## Проверка
`ufw status verbose`, `fail2ban-client status`, `ss -tlnp` — вне 127.0.0.1 слушают Caddy, sshd и relay (`*:7466`, закрыт `IPAddressDeny`/UFW, `components/omp-relay.md`).
