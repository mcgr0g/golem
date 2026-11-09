# Алерты квот OAuth-аккаунтов CPA

Читать, когда: настраиваешь или чинишь уведомления об остатке лимитов Claude/Codex в Telegram.

Роль `cpa_quota_alert` (после `ops_timers` в `site.yml`: `/etc/golem/telegram.env` создаёт она). Решение и отвергнутые варианты - `decisions/0016-cpa-quota-alert-script.md`.

## Что делает
Раз в `cpa_quota_alert_interval` (15 мин, `OnBootSec=3min`) один запрос `GET /v8/management/credentials` на loopback CPA с открытым ключом management. Остаток считается по пассивным сигналам, которые CPA сам запоминает из ответов апстрима; живых запросов к провайдерам скрипт не делает, поэтому без трафика снимок старый (время снимка есть в сообщении).

Формат `quota.signals` Claude (проверен на prod 2026-11-09): `Anthropic-Ratelimit-Unified-{5h,7d}-{Utilization,Status,Reset}`. `Utilization` - доля 0..1 строкой, остаток % = `100 - 100*Utilization`; `Reset` - epoch в секундах. Сверка с веб-интерфейсом Claude (по словам владельца: «Лимит на 5 часов 83%», сброс 19:50): снимок CPA 08:08 EST дал `Utilization` 0.16, то есть остаток 84%; разница в 1 п.п. объясняется временем между снимком и сверкой (вывод, повторно не снималось).

Проверяются только аккаунты, по которым выполнен вход (что отдаёт `/credentials`). У провайдеров без разбора квот (`gemini`, `antigravity`, `kimi`, `xai`, а также `codex`, пока формат не проверен) - только `status`, `unavailable`, `quota_blocked`, `requires_sign_in`.

## Сообщения
| Событие | Когда |
| :--- | :--- |
| «мониторинг квот CPA запущен» + остаток по аккаунтам | первый успешный опрос после каждой загрузки сервера (маркер в `/run/golem-cpa-quota`, очищается при загрузке) и после первой раскатки |
| «новый аккаунт CPA» | в ответе появился аккаунт, которого нет в состоянии |
| остаток до порога (`15/10/5`%) | остаток окна впервые стал `<=` порога; на каждый более глубокий порог одно сообщение; первое наблюдение сразу на 4% даёт одно сообщение (порог 5) |
| «лимит восстановлен» | окно сброшено (`Reset` прошёл или сменился) или остаток снова выше порога |
| проблема аккаунта / «снова в порядке» | `requires_sign_in`, `quota_blocked`, `unavailable` или статус не `active` |
| «CPA не принял ключ management» | HTTP 401/403: флаг `auth-failed`, одно сообщение, опросы прекращаются (одна неверная попытка из пяти, бан `127.0.0.1` на 30 мин затронул бы и панель) |

Подпись аккаунта - первые два сегмента `id` (`claude-6cd601b3`), email нигде не используется. Если `id` не подходит под шаблон `<провайдер>-<хеш>-...`, подпись `<провайдер>-<auth_index>`.

## Файлы и состояние
- `/usr/local/lib/golem/cpa_quota_alert.py` - скрипт, только stdlib (Python 3.11: `tomllib`, `zoneinfo`; роль проверяет импорт).
- `/etc/golem/cpa-quota-alert.toml` (0644) - настройки из шаблона роли: URL, `thresholds`, `quota_providers`, `display_tz`; без секретов.
- `/etc/golem/cpa-monitor.env` (0600) - `CPA_MANAGEMENT_KEY` из SOPS; токен Telegram - в `/etc/golem/telegram.env`.
- Состояние `state.json` в `StateDirectory=golem-cpa-quota` (`/var/lib/private/golem-cpa-quota`, переживает перезагрузку): `accounts`, `windows` (`reset`, `level`), `flags`. Сообщение учитывается в состоянии только после успешной отправки: сбой Telegram = повтор в следующий запуск, юнит `failed` (`systemctl --failed`, `resource-alert`).
- Юнит `cpa-quota-alert.service` (`Type=oneshot`, `DynamicUser`, `MemoryMax=64M`) и `cpa-quota-alert.timer`.

## Эксплуатация
- Ручной запуск: `sudo systemctl start cpa-quota-alert.service`, лог - `journalctl -u cpa-quota-alert.service` (все сообщения дублируются в журнал).
- Опрос остановлен после 401/403: сменить ключ (`components/cliproxyapi.md`, «Экстренная смена ключа management»), затем `sudo rm /var/lib/private/golem-cpa-quota/auth-failed` и запуск службы.
- Новый провайдер квот: добавить разбор окон в `WINDOW_PARSERS` скрипта по реальному ответу и фикстуру в тест, затем имя в `cpa_quota_alert_quota_providers`.

## Проверено
- Тесты логики: `python3 -m unittest discover -s tests/cpa_quota_alert -v` (22 теста: пороги, сброс окна, перезагрузка, новый аккаунт, ключ не принят, сбой Telegram).
- Lima (Debian 12, Python 3.11.2, 2026-11-09): роль применяется, повторный прогон `changed=0`; служба получает ответ реального CPA (`files: []`, ключ из SOPS принят); сквозной прогон со заглушками CPA и Telegram на значениях prod: старт, порог, повтор после перезагрузки, ключ не принят (один запрос).
- Telegram из Lima недостижим (нет маршрута к `api.telegram.org`); доставка проверена только на заглушке.
- Не проверено: работа на prod; формат Codex; значения `Status` окна при превышении лимита; содержимое `signals` после сброса окна; что панель CPA позволяет менять ключ management (`open-questions.md`, Q20).
