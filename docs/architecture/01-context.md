# C4 L1 — System Context

Читать, когда: нужна картина «кто пользуется системой и с чем она связана».

Нотация: C4 в Mermaid (`C4Context`/`C4Container`/`C4Deployment`), решение — `decisions/0008-c4-mermaid.md`. Диаграммы живут рядом с описанием, один уровень — один файл.

```mermaid
C4Context
  title Golem — System Context
  Person(owner, "Владелец", "Телефон (браузер) и MacBook")
  System(golem, "Golem VPS", "Один домен на 443")
  System_Ext(omp, "omp (MacBook)", "Агент-хост, подключается к relay как host")
  System_Ext(dolphin, "Dolphin Anty / агенты", "Клиент VLESS через mihomo на Mac")
  System_Ext(llm, "LLM-провайдеры", "Upstream для cliproxyapi")
  System_Ext(ai, "Западные AI-сервисы, биллинг", "Видят IP VPS")
  System_Ext(resi, "Static ISP прокси", "Опционально")
  System_Ext(le, "Let's Encrypt / DuckDNS", "Сертификат и DNS")
  Rel(owner, golem, "Веб-клиент collab", "HTTPS")
  Rel(omp, golem, "Комната collab", "WSS /r/*")
  Rel(omp, golem, "LLM-запросы", "HTTPS, Bearer")
  Rel(dolphin, golem, "VLESS+WS+TLS", "443")
  Rel(golem, llm, "Запросы моделей", "HTTPS")
  Rel(golem, ai, "Выходной трафик", "TCP")
  Rel(golem, resi, "Цепочка (опц.)", "SOCKS5/HTTP")
  Rel(golem, le, "ACME, обновление IP", "HTTPS")
```

Границы: трафик содержимого collab шифруется end-to-end (AES-256-GCM), relay видит только room id и шифртекст. Ссылка с ключом = пароль.
