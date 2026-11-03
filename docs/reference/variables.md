# Переменные Ansible

Читать, когда: добавляешь/меняешь переменную. Обновлять при каждом изменении (правило синхронизации).

| Переменная | Область | Пример/умолчание | Назначение |
| :--- | :--- | :--- | :--- |
| `domain` | host | `<sub>.duckdns.org` | единственный FQDN |
| `duckdns_subdomain` | host | `golem01` | обновление DNS |
| `target_arch` | env | `amd64` / `arm64` | выбор артефактов |
| `ssh_port` | env | число; не 22 без DNAT | порт sshd на VPS (внутренний), UFW, джейл fail2ban `sshd` |
| `ssh_external_port` | env | число | внешний порт SSH: `ansible_port`, туннель; равен `ssh_port`, если нет DNAT |
| `tls_mode` | env | `acme`/`internal`/`dns01_duckdns` | выпуск сертификата |
| `app_path`, `ws_path`, `llm_path` | host (sops) | случайные | секретные маршруты |
| `vless_users` | host (sops) | список `{id,email}` | клиенты Xray |
| `cliproxyapi_api_keys` | host (sops) | список | Bearer-ключи |
| `cliproxyapi_openai_compatibility` | роль; значение только в inventories lima | `[]` | провайдеры `openai-compatibility` в конфиге cliproxyapi (в Lima — фиктивный апстрим `tests/fake-llm`) |
| `cliproxyapi_keepalive_seconds`, `cliproxyapi_keepalive_before_first_token` | роль | `0`, `false` | `streaming.keepalive-seconds` и `send-keepalive-before-ft` в конфиге cliproxyapi: SSE-комментарии `: keep-alive`, в том числе до первого токена. 0 — выключено |
| `cliproxyapi_proxy_url` | host | `""` | выход через static ISP прокси |
| `xray_chain_enabled` | host | `false` (`true` не реализовано, роль падает) | серверная цепочка |
| `GOLEM_CPA_LLM_PORT` / `client_artifacts_cpa_local_port` | окружение (`mise.local.toml`) / роль | `18317` | локальный порт на Mac для туннеля к cliproxyapi (в `cpa-access.txt`); не 8317 |
| `GOLEM_CPA_ROUTE` / `xray_cpa_route_enabled`, `xray_cpa_domain` | окружение (`mise.local.toml`) / роль | `false` (включение: `GOLEM_CPA_ROUTE = "true"`; через `-e` булево передавать JSON-ом), `cpa.golem` | маршрут имени в Xray на loopback cliproxyapi (ADR 0012); добавляет в `cpa-access.txt` туннельный адрес и `management_key` |
| `cliproxyapi_management_key` | host (sops) | 48 символов | открытый ключ management; попадает в `cpa-access.txt` при включённом маршруте |
| `ram_alert_kb` | env | `51200` (по умолчанию в юните) | порог алерта |
| `fail2ban_ignoreip` | env | `[]` | белый список |
| `fail2ban_{sshd,ratelimit,auth}_{maxretry,findtime,bantime}`, `fail2ban_caddy_log` | роль | 3/10m/72h, 20/10m/24h, 15/10m/24h | параметры джейлов |
| `ops_timers_interval`, `ops_timers_duckdns_enabled`, `ops_timers_health_check_enabled`, `ops_timers_scripts_dir` | роль | `5min`, по токену и поддомену, `true`, `/usr/local/lib/golem` | таймеры эксплуатации |
| `gatus_port`, `gatus_interval`, `gatus_cert_min` | роль | 3002, `60s`, `168h` | Gatus |
| `client_artifacts_out_dir`, `client_artifacts_templates_dir` | роль | `clients/generated/<host>`, `clients/templates` | выход и шаблоны клиентских конфигов |
| `versions.*` | all | caddy/xray/cliproxyapi/omp | пины версий |
| `cliproxyapi_management_key_hash` | host (sops) | bcrypt | `management.secret-key` |
| `cpa_panel_version`, `cpa_panel_sha256` | all | v1.26.6 / sha256 | пиннинг `management.html` |
| `caddy_rl_ws`, `caddy_rl_llm`, `caddy_rl_static` | env | 30 / 120 / 120 (оценка) | лимиты Caddy, событий/мин на IP |
| `caddy_acme_ca` | env | `""` | URL каталога ACME (staging); пусто = боевой |
| `ssh_user` | env | `ronnie` | пользователь Ansible и `AllowUsers` |
| `xray_version`, `xray_assets`, `cliproxyapi_version`, `cliproxyapi_assets` | all | `group_vars/all/versions.yml` | пины версий и sha256 по `target_arch` |
| `ops_timers_duckdns_ipv4` (`GOLEM_PUBLIC_IP`) | окружение (`mise.local.toml`) | пусто | явный IPv4 для A-записи DuckDNS; пусто — адрес исходящего запроса (за NAT может не совпасть с входящим) |
| `duckdns_token` | common (sops) | — | DNS-01 и обновление DNS |
| `GOLEM_SSH_HOST`, `GOLEM_SSH_PORT`, `GOLEM_DOMAIN`, `GOLEM_DUCKDNS_SUBDOMAIN` | окружение (`mise.local.toml`) | — | `ansible_host`, `ssh_external_port` (и `ansible_port`), `domain`, `duckdns_subdomain` прод-хоста |
| `GOLEM_SSH_PORT_INTERNAL` | окружение (`mise.local.toml`), необязательно | пусто → равен `GOLEM_SSH_PORT`; при DNAT `22` | `ssh_port` (порт sshd). Заданный — признак DNAT: `ansible:bootstrap` ходит на внешний порт, а не на 22 |
| `gatus_enabled` | host | `false` (в Lima `true`) | роль мониторинга |
| `telegram_bot_token`, `telegram_chat_id` | env (sops) | — | алерты Gatus и ram-alert |
| `ssh_authorized_keys` | env (локальный файл, .gitignore) | список pub-ключей | доступ `ronnie` |
| `duckdns_subdomain` | host | prod: `golem01`; тест: `golem-dev` | домены `golem01.duckdns.org`, `golem-dev.duckdns.org` |
