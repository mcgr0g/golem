# Первый запуск: Lima

Читать, когда: поднимаешь тестовую VM на Mac. Общий порядок и параметры — `first-start.md`.

Ничего не нужно: ни домена, ни DuckDNS, ни Telegram, ни `ssh_keys.yml`, ни `mise.local.toml` (параметры инвентори `lima` заданы в репозитории). Хост — `golem-test`, `target_arch: arm64`, `tls_mode: internal`.

1. `mise install`; Lima: `limactl` установлен.
2. Запустить VM (Debian 12, 1 CPU, 1 ГиБ): `limactl start --name=golem-test infra/lima/vps-test.yaml`. Ключ SSH Lima кладёт сама. Внешний порт SSH — 60022 (проброс Lima на 22 гостя).
3. Секреты: `mise run secrets:init golem-test` (создаст age-ключ, если его ещё нет, — сделайте бэкап).
4. Артефакты под arm64: `TARGET_ARCH=arm64 mise run build:artifacts`.
5. Прогон: `mise run ansible:site lima`; повторный — `changed=0`.
6. Домен `golem.test`: добавьте в `/etc/hosts` Mac `127.0.0.1 golem.test`; порт 443 Lima пробрасывает на Mac. Сертификат — локальный CA Caddy, клиентам нужен `-k`/`skip-cert-verify`; для `curl` без правки hosts: `--resolve golem.test:443:127.0.0.1`.
7. Клиентские конфиги: `clients/generated/golem-test/` (`mihomo-node.yaml`, `cpa-access.txt`, …).
8. Проверки: общий раздел `operations/smoke-checklist.md`. LLM без реального провайдера — `tests/fake-llm/lima.sh start` (см. `operations/testing-lima.md`); трафик через туннель — `operations/testing-mihomo.md`.

Ограничения: Lima проверяет роли, идемпотентность, лимиты systemd и маршруты. Выпуск Let's Encrypt, внешнюю доступность 443, DuckDNS и реальную латентность проверить нельзя — `operations/testing-lima.md`.
