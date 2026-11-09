#!/usr/bin/env python3
"""Алерты остатка квот OAuth-аккаунтов CPA в Telegram.

Раз в интервал таймера делает один GET /v8/management/credentials, считает остаток
по окнам лимита и шлёт сообщение, когда остаток впервые опустился до очередного порога.
Только stdlib (Python 3.11+: tomllib). Настройки - TOML (без секретов), секреты - из окружения:
CPA_MANAGEMENT_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID. Каталоги - от systemd:
STATE_DIRECTORY (переживает перезагрузку), RUNTIME_DIRECTORY (очищается при загрузке).

Сообщения: «запущен» после каждой загрузки сервера, новый аккаунт, порог остатка,
окно сброшено/остаток восстановлен, проблема аккаунта, ключ management не принят.
Email аккаунтов не используется: подпись берётся из id вида «<провайдер>-<хеш>-<email>».
"""
import json
import os
import re
import sys
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

AUTH_FAILED = "auth-failed"
STARTED = "started"
STATE_FILE = "state.json"


class AuthError(Exception):
    """CPA отклонил ключ management (401/403)."""


class ConfigError(Exception):
    pass


class QuotaFormatError(Exception):
    pass


# ---------- чистая логика ----------

def account_label(entry):
    """`claude-6cd601b3` из id `claude-6cd601b3-<email>`; без email при любом другом формате."""
    provider = entry.get("provider")
    parts = str(entry.get("id") or "").split("-", 2)
    if len(parts) == 3 and parts[0] == provider and parts[1]:
        return f"{parts[0]}-{parts[1]}"
    return f"{provider}-{entry.get('auth_index') or '?'}"


def claude_windows(signals):
    """{'5h': (остаток %, reset epoch), '7d': ...} из Anthropic-Ratelimit-Unified-*; пустой signals - пустой результат."""
    low = {k.lower(): v for k, v in signals.items()}
    out = {}
    for name in ("5h", "7d"):
        prefix = f"anthropic-ratelimit-unified-{name}-"
        util, reset = low.get(prefix + "utilization"), low.get(prefix + "reset")
        if util is None and reset is None:
            continue
        if util is None or reset is None:
            raise QuotaFormatError(f"окно {name}: есть только одно из utilization/reset")
        try:
            out[name] = (100.0 - 100.0 * float(util), int(reset))
        except ValueError:
            raise QuotaFormatError(f"окно {name}: не число utilization={util!r} reset={reset!r}") from None
    return out


WINDOW_PARSERS = {"claude": claude_windows}


def level_for(remaining, thresholds):
    """Самый глубокий пройденный порог (остаток <= порога) или None."""
    crossed = [t for t in thresholds if remaining <= t]
    return min(crossed) if crossed else None


def evaluate_window(prev, remaining, reset, thresholds, now):
    """prev - {'reset', 'level'} или None. Возвращает (новое состояние или None, [('alert', порог) | ('recovered', None)])."""
    events = []
    if prev is not None and (now >= prev["reset"] or reset != prev["reset"]):
        # окно закончилось или сменилось: прошлое состояние закрыто
        if prev["level"] is not None:
            events.append(("recovered", None))
        prev = None
    if reset <= now:
        # снимок относится к закончившемуся окну: фактический остаток неизвестен
        return None, events
    prev_level = prev["level"] if prev else None
    level = level_for(remaining, thresholds)
    if level is None:
        if prev_level is not None:
            events.append(("recovered", None))
        return {"reset": reset, "level": None}, events
    if prev_level is None or level < prev_level:
        events.append(("alert", level))
        return {"reset": reset, "level": level}, events
    return {"reset": reset, "level": prev_level}, events


def account_problem(entry):
    if entry.get("requires_sign_in"):
        return "требуется повторный вход"
    if entry.get("quota_blocked"):
        return "квота исчерпана (quota_blocked)"
    if entry.get("unavailable"):
        return "аккаунт недоступен (unavailable)"
    if entry.get("status") != "active":
        return f"статус {entry.get('status')}"
    return None


