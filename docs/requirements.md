# Требования

Читать, когда: нужно понять цели, ограничения и что НЕ делаем.

## Цели
1. **omp /collab с телефона** через собственный relay на VPS (без туннелей с MacBook). Детали: `components/omp-relay.md`.
2. **Прокси LLM-API** (cliproxyapi) с личным Bearer-ключом. `components/cliproxyapi.md`.
3. **VLESS+WS+TLS прокси**, неотличимый от обычного HTTPS на 443, для Dolphin Anty, авторизации и пополнения баланса в западных AI-сервисах и для агентов (веб-поиск, чтение источников). `components/xray.md`, `clients/`.
4. **Защита**: секретные пути, Caddy rate limit, fail2ban, UFW, ключевой SSH. `components/security-baseline.md`.
5. **Цепочка** с static ISP прокси (опционально). `architecture/04-traffic-flows.md`.
6. **Повторяемость**: 2–3 одинаковых VPS, отличие — домен 3-го уровня (DuckDNS) и секреты. `operations/ansible-layout.md`.

## Ограничения
- VPS: Debian 12, x86_64, 1 GB RAM, + swap 512 MB. Если нагрузочный тест не проходит — +0.5 GB RAM.
- Наружу: только 443/tcp и SSH (нестандартный порт). 80 закрыт (ACME через TLS-ALPN). Все сервисы слушают 127.0.0.1.
- Один домен, один сертификат, один порт.
- Сборка артефактов — на Mac, не на VPS.
- Тестовый стенд (Lima за NAT) не получает сертификат Let's Encrypt по HTTP/ALPN: проверка TLS-пути — на проде; см. `open-questions.md` (Q3).

## Не-цели (в этой версии)
- Gost/ShadowTLS резервный канал, Uptime Kuma, веб-панели Xray (3x-ui и т.п.). Обоснование: `decisions/0007-scope-cuts.md`.
- Docker. `decisions/0001-no-docker-cliproxyapi.md`.
- Мульти-пользовательский доступ: один владелец.

## Что значит «не детектируется реальный IP/DNS»
Целевые сервисы видят только IP VPS (или static ISP прокси при цепочке). DNS-запросы клиента уходят внутрь туннеля (удалённый резолв в mihomo, SOCKS5 с доменом). Что остаётся рисками: утечки WebRTC/DNS на стороне браузера Dolphin, совпадение IP VPS с известными дата-центровыми диапазонами. См. `clients/dolphin-anty.md`.
