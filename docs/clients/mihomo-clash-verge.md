# mihomo / clash-verge-rev

Читать, когда: добавляешь узел VPS в конфиг mihomo.

Схема vless+ws+tls с `alpn: http/1.1` проверена на практике (omp collab через mihomo).

Шаблон узла (плейсхолдеры подставляет Ansible из `clients/templates/mihomo-node.yaml.j2`):

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

Рекомендации:
- Для Dolphin и агентов — отдельная группа `select` из одного узла `golem-*` (никогда `DIRECT` внутри группы: при падении узла трафик уйдёт напрямую и раскроет IP).
- Домен VPS в `DIRECT`/`NO_PROXY` для самого relay omp (`architecture/04-traffic-flows.md`, А).
- Цепочка с static ISP прокси: узел с `dialer-proxy: golem-<host>`.
- DNS: `enhanced-mode: fake-ip`, `respect-rules`, `proxy-server-nameserver` на DoH, чтобы домен VPS резолвился вне туннеля.
- Обязательно для порта mixed на LAN: `authentication:` — иначе открытый прокси.
- Подписки/`proxy-providers` для узла VPS не нужны (ADR 0003): фрагмент вставляется как `proxies:`.
