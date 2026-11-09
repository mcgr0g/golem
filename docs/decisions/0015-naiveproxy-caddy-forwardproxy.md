# 0015 — NaïveProxy через Caddy forward_proxy

Статус: принято (выбор владельца 2026-11-09); включается переменной `GOLEM_NAIVE_ENABLED`, по умолчанию выключено. Проверено: сервер (Lima, golem-dev, golem01) принимает и обслуживает CONNECT; клиентская сторона на golem-dev работает напрямую. На golem01 прямой путь из РФ не работает по причине, не связанной с протоколом (см. «Последствия»).

## Контекст
Прямое подключение к `golem01` по VLESS (WS, XHTTP) блокируется ТСПУ (инцидент 2026-11-08, `local/research/incident-20261108-analysis.md`). `client-fingerprint: chrome` в mihomo уже включён, поэтому причина не в отпечатке клиента. NaïveProxy использует настоящий сетевой стек Chromium (TLS-отпечаток неотличим от браузера), HTTP/2 CONNECT и padding первых пакетов; при пробе без учётных данных сервер отдаёт обычный сайт. Клиенты: v2rayN и Throne (оба встраивают naive), в mihomo протокола нет. Дополнительные порты у провайдера заказываются долго (VPS за SNAT), Xray убирать нельзя.

## Решение
- Серверная часть — тот же Caddy на :443 с плагином `forward_proxy` (форк klzgrad/forwardproxy, ветка `naive`). Отдельного серверного бинарника у проекта нет.
- Конфигурация включается `caddy_naive_enabled` (из `naive_enabled` ← `GOLEM_NAIVE_ENABLED`). Два условия, без которых `forward_proxy` не вызывается (подтверждено на golem-dev: в логе Caddy `NOP`, status 0, bytes_read 0):
  1. адрес сайта `<domain>, :443`: у CONNECT заголовок `Host` равен цели (`2ip.io:443`), блок только с доменом такой запрос не принимает;
  2. глобально `order forward_proxy first`: `before route` ставит его после `handle`-блоков, и фолбэк-`handle` перехватывает запрос.
- `probe_resistance`, `hide_ip`, `hide_via`. Учётные данные: имя — часть `email` первого `vless_users` до `@`, пароль — его `id` (отдельного секрета нет; ротация VLESS UUID меняет и пароль naive).
- Сборка Caddy — по рецепту форка (`.github/workflows/build.yml`): клон Caddy нужной версии + два патча форка (`caddy-sing-quic-bbrv1.patch`, `caddy-read-idle-timeout.patch`), `xcaddy build --replace github.com/caddyserver/caddy/v2=<клон> --with github.com/caddyserver/forwardproxy=<форк>`. Форк закреплён полным SHA (`FORWARDPROXY_REF`), `scripts/build-artifacts.sh` падает, если `CADDY_VERSION` форка не совпадает с нашим. Версия Caddy остаётся v2.11.7 (понижение до v2.8.4 не нужно, duckdns сохраняется).
- Клиентская ссылка `naive+https://…` пишется ролью `client_artifacts` в `v2rayn-naive.txt` (формат — как экспортирует сам v2rayN: `security=tls&sni&type=tcp&headerType=none`).

## Последствия
- Проверено на golem-dev вручную: standalone naive-клиент → padding `Variant1`, `2ip.io` показывает IP сервера, HTTP и HTTPS проходят; и на патченом Caddy v2.11.7 + форк `e747854e`, и на Caddy v2.8.4 + форк `85634417`, то есть патч idle-timeout причиной первоначального отказа не был.
- Бинарник Caddy теперь один патченый на все хосты (включая prod, при следующей выкладке): `forward_proxy` без директивы в Caddyfile не работает, патч `bbrv1` относится к HTTP/3, а `protocols h1 h2` его не включает.
- При включении сайт на :443 отвечает на любой `Host` (фолбэк-лендинг), а не только на наш домен; без включения рендер прежний.
- На golem01 адрес из DuckDNS из РФ блокируется на уровне TCP (check-host, ru1/ru2: `Connection timed out`; из DE и PL открывается), поэтому на нём naive не может помочь; golem-dev достижим из РФ. Второй (исходящий) адрес того же сервера из РФ достижим: прямой тест с клиентской сети без TUN (2026-11-09) — TCP, HTTPS и naive-клиент с подменой адреса работают, в `access.log` виден адрес клиента, PROXY protocol приходит. Решение по адресу — `local/antiblock-roadmap.md`, Q18.
- Известный недостаток: на части CONNECT журнал Caddy получал `error HTTP 500: strconv.Atoi: parsing ""` (`handle_errors` использовал `{err.status_code}`, у ошибки закрытия туннеля кода нет); на трафик не влияет. Шаблон исправлен (`respond` только при числовом коде, Q17), эффект на реальном трафике не подтверждён.
- Не проверено (`open-questions.md`, Q17): простой туннеля дольше стандартных таймаутов (патч задаёт 24 ч для авторизованных CONNECT); поведение при IPv4-only на сервере; импорт ссылки в Throne.

## Пересмотреть
Если ТСПУ начнёт блокировать и naive, если форк перестанет собираться с нашей версией Caddy, или если у проекта появится отдельный серверный бинарник без патчей Caddy.
