"""History that survives restarts, the history/CSV endpoints, and the live-readiness report."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import main, readiness
from backend.config import load_settings
from backend.paper_engine import PaperEngine


class JournalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "desk.sqlite3")
        self.env = patch.dict(os.environ, {"NEXUS_STATE_DB": self.db, "NEXUS_CONTROL_PASSWORD": "test-secret-123"})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_button_history_logs_and_decisions_survive_a_restart(self) -> None:
        first = PaperEngine(load_settings())
        first._command("PAUSE", "Paper observer paused.")
        first._log("BTC/USD WAIT: no trigger")
        restarted = PaperEngine(load_settings())  # same database file, brand-new process
        self.assertEqual([c["action"] for c in restarted.commands], ["PAUSE"])
        self.assertEqual([r["message"] for r in restarted.logs], ["BTC/USD WAIT: no trigger"])
        self.assertEqual(restarted.decisions[0]["reason"], "BTC/USD WAIT: no trigger")

    def test_a_broken_journal_never_stops_the_engine(self) -> None:
        engine = PaperEngine(load_settings())
        with patch.object(engine.store, "append_event", side_effect=RuntimeError("disk full")):
            engine._command("REFRESH", "x")
            engine._log("still running")
        self.assertEqual(engine.journal_errors, 2)
        self.assertEqual(engine.commands[0]["action"], "REFRESH")  # in-memory copy still kept

    def test_settings_changes_are_recorded_with_old_and_new_values(self) -> None:
        engine = PaperEngine(load_settings())
        header = {"x-nexus-control-password": "test-secret-123"}
        with patch.object(main, "get_engine", return_value=engine), TestClient(main.app) as client:
            os.environ.pop("NEXUS_SCALP_POSITION_USD", None)
            reply = client.post("/api/settings", headers=header,
                                json={"changes": {"NEXUS_SCALP_POSITION_USD": "40"}, "confirmation": "I_ACCEPT_CONFIG_RISK"})
            self.assertEqual(reply.status_code, 200)
            rows = client.get("/api/history?kind=settings_change").json()["events"]
        change = rows[0]["data"]["changes"]["NEXUS_SCALP_POSITION_USD"]
        self.assertEqual(change, {"from": "", "to": "40"})

    def test_history_filters_by_type_and_date_and_pages_backwards(self) -> None:
        engine = PaperEngine(load_settings())
        for i in range(5):
            engine._log(f"line {i}")
        engine._command("RESUME", "r")
        with patch.object(main, "get_engine", return_value=engine), TestClient(main.app) as client:
            logs = client.get("/api/history?kind=log&limit=2").json()
            self.assertEqual([e["kind"] for e in logs["events"]], ["log", "log"])
            older = client.get(f"/api/history?kind=log&limit=10&before={logs['nextBefore']}").json()
            self.assertEqual(len(older["events"]), 3)
            self.assertEqual(client.get("/api/history?since=2999-01-01").json()["events"], [])
            self.assertEqual(client.get("/api/history?since=not-a-date").status_code, 400)
            self.assertIn("command", client.get("/api/history").json()["kinds"])

    def test_csv_download_has_header_and_rows_and_neutralises_spreadsheet_formulas(self) -> None:
        engine = PaperEngine(load_settings())
        engine._log("hello")
        with patch.object(main, "get_engine", return_value=engine), TestClient(main.app) as client:
            reply = client.get("/api/history.csv?kind=log")
        self.assertEqual(reply.status_code, 200)
        self.assertTrue(reply.text.startswith("id,time_utc,kind,detail_json"))
        self.assertIn("hello", reply.text)
        self.assertEqual(main._csv_safe("=HYPERLINK(1)"), "'=HYPERLINK(1)")
        self.assertEqual(main._csv_safe("log"), "log")

    def test_history_says_so_when_no_journal_is_configured(self) -> None:
        with patch.dict(os.environ, {"NEXUS_STATE_DB": ""}):
            engine = PaperEngine(load_settings())
            with patch.object(main, "get_engine", return_value=engine), TestClient(main.app) as client:
                body = client.get("/api/history").json()
                self.assertFalse(body["enabled"])
                self.assertEqual(client.get("/api/history.csv").status_code, 404)

    def test_history_page_is_served(self) -> None:
        with TestClient(main.app) as client:
            reply = client.get("/history")
        self.assertEqual(reply.status_code, 200)
        self.assertIn("History and readiness", reply.text)


class ReadinessTests(unittest.TestCase):
    ALL_SET = {
        "KRAKEN_API_KEY": "k", "KRAKEN_API_SECRET": "s",
        "NEXUS_FEE_MAKER_PCT": "0.25", "NEXUS_FEE_TAKER_PCT": "0.40",
        "NEXUS_MAX_ORDER_USD": "25", "NEXUS_MAX_DAILY_LOSS_USD": "50", "NEXUS_MAX_OPEN_EXPOSURE_USD": "100",
        "NEXUS_CONTROL_PASSWORD": "a-long-unique-password",
    }

    def _report(self, env: dict[str, str], store=None) -> dict:
        with patch.dict(os.environ, env, clear=False):
            for name in ("KRAKEN_API_KEY", "KRAKEN_API_SECRET", "NEXUS_FEE_MAKER_PCT", "NEXUS_FEE_TAKER_PCT",
                         "NEXUS_MAX_ORDER_USD", "NEXUS_MAX_DAILY_LOSS_USD", "NEXUS_MAX_OPEN_EXPOSURE_USD",
                         "NEXUS_CONTROL_PASSWORD"):
                if name not in env:
                    os.environ.pop(name, None)
            return readiness.evaluate(load_settings(), store, os.environ)

    def status(self, report: dict, key: str) -> str:
        return next(g["status"] for g in report["gates"] if g["key"] == key)

    def test_fresh_install_fails_every_setup_check_and_says_how_to_fix_each(self) -> None:
        report = self._report({})
        self.assertFalse(report["liveAllowed"])
        for key in ("exchange_keys", "fees", "risk_caps", "control_password", "verification", "switch_on"):
            self.assertEqual(self.status(report, key), "fail", key)
        for gate in report["gates"]:
            if gate["status"] == "fail" and gate["key"] != "switch_on":
                self.assertTrue(gate["fix"], gate["key"] + " has no instruction")

    def test_each_missing_item_is_reported_on_its_own(self) -> None:
        for missing, gate_key in (("KRAKEN_API_SECRET", "exchange_keys"), ("NEXUS_FEE_TAKER_PCT", "fees"),
                                  ("NEXUS_MAX_DAILY_LOSS_USD", "risk_caps"), ("NEXUS_CONTROL_PASSWORD", "control_password")):
            env = {k: v for k, v in self.ALL_SET.items() if k != missing}
            self.assertEqual(self.status(self._report(env), gate_key), "fail", missing)
        self.assertEqual(self.status(self._report({**self.ALL_SET, "NEXUS_CONTROL_PASSWORD": "short"}), "control_password"), "fail")

    def test_live_stays_blocked_even_when_every_setup_check_passes(self) -> None:
        report = self._report(self.ALL_SET)
        for key in ("exchange_keys", "fees", "risk_caps", "control_password"):
            self.assertEqual(self.status(report, key), "pass", key)
        self.assertFalse(report["liveAllowed"])
        # checks that need an exchange adapter are honest about not being done
        for key in ("keys_work", "key_permissions", "balance"):
            self.assertEqual(self.status(report, key), "not_checked", key)

    def test_verification_gate_needs_a_recent_passing_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"NEXUS_STATE_DB": str(Path(tmp) / "d.sqlite3")}):
                engine = PaperEngine(load_settings())
            store = engine.store
            self.assertEqual(self.status(self._report(self.ALL_SET, store), "verification"), "fail")
            store.append_event("verification", {"ok": False}, "2999-01-01T00:00:00Z")
            self.assertEqual(self.status(self._report(self.ALL_SET, store), "verification"), "fail")
            store.append_event("verification", {"ok": True}, "2000-01-01T00:00:00Z")
            self.assertEqual(self.status(self._report(self.ALL_SET, store), "verification"), "fail")  # too old
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            store.append_event("verification", {"ok": True}, now)
            self.assertEqual(self.status(self._report(self.ALL_SET, store), "verification"), "pass")

    def test_endpoint_is_open_to_read_and_verification_post_needs_the_password(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
                "NEXUS_STATE_DB": str(Path(tmp) / "d.sqlite3"), "NEXUS_CONTROL_PASSWORD": "test-secret-123"}):
            engine = PaperEngine(load_settings())
            with patch.object(main, "get_engine", return_value=engine), TestClient(main.app) as client:
                self.assertFalse(client.get("/api/live/readiness").json()["liveAllowed"])
                body = {"ok": True, "passed": 20, "failed": 0}
                self.assertEqual(client.post("/api/verification", json=body).status_code, 401)
                self.assertEqual(client.post("/api/verification", json=body,
                                             headers={"x-nexus-control-password": "test-secret-123"}).status_code, 200)
                self.assertEqual(client.get("/api/history?kind=verification").json()["events"][0]["data"]["ok"], True)


if __name__ == "__main__":
    unittest.main()
