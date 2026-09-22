#!/usr/bin/env python3
"""Behavior checks for the regime scorecard. No network."""

from __future__ import annotations

import json
import unittest
from datetime import date, timedelta
from pathlib import Path

from build_regime_scorecard import (
    ROOT,
    build_scorecard,
    cerberus_positions,
    hydra_positions,
    load_universe,
    orthrus_positions,
    score_window,
    sisyphus_positions,
)


def rising_series(days: int, daily_growth: float = 0.003) -> tuple[list[date], list[float]]:
    start = date(2018, 1, 1)
    dates = [start + timedelta(days=offset) for offset in range(days)]
    closes = [100.0 * ((1.0 + daily_growth) ** offset) for offset in range(days)]
    return dates, closes


class ScorecardMathTests(unittest.TestCase):
    def test_hit_rate_counts_direction_not_fees(self) -> None:
        dates = [date(2024, 1, 1) + timedelta(days=offset) for offset in range(6)]
        closes = [100, 101, 99, 100, 102, 101]
        # Position known at the prior close. Held over days 2, 3, and 4.
        positions = [0, 1, 1, 1, 0, 0]
        metrics = score_window(dates, closes, positions, dates[0], dates[-1], fee_per_side=0.5, min_bars=1)
        self.assertEqual(metrics["active_days"], 3)
        self.assertAlmostEqual(metrics["hit_rate_active"], 2 / 3)

    def test_cerberus_rides_a_steady_uptrend(self) -> None:
        dates, closes = rising_series(700)
        positions = cerberus_positions(closes, window=20, threshold=0.05, min_train=252)
        self.assertEqual(len(positions), len(closes))
        self.assertGreater(sum(1 for value in positions[400:] if value > 0), 200)
        metrics = score_window(dates, closes, positions, date(2019, 6, 1), dates[-1], 0.004)
        self.assertGreater(metrics["hit_rate_active"], 0.9)
        self.assertGreater(metrics["total_return"], 0)

    def test_orthrus_is_long_above_a_rising_average(self) -> None:
        _dates, closes = rising_series(400)
        positions = orthrus_positions(closes, 200)
        self.assertTrue(all(value == 0 for value in positions[:199]))
        self.assertTrue(all(value == 1 for value in positions[250:]))

    def test_hydra_follows_positive_trailing_return(self) -> None:
        _dates, closes = rising_series(400)
        positions = hydra_positions(closes, 182)
        self.assertTrue(all(value == 1 for value in positions[200:]))

    def test_sisyphus_stays_mostly_flat_in_a_smooth_uptrend(self) -> None:
        _dates, closes = rising_series(400, daily_growth=0.002)
        positions = sisyphus_positions(closes, 20, 2.0)
        self.assertLess(sum(positions) / len(positions), 0.05)

    def test_shared_window_ranks_buy_and_hold_against_the_rules(self) -> None:
        dates, closes = rising_series(900)
        series = {"UP-USD": (dates, closes)}
        universe = {
            "history_start": "2018-01-01",
            "eval_start": "2019-06-01",
            "eval_end": dates[-1].isoformat(),
            "fee_per_side": 0.004,
            "symbols": ["UP-USD"],
            "engines": load_universe(ROOT / "scorecard-universe.json")["engines"],
        }
        scorecard = build_scorecard(universe, series)
        self.assertEqual(scorecard["assets_tested"], 1)
        by_id = {engine["id"]: engine for engine in scorecard["engines"]}
        self.assertGreater(by_id["cerberus"]["hit_rate_active"], 0.9)
        self.assertGreater(by_id["cerberus"]["pct_in_market"], 0.95)
        self.assertLessEqual(by_id["cerberus"]["excess_return"], 0.0)
        self.assertLess(by_id["sisyphus"]["pct_in_market"], 0.1)

    def test_checked_in_universe_is_complete(self) -> None:
        universe = json.loads((ROOT / "scorecard-universe.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(universe["symbols"]), 8)
        self.assertEqual(len(universe["symbols"]), len(set(universe["symbols"])))
        self.assertAlmostEqual(universe["fee_per_side"], 0.004)
        loaded = load_universe(Path(ROOT / "scorecard-universe.json"))
        self.assertEqual(loaded["symbols"][0], "BTC-USD")


if __name__ == "__main__":
    unittest.main()
