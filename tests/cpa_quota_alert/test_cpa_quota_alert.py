"""Тесты cpa_quota_alert: пороги, окна, сообщения при старте, отказ ключа, повтор после сбоя Telegram.
Запуск: python3 -m unittest discover -s tests/cpa_quota_alert -v
Значения signals - из реального ответа prod (2026-11-09), email заменён."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "cpa_quota_alert", ROOT / "infra/ansible/roles/cpa_quota_alert/files/cpa_quota_alert.py")
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)

NOW = 1794200000
RESET_5H = 1794243000
RESET_7D = 1794250800
EMAIL = "someone@example.invalid"
CFG = {"host": "golem01", "thresholds": [15, 10, 5], "quota_providers": ["claude"], "display_tz": "UTC"}


def signals(util5h, util7d="0.07", reset5h=RESET_5H):
    return {
        "Anthropic-Ratelimit-Unified-5h-Reset": str(reset5h),
        "Anthropic-Ratelimit-Unified-5h-Status": "allowed",
        "Anthropic-Ratelimit-Unified-5h-Utilization": util5h,
        "Anthropic-Ratelimit-Unified-7d-Reset": str(RESET_7D),
        "Anthropic-Ratelimit-Unified-7d-Status": "allowed",
        "Anthropic-Ratelimit-Unified-7d-Utilization": util7d,
        "Anthropic-Ratelimit-Unified-Representative-Claim": "five_hour",
    }


def claude_entry(util5h="0.16", **extra):
    entry = {
        "id": f"claude-6cd601b3-{EMAIL}.json", "provider": "claude", "auth_index": "dc2f445b7a00a3ba",
        "email": EMAIL, "status": "active", "unavailable": False, "requires_sign_in": False,
        "quota_blocked": False, "disabled": False,
        "quota": {"observed_at": "2026-11-09T08:08:01.405016042-05:00", "signals": signals(util5h)},
    }
    entry.update(extra)
    return entry


class Harness:
    """Каталоги состояния/runtime и заглушки CPA и Telegram."""

    def __init__(self, test):
        self._dirs = [tempfile.TemporaryDirectory() for _ in range(2)]
        for d in self._dirs:
            test.addCleanup(d.cleanup)
        self.state = Path(self._dirs[0].name)
        self.runtime = Path(self._dirs[1].name)
        self.sent = []
        self.fail_send = False
        self.payload = {"files": []}
        self.fetches = 0
        self.auth_error = False

    def fetch(self):
        self.fetches += 1
        if self.auth_error:
            raise q.AuthError("HTTP 401")
        return self.payload

    def send(self, text):
        if self.fail_send:
            raise RuntimeError("Telegram недоступен")
        self.sent.append(text)

    def run(self, now=NOW):
        return q.run(CFG, self.state, self.runtime, now, self.fetch, self.send)

    def reboot(self):
        """Перезагрузка: /run очищается, состояние в StateDirectory остаётся."""
        (self.runtime / q.STARTED).unlink()
        self.sent.clear()


class LabelTests(unittest.TestCase):
    def test_label_без_email(self):
        self.assertEqual(q.account_label(claude_entry()), "claude-6cd601b3")

    def test_нестандартный_id_не_раскрывает_email(self):
        label = q.account_label(claude_entry(id=f"{EMAIL}.json"))
        self.assertEqual(label, "claude-dc2f445b7a00a3ba")
        self.assertNotIn("example", label)


class WindowParseTests(unittest.TestCase):
    def test_остаток_это_100_минус_доля(self):
        w = q.claude_windows(signals("0.16"))
        self.assertAlmostEqual(w["5h"][0], 84.0)
        self.assertEqual(w["5h"][1], RESET_5H)
        self.assertAlmostEqual(w["7d"][0], 93.0)

    def test_пустые_signals_не_ошибка(self):
        self.assertEqual(q.claude_windows({}), {})

    def test_половина_окна_это_ошибка_формата(self):
        with self.assertRaises(q.QuotaFormatError):
            q.claude_windows({"Anthropic-Ratelimit-Unified-5h-Utilization": "0.5"})


class ThresholdTests(unittest.TestCase):
    TH = [15, 10, 5]

    def ev(self, prev, remaining, reset=RESET_5H, now=NOW):
        return q.evaluate_window(prev, remaining, reset, self.TH, now)

    def test_выше_порога_тихо(self):
        state, events = self.ev(None, 84)
        self.assertEqual((state, events), ({"reset": RESET_5H, "level": None}, []))

    def test_граница_включительно(self):
        self.assertEqual(self.ev(None, 15)[1], [("alert", 15)])

    def test_первое_наблюдение_сразу_на_4_процентах_даёт_один_самый_глубокий_алерт(self):
        state, events = self.ev(None, 4)
        self.assertEqual(events, [("alert", 5)])
        self.assertEqual(state["level"], 5)

    def test_спуск_15_10_5_по_одному_сообщению(self):
        state = None
        got = []
        for remaining in (14, 13, 9, 9, 4):
            state, events = self.ev(state, remaining)
            got += [e for e in events]
        self.assertEqual(got, [("alert", 15), ("alert", 10), ("alert", 5)])

    def test_повтор_на_том_же_уровне_молчит(self):
        state, _ = self.ev(None, 12)
        self.assertEqual(self.ev(state, 11)[1], [])

    def test_сброс_окна_даёт_восстановлено_и_новый_алерт_если_снова_низко(self):
        state, _ = self.ev(None, 8)
        new_reset = RESET_5H + 5 * 3600
        state2, events = self.ev(state, 12, reset=new_reset, now=RESET_5H + 60)
        self.assertEqual(events, [("recovered", None), ("alert", 15)])
        self.assertEqual(state2, {"reset": new_reset, "level": 15})

    def test_окно_закончилось_а_снимок_старый_восстановлено_без_нового_алерта(self):
        state, _ = self.ev(None, 8)
        state2, events = self.ev(state, 8, now=RESET_5H + 60)
        self.assertEqual((state2, events), (None, [("recovered", None)]))

    def test_старый_снимок_без_состояния_ничего_не_делает(self):
        self.assertEqual(self.ev(None, 3, now=RESET_5H + 1), (None, []))

    def test_остаток_снова_выше_порога_в_том_же_окне_восстановлено(self):
        state, _ = self.ev(None, 8)
        state2, events = self.ev(state, 40)
        self.assertEqual(events, [("recovered", None)])
        self.assertIsNone(state2["level"])


class RunTests(unittest.TestCase):
    def setUp(self):
        self.h = Harness(self)

    def test_старт_и_ни_одного_порога_одно_сообщение_без_email(self):
        self.h.payload = {"files": [claude_entry("0.16")]}
        self.assertEqual(self.h.run(), 0)
        self.assertEqual(len(self.h.sent), 1)
        text = self.h.sent[0]
        self.assertIn("запущен", text)
        self.assertIn("claude-6cd601b3: 5h 84%, 7d 93%", text)
        self.assertNotIn(EMAIL, text)

    def test_второй_проход_без_изменений_молчит(self):
        self.h.payload = {"files": [claude_entry("0.16")]}
        self.h.run()
        self.h.sent.clear()
        self.h.run(NOW + 900)
        self.assertEqual(self.h.sent, [])

    def test_перезагрузка_снова_шлёт_запущен_но_не_повторяет_порог(self):
        self.h.payload = {"files": [claude_entry("0.92")]}
        self.h.run()
        self.assertEqual(len(self.h.sent), 2)  # запущен + порог 15 на 8% остатка -> уровень 10
        self.assertIn("остаток 8%", self.h.sent[1])
        self.assertIn("порог 10%", self.h.sent[1])
        self.h.reboot()
        self.h.run(NOW + 900)
        self.assertEqual(len(self.h.sent), 1)
        self.assertIn("запущен", self.h.sent[0])

    def test_новый_аккаунт_после_старта(self):
        self.h.payload = {"files": [claude_entry()]}
        self.h.run()
        self.h.sent.clear()
        second = claude_entry(id=f"claude-aaaa1111-{EMAIL}.json", auth_index="ffff")
        self.h.payload = {"files": [claude_entry(), second]}
        self.h.run(NOW + 900)
        self.assertEqual(len(self.h.sent), 1)
        self.assertIn("новый аккаунт", self.h.sent[0])
        self.assertIn("claude-aaaa1111", self.h.sent[0])

    def test_аккаунт_без_квот_проверяется_только_по_статусу(self):
        gem = {"id": f"gemini-1234abcd-{EMAIL}.json", "provider": "gemini", "auth_index": "g", "status": "active",
               "unavailable": False, "requires_sign_in": False, "quota_blocked": False, "disabled": False}
        self.h.payload = {"files": [gem]}
        self.h.run()
        self.assertIn("gemini-1234abcd: статус active", self.h.sent[0])
        self.h.sent.clear()
        self.h.payload = {"files": [dict(gem, requires_sign_in=True)]}
        self.h.run(NOW + 900)
        self.assertEqual(len(self.h.sent), 1)
        self.assertIn("требуется повторный вход", self.h.sent[0])

    def test_ключ_не_принят_одно_сообщение_и_больше_ни_одного_запроса(self):
        self.h.auth_error = True
        self.assertEqual(self.h.run(), 1)
        self.assertEqual(len(self.h.sent), 1)
        self.assertIn("не принял ключ", self.h.sent[0])
        self.assertEqual(self.h.run(NOW + 900), 1)
        self.assertEqual(self.h.fetches, 1)
        self.assertEqual(len(self.h.sent), 1)

    def test_сбой_telegram_не_фиксирует_порог_и_алерт_повторится(self):
        self.h.payload = {"files": [claude_entry("0.16")]}
        self.h.run()  # запущен; маркер старта есть
        self.h.sent.clear()
        self.h.payload = {"files": [claude_entry("0.95")]}
        self.h.fail_send = True
        with self.assertRaises(RuntimeError):
            self.h.run(NOW + 900)
        self.h.fail_send = False
        self.h.run(NOW + 1800)
        self.assertEqual(len(self.h.sent), 1)
        self.assertIn("порог 5%", self.h.sent[0])
        self.h.sent.clear()
        self.h.run(NOW + 2700)
        self.assertEqual(self.h.sent, [])

    def test_данные_пустые_signals_значит_нет_данных_а_не_ошибка(self):
        entry = claude_entry()
        entry["quota"] = {"observed_at": "2026-11-09T08:08:01.405016042-05:00", "signals": {}}
        self.h.payload = {"files": [entry]}
        self.assertEqual(self.h.run(), 0)
        self.assertIn("данных по квоте нет", self.h.sent[0])


if __name__ == "__main__":
    unittest.main()
