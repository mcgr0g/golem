# Роль cliproxyapi

Релиз по sha256, конфиг v8 с bcrypt-хэшем, панель с пиннингом, юнит. `docs/components/cliproxyapi.md`. Необязательная переменная `cliproxyapi_openai_compatibility` добавляет провайдеров `openai-compatibility` (в Lima — фиктивный апстрим, `tests/fake-llm/`).
SSE heartbeat — `cliproxyapi_keepalive_seconds` / `cliproxyapi_keepalive_before_first_token` (по умолчанию выключен).
