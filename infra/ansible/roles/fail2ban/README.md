# Роль fail2ban

Устанавливает fail2ban и джейлы `sshd` (backend systemd, порт `ssh_port`), `caddy-ratelimit` (ответы 429) и `caddy-auth` (серии 404) по JSON-логу доступа Caddy; бан через UFW. Белый список — `fail2ban_ignoreip`. Описание и значения: `docs/components/security-baseline.md`, переменные — `docs/reference/variables.md`. Роль идёт после `caddy` (нужен лог).
