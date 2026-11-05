# Роль client_artifacts

Рендерит на Mac из `clients/templates/` шесть файлов в `clients/generated/<host>/` (каталог 0700, файлы 0600, вне git): `mihomo-node.yaml` (фрагмент для `proxies:`), `vless-link.txt`, `omp-env.txt`, `cpa-access.txt` (ключ management, адреса прямого и туннельного доступа), `cpa-keys.txt` (именованные ключи LLM). Берётся первый пользователь `vless_users`, в `omp-env.txt` — ключ `home-omp`. После ротации секретов запускается тегом `client_artifacts`. Описание: `docs/clients/README.md`.
