# Клиенты

Читать, когда: подключаешь устройство к VPS.

| Приоритет | Клиент | Когда | Файл |
| :--- | :--- | :--- | :--- |
| 1 | clash-verge-rev (mihomo) | основной на Mac, текстовый конфиг | `mihomo-clash-verge.md` |
| 2 | v2rayN | фоллбек, импорт `vless://` или подписки | `fallbacks.md` |
| 3 | Throne | если остальные не подошли; часто ручной ввод | `fallbacks.md` |
| — | Dolphin Anty | потребитель SOCKS5 от mihomo | `dolphin-anty.md` |

Ansible выдаёт три артефакта в `clients/generated/<host>/` (вне git): `mihomo-proxy.yaml` (фрагмент), `vless-link.txt`, `omp-env.txt` (переменные omp). Содержат секреты.
