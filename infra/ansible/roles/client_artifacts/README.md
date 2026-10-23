# Роль client_artifacts

Рендерит на Mac из `clients/templates/` три файла в `clients/generated/<host>/` (каталог 0700, файлы 0600, вне git): `mihomo-node.yaml` (фрагмент для `proxies:`), `vless-link.txt`, `omp-env.txt`. Берётся первый пользователь `vless_users` и первый ключ `cliproxyapi_api_keys`. После ротации секретов запускается тегом `client_artifacts`. Описание: `docs/clients/README.md`.
