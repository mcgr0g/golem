# 0001 — cliproxyapi без Docker

Статус: принято.

## Контекст
cliproxyapi — один статический Go-бинарник (релизы `CLIProxyAPI_<ver>_linux_<arch>.tar.gz`, последняя проверенная v8.0.35). В репозитории есть Dockerfile, но он не обязателен. Docker-демон на 1 GB RAM: ~50–100 MB (оценка) и отдельная сеть/iptables, конфликтующая с UFW.

## Решение
Бинарник + systemd-юнит от непривилегированного пользователя. Docker на VPS не ставим. Вопрос «rootful vs rootless» снимается; если Docker понадобится позже — rootless/podman, не rootful (rootful Docker публикует порты в обход UFW).

## Последствия
- Обновление: роль скачивает релиз по версии из переменной, проверяет sha256.
- Изоляция — средствами systemd (`ProtectSystem=strict`, `NoNewPrivileges`, `MemoryMax`).
- Слушает `server.host: 127.0.0.1`. Management API выключен (`management.secret-key` пуст).

## Пересмотреть
Если cliproxyapi начнёт требовать внешние сервисы (БД/браузер) для OAuth.
