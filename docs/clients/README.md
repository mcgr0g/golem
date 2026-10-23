# Клиенты

Читать, когда: подключаешь устройство к VPS.

| Приоритет | Клиент | Когда | Файл |
| :--- | :--- | :--- | :--- |
| 1 | clash-verge-rev (mihomo) | основной на Mac, текстовый конфиг | `mihomo-clash-verge.md` |
| 2 | v2rayN | фоллбек, импорт `vless://` или подписки | `fallbacks.md` |
| 3 | Throne | если остальные не подошли; часто ручной ввод | `fallbacks.md` |
| — | Dolphin Anty | потребитель SOCKS5 от mihomo | `dolphin-anty.md` |

Роль `client_artifacts` рендерит три файла из `clients/templates/` в `clients/generated/<host>/` (вне git, каталог 0700, файлы 0600): `mihomo-node.yaml` (фрагмент для `proxies:`), `vless-link.txt`, `omp-env.txt` (адреса relay и веб-клиента, `NO_PROXY`, URL и ключ LLM). Берутся первый пользователь `vless_users` и первый ключ `cliproxyapi_api_keys`. Содержат секреты. После ротации: `mise run ansible:site prod --tags client_artifacts`.
