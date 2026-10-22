# Caddy

Читать, когда: правишь TLS, маршруты, rate limit, логи.

- Роль Ansible: `caddy`. Бинарник — кастомная сборка на Mac (ADR 0009, проверено v2.11.7): `xcaddy build --with github.com/mholt/caddy-ratelimit --with github.com/caddy-dns/duckdns`, `GOOS=linux GOARCH=amd64` для прода.
- Порт 80 не слушается: `auto_https disable_redirects` (безопасно, выпуск и продление работают). `auto_https off` не использовать. HTTP-01 отключается на эмитенте: `tls { issuer acme { disable_http_challenge } }` (не глобальная опция).
- `tls_mode` (переменная): `acme` (прод, TLS-ALPN-01), `internal` (Lima), `dns01_duckdns`.
  - `internal`: `tls internal`
  - `acme`: `tls { issuer acme { disable_http_challenge } }`
  - `dns01_duckdns`: `tls { issuer acme { dns duckdns {env.DUCK_TOKEN} } }`; staging CA задаётся `dir <URL>` (не `ca`).
- Rate limit: `order rate_limit before basicauth` в глобальных опциях; зона внутри `handle`/`handle_path`, имя зоны уникально; счётчики в памяти, сбрасываются при рестарте; ответ 429 + `Retry-After`. Значения — переменные `RL_WS`, `RL_LLM`, `RL_STATIC` (подбор — Q8).
- Маршрут LLM — только белый список `/<llm_path>/v1/*` (проверено 11 вариантов обхода `..`, `%2e%2e`, `%2f`, `//`, `;`, регистр — все 404). Наивный `handle_path` отдаёт панель и management API наружу.
- WS-матчеры работают только по HTTP/1.1: клиентам Xray ставить `alpn: http/1.1`, иначе получат лендинг.
- `handle_errors` скрывает `Server` и в ответах 429. Лендинг одинаков для любых неизвестных путей, включая WS-пути без Upgrade (проб не отличает).
- Логи: JSON, ротация встроена (`roll_size`, `roll_keep`); fail2ban читает их.
- Systemd: пользователь `caddy`, `AmbientCapabilities=CAP_NET_BIND_SERVICE`, `MemoryMax=96M` — RSS в покое ~50 MB (измерено), под нагрузкой не мерили: возможно потребуется 128M.
- DNS-01 DuckDNS проверен на staging CA для `golem-dev.duckdns.org` (Caddy на Mac, выпуск ~20 с, плагин меняет только TXT). Плагин при сетевой ошибке пишет токен в текст ошибки (URL с `token=`): лог Caddy закрыт (0640, `caddy:adm`), токен считать скомпрометированным при утечке лога.
- Не проверено: боевой CA (первая попытка упала на TLS handshake timeout к www.duckdns.org до создания челленджа), сам TLS-ALPN-01 (нужен публичный хост), запуск сборки amd64.

Проверенный Caddyfile — образец; рабочая версия — шаблон `roles/caddy/templates/Caddyfile.j2` (Jinja вместо `{$ENV}`, `redir` уже добавлен). Конфиг проверяется `caddy adapt` до записи (`validate` через `caddy validate` создал бы лог-файл от root). Проверено в Lima: 401/200 для /v1/*, 404 для management и `..`, 308 на `/<app_path>`, WS 101 для Xray и relay, заголовка `Server` нет; RSS ~17 MB cgroup в покое. Редирект `/<app_path>` → `/<app_path>/` добавить (`redir`).

```
{
	order rate_limit before basicauth
	# 80 не слушаем: без редиректов, без HTTP-01
	auto_https disable_redirects
	servers {
		protocols h1 h2
	}
	{$ACME_CA_LINE}
}

{$DOMAIN} {
	{$TLS_LINE}

	log {
		output file {$LOG_FILE} {
			roll_size 10MiB
			roll_keep 3
		}
		format json
	}

	header -Server
	header Strict-Transport-Security "max-age=31536000"

	@ws_relay {
		path /r/*
		header Connection *Upgrade*
		header Upgrade websocket
	}
	@ws_xray {
		path /{$WS_PATH}
		header Connection *Upgrade*
		header Upgrade websocket
	}

	handle @ws_relay {
		rate_limit {
			zone ws {
				key {remote_host}
				events {$RL_WS}
				window 1m
			}
		}
		reverse_proxy 127.0.0.1:7466
	}
	handle @ws_xray {
		rate_limit {
			zone ws_xray {
				key {remote_host}
				events {$RL_WS}
				window 1m
			}
		}
		reverse_proxy 127.0.0.1:10000
	}
	# Белый список: наружу только /v1/*. Всё остальное (/management.html, /v0/management/*,
	# OAuth-callback) для Caddy-клиента закрыто, иначе оно считалось бы локальным (см. components/cliproxyapi.md)
	handle /{$LLM_PATH}/v1/* {
		rate_limit {
			zone llm {
				key {remote_host}
				events {$RL_LLM}
				window 1m
			}
		}
		uri strip_prefix /{$LLM_PATH}
		reverse_proxy 127.0.0.1:8317
	}
	handle /{$LLM_PATH}/* {
		respond 404
	}
	handle_path /{$APP_PATH}/* {
		rate_limit {
			zone static_app {
				key {remote_host}
				events {$RL_STATIC}
				window 1m
			}
		}
		root * {$APP_ROOT}
		file_server
	}
	handle {
		rate_limit {
			zone static_landing {
				key {remote_host}
				events {$RL_STATIC}
				window 1m
			}
		}
		root * {$LANDING_ROOT}
		try_files {path} /index.html
		file_server
	}

	# 429 и прочие ошибки, сгенерированные самим Caddy, тоже без заголовка Server
	handle_errors {
		header -Server
		respond "{err.status_code} {err.status_text}" {err.status_code}
	}
}
```
