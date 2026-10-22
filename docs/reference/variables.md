# Переменные Ansible

Читать, когда: добавляешь/меняешь переменную. Обновлять при каждом изменении (правило синхронизации).

| Переменная | Область | Пример/умолчание | Назначение |
| :--- | :--- | :--- | :--- |
| `domain` | host | `<sub>.duckdns.org` | единственный FQDN |
| `duckdns_subdomain` | host | `golem01` | обновление DNS |
| `target_arch` | env | `amd64` / `arm64` | выбор артефактов |
| `ssh_port` | env | число ≠ 22 | порт sshd и UFW |
| `tls_mode` | env | `acme`/`internal`/`dns01_duckdns` | выпуск сертификата |
| `app_path`, `ws_path`, `llm_path` | host (sops) | случайные | секретные маршруты |
| `vless_users` | host (sops) | список `{id,email}` | клиенты Xray |
| `cliproxyapi_api_keys` | host (sops) | список | Bearer-ключи |
| `cliproxyapi_proxy_url` | host | `""` | выход через static ISP прокси |
| `xray_chain_enabled` | host | `false` | серверная цепочка |
| `ram_alert_kb` | env | `51200` | порог алерта |
| `fail2ban_ignoreip` | env | список | белый список |
| `versions.*` | all | caddy/xray/cliproxyapi/omp | пины версий |
| `cliproxyapi_management_key_hash` | host (sops) | bcrypt | `management.secret-key` |
| `cpa_panel_version`, `cpa_panel_sha256` | all | v1.26.6 / sha256 | пиннинг `management.html` |
| `RL_WS`, `RL_LLM`, `RL_STATIC` | env | событий/мин | лимиты Caddy |
| `gatus_enabled` | host | `false` | роль мониторинга |
| `telegram_bot_token`, `telegram_chat_id` | env (sops) | — | алерты Gatus и ram-alert |
| `ssh_authorized_keys` | env (локальный файл, .gitignore) | список pub-ключей | доступ `ronnie` |
| `duckdns_subdomain` | host | prod: `golem01`; тест: `golem-dev` | домены `golem01.duckdns.org`, `golem-dev.duckdns.org` |
