# Smoke-чеклист

Читать, когда: после выката на Lima или прод.

## Общее (Lima и прод)
1. `ansible-playbook site.yml` повторно: `changed=0`.
2. `ss -tlnp`: вне 127.0.0.1 — Caddy:443, sshd и relay:7466 (последний недоступен снаружи: `IPAddressDeny`, UFW).
3. `systemctl --failed` пусто; `systemctl show <svc> -p MemoryMax`.
4. `curl -I https://<domain>/` → 200 лендинг; случайный путь → тот же лендинг; `/r/x` без Upgrade → лендинг/404 (не 400/502).
5. WS-handshake на `/r/<id>?role=host` с `Upgrade` → 101; на `/<ws_path>` → 101 или ответ Xray.
6. mihomo с узлом: `curl -x socks5h://127.0.0.1:7897 https://ifconfig.me` → IP VPS.
7. `omp` `/collab` с настроенным relayUrl: гость из браузера подключается, промпт доходит.
8. LLM: `curl -H "Authorization: Bearer <ключ>" https://<domain>/<llm_path>/v1/models` → 200; без ключа → 401.
9. rate limit: серия запросов → 429, fail2ban банит (тест с отдельного IP или через `fail2ban-client set <jail> banip/unbanip`; с самого хоста — после `set <jail> delignoreip 127.0.0.0/8` и `ignoreself false`, затем `systemctl restart fail2ban`). Проверить `caddy-auth`: серия запросов с неверным ключом на `/<llm_path>/v1/models`.
10. Нагрузка: 3 потока через Xray + активная комната + запрос к LLM; `MemAvailable` не ниже 100 MB (повторить на x86 при первом выкате).

## Только прод
11. Сертификат выпущен (`caddy`/journal), браузер без предупреждений.
12. Порт 80 закрыт снаружи, обновление сертификата пробное (`caddy reload` + проверка срока).
13. DuckDNS таймер обновляет запись; `ram-alert` шлёт тестовое уведомление; `reboot-alert` шлёт сообщение, если ядро старее установленного (на свежем хосте сообщения нет — это норма).
14. Утечки: DNS-leak и IP-проверка в профиле Dolphin; IP = VPS.
