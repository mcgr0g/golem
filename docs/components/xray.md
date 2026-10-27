# Xray-core

Читать, когда: правишь VLESS inbound, пользователей, цепочку к static ISP прокси.

- Роль: `xray`. Бинарник — официальный релиз XTLS/Xray-core, версия и sha256 в `versions.yml`.
- Конфиг `/etc/xray/config.json` из шаблона. Inbound: `vless`, listen `127.0.0.1:10000`, `network: ws`, `wsSettings.path: /<ws_path>`, `security: none`, `decryption: none`, `clients: [{id: <uuid>, email: <label>}]`. Без `flow` (xtls-rprx-vision не работает с WS).
- Outbound по умолчанию: `freedom` (с `domainStrategy: UseIPv4`, если у VPS нет IPv6-маршрута), `blackhole` для блокировок, правило `geoip:private → block`, чтобы не ходить из туннеля в 127.0.0.1/LAN VPS.
- Маршрут к cliproxyapi (`xray_cpa_route_enabled`, по умолчанию выключен; ADR 0012): outbound `cpa` (`freedom`, `redirect 127.0.0.1:<cliproxyapi_port>`) и правило `domain: full:<xray_cpa_domain>` выше `geoip:private`. Известно: `localhost:8317` через VLESS не блокируется (правило по IP не видит имя), риск принят в ADR 0012.
- Цепочка на сервере (опционально, `xray_chain_enabled`): outbound `socks`/`http` на static ISP прокси + routing по `user`. По умолчанию выключено; основная цепочка — на клиенте (`architecture/04-traffic-flows.md`, вариант D).
- Логи: `loglevel: warning`, без access-логов (экономия диска, меньше следов).
- Systemd: `MemoryHigh=80M`, `MemoryMax=96M`, пользователь `xray` (системный, без shell; `DynamicUser` не используем: конфиг `root:xray 0640`), `XRAY_LOCATION_ASSET=/opt/xray/current` (geoip.dat/geosite.dat лежат рядом с бинарником в `/opt/xray/<ver>`, `current` — симлинк; без них правило `geoip:private` не загрузится). Конфиг проверяется `xray run -test` до записи.
- Клиентский профиль: `clients/mihomo-clash-verge.md`.
- Нагрузка (Xray v26.3.27, aarch64, без TLS): покой RSS ~31 MB; 5 потоков по 400 MB + короткие соединения — пик cgroup 63 MB; шквал 50 параллельных циклов — RSS 47 MB, без OOM. `MemoryMax=96M` достаточен. Пик смотреть в `/sys/fs/cgroup/system.slice/xray.service/memory.peak` (`systemctl show -p MemoryPeak` на systemd 252 пуст). Повторить на x86 при первом выкате.
- Xray предупреждает, что WebSocket-транспорт устарел (рекомендует XHTTP). Остаёмся на WS (совместимость с Caddy и клиентами); смена — новый ADR.