def parse_rfc3339(text):
    # fromisoformat принимает не более 6 знаков дроби; CPA отдаёт наносекунды
    return datetime.fromisoformat(re.sub(r"(\.\d{6})\d+", r"\1", text))


# ---------- сообщения ----------

def fmt_time(epoch_or_dt, tz):
    dt = epoch_or_dt if isinstance(epoch_or_dt, datetime) else datetime.fromtimestamp(epoch_or_dt, tz=timezone.utc)
    return dt.astimezone(tz).strftime("%d.%m %H:%M")


def summary_line(label, entry, windows, problem, quota_providers):
    if problem:
        return f"{label}: {problem}"
    if windows:
        return f"{label}: " + ", ".join(f"{n} {rem:.0f}%" for n, (rem, _) in windows.items())
    if entry.get("provider") in quota_providers:
        return f"{label}: данных по квоте нет (запросов после входа не было)"
    return f"{label}: статус {entry.get('status')}"


# ---------- состояние ----------

def load_state(state_dir):
    path = state_dir / STATE_FILE
    if not path.exists():
        return {"accounts": [], "windows": {}, "flags": {}}
    return json.loads(path.read_text())


def save_state(state_dir, state):
    tmp = state_dir / (STATE_FILE + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1))
    os.replace(tmp, state_dir / STATE_FILE)


# ---------- основной проход ----------

def run(cfg, state_dir, runtime_dir, now, fetch, send):
    """Один проход. 0 - всё штатно, 1 - ошибка (юнит failed, видно в systemctl --failed)."""
    if (state_dir / AUTH_FAILED).exists():
        print("опрос остановлен: CPA ранее не принял ключ management; после исправления удалите "
              f"{state_dir / AUTH_FAILED}", file=sys.stderr)
        return 1
    host, thresholds, quota_providers = cfg["host"], cfg["thresholds"], cfg["quota_providers"]
    tz = ZoneInfo(cfg["display_tz"]) if cfg["display_tz"] != "UTC" else timezone.utc
    try:
        payload = fetch()
    except AuthError as err:
        # флаг до отправки: больше ни одной попытки с этим ключом (5 неверных = бан 127.0.0.1 на 30 мин)
        (state_dir / AUTH_FAILED).write_text(f"{now}\n")
        send(f"golem {host}: CPA не принял ключ management ({err}); опрос квот остановлен, см. docs/components/cliproxyapi.md")
        return 1

    state = load_state(state_dir)
    try:
        infos = []
        for entry in payload["files"]:
            if entry.get("disabled"):
                continue
            provider = entry.get("provider")
            quota = entry.get("quota") or {}
            windows = {}
            if provider in quota_providers:
                windows = WINDOW_PARSERS[provider](quota.get("signals") or {})
            infos.append((entry, account_label(entry), account_problem(entry), windows))

        def emit(text, apply):
            send(text)
            apply()

        started = runtime_dir / STARTED
        if not started.exists():
            lines = [summary_line(lb, e, w, p, quota_providers) for e, lb, p, w in infos] or ["аккаунтов нет"]
            known = [lb for _, lb, _, _ in infos]
            emit(f"golem {host}: мониторинг квот CPA запущен\n" + "\n".join(lines),
                 lambda: state.__setitem__("accounts", sorted(set(state["accounts"]) | set(known))))
            started.touch()
        else:
            for entry, label, problem, windows in infos:
                if label not in state["accounts"]:
                    line = summary_line(label, entry, windows, problem, quota_providers)
                    emit(f"golem {host}: новый аккаунт CPA\n{line}", lambda lb=label: state["accounts"].append(lb))

        seen = set()
        for entry, label, problem, windows in infos:
            flag = f"status:{label}"
            if problem != state["flags"].get(flag):
                if problem:
                    emit(f"golem {host}: {label}: {problem}", lambda f=flag, p=problem: state["flags"].__setitem__(f, p))
                else:
                    emit(f"golem {host}: {label}: снова в порядке", lambda f=flag: state["flags"].pop(f))
            observed = (entry.get("quota") or {}).get("observed_at")
            snapshot = f", снимок {fmt_time(parse_rfc3339(observed), tz)}" if observed else ""
            for name, (remaining, reset) in windows.items():
                key = f"{label}|{name}"
                seen.add(key)
                new, events = evaluate_window(state["windows"].get(key), remaining, reset, thresholds, now)

                def settle(k=key, n=new):
                    if n is None:
                        state["windows"].pop(k, None)
                    else:
                        state["windows"][k] = n

                if not events:
                    settle()
                    continue
                for i, (kind, level) in enumerate(events):
                    if kind == "alert":
                        text = (f"golem {host}: {label} окно {name}: остаток {remaining:.0f}% "
                                f"(порог {level}%), сброс {fmt_time(reset, tz)}{snapshot}")
                    else:
                        text = f"golem {host}: {label} окно {name}: лимит восстановлен"
                    emit(text, settle if i == len(events) - 1 else (lambda: None))

        # окна аккаунтов, которых в ответе уже нет: закрыть молча после сброса
        for key in [k for k, v in state["windows"].items() if k not in seen and now >= v["reset"]]:
            del state["windows"][key]
    finally:
        save_state(state_dir, state)
    return 0


