# Тестирование на Lima

Читать, когда: проверяешь роли до выката.

- Запуск: `limactl start --name=golem-test infra/lima/vps-test.yaml`; `mise run secrets:init golem-test`; `TARGET_ARCH=arm64 mise run build:artifacts`; `mise run ansible:site lima`. Проверено: 11 ролей, повторный прогон `changed=0`. VM наследует прокси Mac: в curl внутри VM использовать `--noproxy '*'`.
- Образ Debian 12, 1 CPU, `memory: 1GiB`, диск 10 GiB — как у целевого VPS. Mac на Apple Silicon: тестовая VM `aarch64` (нативно), поэтому артефакты собираются под `target_arch=arm64`. Прогон x86_64 в QEMU возможен, но медленный — только для финальной сверки.
- Шаблон: `infra/lima/vps-test.yaml` (пользователь `ronnie`). SSH: `limactl list`, порт — из вывода.
- Инвентори `inventories/lima`: `tls_mode=internal` (локальный CA Caddy), домен `golem.test` в `/etc/hosts` Mac на 127.0.0.1 с пробросом 443 (Q3: либо DNS-01 DuckDNS для настоящего сертификата).
- Что проверяется в Lima: идемпотентность, systemd-юниты и `MemoryMax`, маршрутизация Caddy, WS-пробы, Xray ↔ mihomo на Mac, rate limit/fail2ban, нагрузка на 1 GiB.
- Что нельзя проверить в Lima (только прод): выпуск Let's Encrypt по ALPN, внешняя доступность 443, DuckDNS обновление, реальная латентность. Эти пункты — в `smoke-checklist.md`, раздел «Прод».
