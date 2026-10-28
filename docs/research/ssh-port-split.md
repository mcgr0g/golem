# Разделение внешнего и внутреннего порта SSH (DNAT у провайдера)

Статус: реализовано 2026-10-28 (Lima: внутренний 22, внешний 60022, changed=0; stage --check без регрессии). Реальный DNAT не воспроизводился. Решение владельца: переменная `GOLEM_SSH_PORT_INTERNAL`.

## Проблема
Целевой провайдер даёт серый IP: DNAT пробрасывает 80/443 и один внешний порт SSH на порт 22 внутри VPS (DNAT подтверждён поддержкой, реальный IP клиента сохраняется). Сейчас `GOLEM_SSH_PORT` → `ssh_port` одновременно задаёт порт sshd, правило UFW, порт джейла fail2ban (внутренний) и `ansible_port`/порт туннеля (внешний). При DNAT эти значения различаются, одной переменной не обойтись.

## Решение
- `GOLEM_SSH_PORT` — внешний порт (то, к чему подключается Mac): `ansible_port`, `tunnel:*`.
- `GOLEM_SSH_PORT_INTERNAL` — порт sshd на VPS. Необязателен; не задан или пуст → равен `GOLEM_SSH_PORT`. Для prod = 22.
- Переменные Ansible: `ssh_port` (внутренний; sshd, UFW, fail2ban — как сейчас) = `GOLEM_SSH_PORT_INTERNAL` или `GOLEM_SSH_PORT`; `ssh_external_port` = `GOLEM_SSH_PORT` (для `ansible_port`). Именовать единообразно с `GOLEM_*`.
- Реализация необязательности: `lookup('env', 'GOLEM_SSH_PORT_INTERNAL', default='')` с проверкой длины в inventory, а не Undefined.

## Находки, которые надо учесть
1. `mise ansible:bootstrap` жёстко ставит `-e ansible_port=22`. При DNAT свежий VPS доступен снаружи только на внешнем порту, а не на 22 → bootstrap должен ходить на `GOLEM_SSH_PORT` (для stage без DNAT оставить прежнее поведение: 22 — когда внутренний ≠ внешний и провайдер не пробрасывает; нужно явное решение).
2. bootstrap.yml пишет drop-in `Port 22` + `Port {{ ssh_port }}`; при `ssh_port == 22` получится дубль → условие (одна строка).
3. firewall: удаление правила UFW для 22 выполняется `when ssh_port != 22`; с внутренним 22 корректно ничего не удалять — проверить.
4. fail2ban sshd: порт джейла = внутренний (после DNAT пакет приходит на 22). Менять не требуется, проверить.
5. Риск потери доступа: ошибка в паре портов отрезает SSH; консоль провайдера на тестовой VPS есть (веб-VNC), на целевой — Q11.
6. DuckDNS за NAT: входящий и исходящий публичный адрес могут не совпасть → проверить; при необходимости передавать IP явно (`ip=` из переменной/внешнего сервиса). IPv6 у серого IP, скорее всего, нет.
7. Q14 сузить: DNAT подтверждён → остаются IPv6 и совпадение адресов.

## План
1. Inventory (stage, prod): `ssh_port` (внутренний), `ssh_external_port`, `ansible_port: ssh_external_port`; `assert` в site.yml на оба.
2. `mise.toml`: tunnel — `GOLEM_SSH_PORT`; `ansible:bootstrap` — порт по п.1; `mise.local.toml.example` — оба с комментарием.
3. Роли: ssh_hardening/firewall/fail2ban — только `ssh_port`; bootstrap.yml — условие дубля (п.2); проверить п.3.
4. Проверка в Lima: ssh_port=22, внешний 60022 (проброс Lima уже есть) → site.yml, повторный прогон changed=0, sshd слушает только 22, fail2ban sshd port=22, UFW 22.
5. Проверка на stage без регрессии: `GOLEM_SSH_PORT_INTERNAL` не задан → поведение прежнее (changed=0).
6. Документация (синхронизация): docs/reference/variables.md, components/security-baseline.md, operations/ansible-layout.md, operations/tunnel.md, architecture/03-deployment.md, mise.local.toml.example, open-questions (Q14).
7. Запреты AGENTS.md: без ignore_errors; ADR не нужен (конфигурация, не архитектура), но п.1 зафиксировать в ansible-layout.md.

## Не проверено
Реальный DNAT (воспроизвести нельзя на stage без смены порта у провайдера); поведение bootstrap при дубле Port; DuckDNS за NAT.