# ---------- ввод-вывод ----------

def load_config(path):
    cfg = tomllib.loads(Path(path).read_text())
    for key in ("host", "api_url", "telegram_api", "timeout_seconds", "thresholds", "quota_providers", "display_tz"):
        if key not in cfg:
            raise ConfigError(f"в {path} нет параметра {key}")
    th = cfg["thresholds"]
    if not th or any(not isinstance(t, int) or not 0 < t < 100 for t in th):
        raise ConfigError("thresholds: непустой список целых от 1 до 99")
    unknown = sorted(set(cfg["quota_providers"]) - set(WINDOW_PARSERS))
    if unknown:
        raise ConfigError(f"quota_providers: нет разбора формата для {unknown}")
    return cfg


def make_fetch(cfg, key):
    def fetch():
        req = urllib.request.Request(cfg["api_url"], headers={"Authorization": f"Bearer {key}"})
        try:
            with urllib.request.urlopen(req, timeout=cfg["timeout_seconds"]) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as err:
            if err.code in (401, 403):
                raise AuthError(f"HTTP {err.code}") from None
            raise RuntimeError(f"CPA ответил HTTP {err.code}") from None
    return fetch


def make_send(cfg, token, chat):
    def send(text):
        print(text, file=sys.stderr)
        if not token or not chat:
            return
        url = f"{cfg['telegram_api']}/bot{token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=cfg["timeout_seconds"]) as resp:
                resp.read()
        except urllib.error.HTTPError as err:
            raise RuntimeError(f"Telegram ответил HTTP {err.code}") from None
    return send


def main(argv):
    if len(argv) != 2:
        print("использование: cpa_quota_alert.py <settings.toml>", file=sys.stderr)
        return 2
    env = os.environ
    try:
        cfg = load_config(argv[1])
        key = env["CPA_MANAGEMENT_KEY"]
        state_dir, runtime_dir = Path(env["STATE_DIRECTORY"]), Path(env["RUNTIME_DIRECTORY"])
    except (ConfigError, KeyError) as err:
        print(f"настройка: {err}", file=sys.stderr)
        return 2
    send = make_send(cfg, env.get("TELEGRAM_BOT_TOKEN"), env.get("TELEGRAM_CHAT_ID"))
    try:
        return run(cfg, state_dir, runtime_dir, int(time.time()), make_fetch(cfg, key), send)
    except (OSError, RuntimeError, QuotaFormatError) as err:
        print(f"ошибка: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
