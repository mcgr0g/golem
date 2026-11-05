# Клиенты

Читать, когда: подключаешь устройство к VPS.

| Приоритет | Клиент | Когда | Файл |
| :--- | :--- | :--- | :--- |
| 1 | clash-verge-rev (mihomo) | основной на Mac, текстовый конфиг | `mihomo-clash-verge.md` |
| 2 | v2rayN | фоллбек, импорт `vless://` или подписки | `fallbacks.md` |
| 3 | Throne | если остальные не подошли; часто ручной ввод | `fallbacks.md` |
| — | Dolphin Anty | потребитель SOCKS5 от mihomo | `dolphin-anty.md` |
| — | AI-агенты (omp, pi, ccs) | подключение к cliproxyapi | `ai-agents.md` |

Роль `client_artifacts` рендерит шесть файлов из `clients/templates/` в `clients/generated/<host>/` (вне git, каталог 0700, файлы 0600): `mihomo-node.yaml` (фрагмент для `proxies:`), `vless-link.txt`, `omp-env.txt` (адреса relay и веб-клиента, `NO_PROXY`, URL и ключ LLM), `cpa-access.txt` (прямой и туннельный адрес cliproxyapi, ключ management; подключение агентов — `ai-agents.md`), `cpa-keys.txt` (именованные ключи LLM `имя = ключ`). Берётся первый пользователь `vless_users`; в `omp-env.txt` — ключ `home-omp`. Содержат секреты. После ротации: `mise run ansible:site prod --tags client_artifacts`.
