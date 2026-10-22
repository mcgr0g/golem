# Фоллбек-клиенты

Читать, когда: clash-verge-rev недоступен.

- **v2rayN**: импорт из буфера `vless://<uuid>@<domain>:443?type=ws&security=tls&sni=<domain>&host=<domain>&path=%2F<ws_path>&alpn=http%2F1.1&fp=chrome#golem-<host>`. Ansible кладёт готовую ссылку в `vless-link.txt`.
- **Throne**: ручной ввод тех же полей (VLESS, транспорт WebSocket, TLS, SNI, путь, Host). Импорт из буфера нестабилен (опыт пользователя).
- Общие правила: `alpn=http/1.1`, `flow` пустой, SNI = домен.
