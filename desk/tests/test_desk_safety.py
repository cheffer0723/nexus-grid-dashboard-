"""Behavior checks for the Desk's write boundary and durable paper journal."""
from __future__ import annotations

import math
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import kraken_public, main
from backend.config import load_settings
from backend.paper_engine import PaperEngine
from backend.state_store import StateStore


class DeskSafetyTests(unittest.TestCase):
    def test_instance_reports_actual_processes_not_systemd_units(self) -> None:
        engine = PaperEngine(load_settings())
        engine.open_positions = [{"symbol": "BTC/USD", "entry_price": 100.0}]
        with patch.object(main, "get_engine", return_value=engine):
            workload = main.instance_workload()
        self.assertEqual([service["unit"] for service in workload["services"]],
                         ["Railway desk process", "In-process paper loop"])
        positions = workload["artifacts"]["openPositions"]["data"]
        self.assertEqual(positions, {"position_count": 1, "active_symbols": "BTC/USD"})

    def test_public_bundle_does_not_advertise_unavailable_hosts_or_live_orders(self) -> None:
        bundle = (Path(__file__).resolve().parents[1] / "public" / "assets" / "index-app.js").read_text(encoding="utf-8")
        self.assertIn("Railway Runtime", bundle)
        self.assertIn("Runtime Components", bundle)
        for stale_claim in (
            "DigitalOcean Runtime",
            "Check Droplet",
            "Live Trading Arm",
            "live arming gated",
            "GO LIVE",
            "Live orders still require the Control Deck live-arm flow",
        ):
            self.assertNotIn(stale_claim, bundle)

    def test_analytics_script_is_served(self) -> None:
        with TestClient(main.app) as client:
            response = client.get("/analytics.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Aggregate page-view analytics", response.text)

    def test_controls_fail_closed_and_jev_get_cannot_spend(self) -> None:
        with patch.dict(os.environ, {"NEXUS_CONTROL_PASSWORD": ""}), \
             patch.object(main, "get_engine", return_value=PaperEngine(load_settings())), \
             TestClient(main.app) as client:
            response = client.post("/api/command", json={"action": "PAUSE"})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(client.get("/api/jev/compare?run=1").status_code, 405)
            self.assertEqual(client.post("/api/jev/compare?run=1").status_code, 503)

        with patch.dict(os.environ, {"NEXUS_CONTROL_PASSWORD": "test-secret"}), \
             patch.object(main, "get_engine", return_value=PaperEngine(load_settings())), \
             TestClient(main.app) as client:
            self.assertEqual(client.post("/api/command", json={"action": "PAUSE"}).status_code, 401)

    def test_paid_call_requires_auth_and_uses_durable_daily_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            variables = {
                "NEXUS_CONTROL_PASSWORD": "test-secret",
                "OPENROUTER_API_KEY": "test-provider-key",
                "NEXUS_JEV_CALLS_ENABLED": "1",
                "NEXUS_JEV_MAX_CALLS_PER_DAY": "1",
                "NEXUS_STATE_DB": str(Path(tmp) / "desk.sqlite3"),
            }
            with patch.dict(os.environ, variables):
                settings = load_settings()
                engine = PaperEngine(settings)
                desk = {"action": "LONG", "symbol": "BTC/USD", "price": 100.0}
                signal = {"action": "LONG", "symbol": "BTC/USD"}
                market = {"symbol": "BTC/USD", "price": 100.0}
                answer = {"direction": "long", "provider": "openrouter", "latencyMs": 1}
                with patch.object(main, "get_engine", return_value=engine), \
                     patch.object(main, "_desk_signal_payload", return_value=(settings, desk, signal, market)), \
                     patch.object(main.jev_client, "evaluate", return_value=answer) as evaluate, \
                     TestClient(main.app) as client:
                    url = "/api/jev/compare?run=1"
                    self.assertEqual(client.post(url).status_code, 401)
                    header = {"x-nexus-control-password": "test-secret"}
                    self.assertEqual(client.post(url, headers=header).status_code, 200)
                    self.assertEqual(client.post(url, headers=header).status_code, 429)
                    evaluate.assert_called_once()
                reopened = StateStore(variables["NEXUS_STATE_DB"])
                self.assertFalse(reopened.reserve_jev_call(datetime.now(timezone.utc).date().isoformat(), 1))

    def test_analytics_is_aggregate_and_report_is_protected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            variables = {
                "NEXUS_CONTROL_PASSWORD": "test-secret",
                "NEXUS_STATE_DB": str(Path(tmp) / "analytics.sqlite3"),
            }
            with patch.dict(os.environ, variables):
                engine = PaperEngine(load_settings())
                with patch.object(main, "get_engine", return_value=engine), TestClient(main.app) as client:
                    response = client.post("/api/analytics/pageview", json={
                        "path": "/market?symbol=BTC/USD",
                        "referrer": "https://example.test/a/private/path?secret=nope",
                        "screen": "compact",
                    })
                    self.assertEqual(response.status_code, 204)
                    self.assertEqual(client.get("/api/analytics").status_code, 401)
                    report = client.get(
                        "/api/analytics?days=7",
                        headers={"x-nexus-control-password": "test-secret"},
                    )
                self.assertEqual(report.status_code, 200)
                data = report.json()
                self.assertEqual(data["totalPageviews"], 1)
                self.assertEqual(data["pages"], [{"page": "/market", "pageviews": 1}])
                self.assertEqual(data["referrers"], [{"domain": "example.test", "pageviews": 1}])
                self.assertTrue(all(value is False for value in data["privacy"].values() if isinstance(value, bool)))

    def test_cycles_and_trade_exits_survive_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"NEXUS_STATE_DB": str(Path(tmp) / "paper.sqlite3")}):
                settings = load_settings()
                engine = PaperEngine(settings)

                def rows(up: bool) -> list[list[float]]:
                    closes = [100 + i * 0.1 + math.sin(i / 2) * 0.7 for i in range(60)]
                    if not up:
                        closes = [110 - i * 0.1 + math.sin(i / 2) * 0.7 for i in range(60)]
                    return [[0, 0, 0, 0, close, 0, 1] for close in closes]

                with patch.object(kraken_public, "ohlc", return_value=rows(True)):
                    engine._run_cycle()
                self.assertEqual(len(engine.open_positions), 1)
                restored = PaperEngine(settings)
                self.assertEqual(restored.cycle, 1)
                self.assertEqual(len(restored.open_positions), 1)
                with patch.object(kraken_public, "ohlc", return_value=rows(False)):
                    restored._run_cycle()
                self.assertEqual(restored.closed_count, 1)
                trades = restored.store.events(kind="trade")
                self.assertEqual([row["data"]["action"] for row in trades], ["close", "open"])
                self.assertEqual(PaperEngine(settings).closed_count, 1)
                self.assertEqual(len(restored.store.events(kind="cycle")), 2)


if __name__ == "__main__":
    unittest.main()
