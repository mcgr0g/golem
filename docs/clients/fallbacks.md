# Фоллбек-клиенты

Читать, когда: clash-verge-rev недоступен.

- **v2rayN**: импорт из буфера `vless://<uuid>@<domain>:443?encryption=none&type=ws&security=tls&sni=<domain>&host=<domain>&path=%2F<ws_path>&alpn=http%2F1.1&fp=chrome#golem-<host>`. Ansible кладёт готовую ссылку в `vless-link.txt`.
- **Throne**: ручной ввод тех же полей (VLESS, транспорт WebSocket, TLS, SNI, путь, Host). Импорт из буфера нестабилен (опыт пользователя).
- Общие правила: `alpn=http/1.1`, `flow` пустой, SNI = домен.
- **NaïveProxy** (ADR 0015, при `GOLEM_NAIVE_ENABLED=true`): v2rayN — импорт из буфера ссылки `naive+https://<имя>:<пароль>@<domain>:443?security=tls&sni=<domain>&type=tcp&headerType=none#<host>-naive`; Ansible кладёт её в `v2rayn-naive.txt`. Throne — тот же формат; нестабилен ли импорт — Не проверено. В mihomo naive нет. В логе v2rayN возможна безвредная ошибка `open UDP connection to [2001:4860:4860::8888]:443 … no route to host`: клиент проверяет наличие IPv6-маршрута, при его отсутствии идёт по IPv4 (трафик при этом проходит).
- Проверка прямого пути: при включённом TUN (mihomo) подключение клиента к серверу идёт через цепочку, и сервер видит адрес её выхода, а не провайдера клиента. Прямой путь проверяет только прогон при выключенном TUN; признак успеха — российский адрес клиента в `access.log` Caddy. Автономный тест: `tests/naive/test-naive.sh <хост>`.
