# mihomo / clash-verge-rev

Читать, когда: добавляешь узел VPS в конфиг mihomo.

Схема vless+ws+tls с `alpn: http/1.1` проверена на практике (omp collab через mihomo).

Роль `client_artifacts` кладёт в `clients/generated/<host>/` два варианта конфигурации (секреты, вне git). Выбор зависит от цели:

| Цель | Файл | Что делать |
| :--- | :--- | :--- |
| Простой профиль, где весь трафик (или выбранная группа) идёт через один VPS; быстрая проверка подключения | `mihomo-node.yaml` (шаблон `clients/templates/mihomo-node.yaml.j2`) | вставить содержимое в секцию `proxies:` своего профиля и направить нужную группу или правила на узел `golem-<host>` |
| Большой общий профиль с подписками и несколькими группами, где через VPS должны идти только AI-домены и локальный порт к cliproxyapi | `mihomo-uni-fragment.yaml` (шаблон `clients/templates/mihomo-uni-fragment.yaml.j2`) | объединить с [профилем](https://github.com/mcgr0g/clash-cfg-mixer/blob/main/tests/fixtures/input/cfg.mih.uni.yml): провайдер `golem-ai` попадает в `proxy-providers:`, группа AI-доменов `Pinned-Proxy` получает `use: [golem-ai]`, при `GOLEM_CPA_ROUTE` добавляется `tunnels:` |

Узел из `mihomo-node.yaml`:

```yaml
proxies:
  - name: "golem-<host>"
    type: vless
    server: <domain>
    port: 443
    uuid: <uuid>
    network: ws
    tls: true
    udp: false
    servername: <domain>
    alpn: [http/1.1]
    client-fingerprint: chrome
    ws-opts:
      path: /<ws_path>
      headers: { Host: <domain> }
    ip-version: ipv4
```

Туннель к cliproxyapi: при `GOLEM_CPA_ROUTE` фрагмент `mihomo-uni-fragment.yaml` содержит верхнеуровневый объект `tunnels:` — локальный порт `GOLEM_CPA_LLM_PORT` (по умолчанию 18317) ведёт через группу с узлом golem на `cpa.golem:8317`. Агентам достаточно `http://127.0.0.1:<порт>` без прокси в настройках (ADR 0012, `ai-agents.md`).

Рекомендации:
- В группе, через которую идут Dolphin и AI-домены, оставляйте только узел golem (в общем профиле это `Pinned Proxy`; в простом профиле создайте группу `select` из одного узла `golem-<host>`). `DIRECT` внутрь не добавляйте: при падении узла трафик уйдёт напрямую и раскроет IP.
- Домен VPS в `DIRECT`/`NO_PROXY` для самого relay omp (`architecture/04-traffic-flows.md`, А).
- DNS: `enhanced-mode: fake-ip`, `respect-rules`, `proxy-server-nameserver` на DoH, чтобы домен VPS резолвился вне туннеля.
