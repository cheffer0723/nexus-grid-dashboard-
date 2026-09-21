#!/usr/bin/env python3
"""Build a shared regime scorecard for the dashboard template.

The coin list, dates, fee, and rule settings live in scorecard-universe.json.
Each engine is one fixed rule from the archived research code. Nothing in this
script searches for a better setting on the coins it scores.

  Cerberus   Markov bull/bear/sideways labels and a walk-forward transition matrix
  Orthrus    long only while price is above its 200-day average
  Hydra      long only while the trailing 182-day return is positive
  Sisyphus   long the day after price closes below its lower Bollinger band

A hit is an in-market day whose price move went the same way as the position.
Fees are charged when the position changes. Buy-and-hold in the table is the
price change over the same days, with no fee.

Requires Python 3.10 or newer and no third-party packages.
"""

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UNIVERSE = ROOT / "scorecard-universe.json"
DEFAULT_OUTPUT = ROOT / "scorecard.json"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

ENGINE_COPY = {
    "cerberus": {
        "name": "Cerberus",
        "rule": "20-day return labels a bull, bear, or sideways day. A walk-forward matrix estimates the next bull-minus-bear odds. Long or short the next day.",
    },
    "orthrus": {
        "name": "Orthrus",
        "rule": "Long the next day while price is above its 200-day average. Flat otherwise.",
    },
    "hydra": {
        "name": "Hydra",
        "rule": "Long the next day while the trailing 182-day return is positive. Flat otherwise.",
    },
    "sisyphus": {
        "name": "Sisyphus",
        "rule": "Long the next day after price closes below its lower 20-day Bollinger band. Flat otherwise.",
    },
}


def parse_iso(value: str) -> date:
    return date.fromisoformat(value)


def sign(value: float) -> float:
    if value > 0:
        return 1.0
    if value < 0:
        return -1.0
    return 0.0


def mean(values: list[float | None]) -> float | None:
    usable = [value for value in values if value is not None and math.isfinite(value)]
    if not usable:
        return None
    return sum(usable) / len(usable)


def sample_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = sum(values) / len(values)
    var = sum((value - mu) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(var)


def sharpe(values: list[float], periods_per_year: int = 365) -> float | None:
    sd = sample_std(values)
    if sd == 0 or len(values) < 2:
        return None
    return (sum(values) / len(values)) / sd * math.sqrt(periods_per_year)


def rolling_sample_std(values: list[float], start: int, end: int) -> float:
    chunk = values[start:end]
    return sample_std(chunk)


def label_regimes(closes: list[float], window: int, threshold: float) -> list[int | None]:
    labels: list[int | None] = [None] * len(closes)
    for index in range(window, len(closes)):
        base = closes[index - window]
        if base == 0:
            continue
        rolled = closes[index] / base - 1.0
        if rolled > threshold:
            labels[index] = 2
        elif rolled < -threshold:
            labels[index] = 0
        else:
            labels[index] = 1
    return labels


def cerberus_positions(closes: list[float], window: int, threshold: float, min_train: int) -> list[float]:
    """Walk-forward Markov position. Fits only on labels seen so far."""
    labels = label_regimes(closes, window, threshold)
    labeled = [index for index, label in enumerate(labels) if label is not None]
    positions = [0.0] * len(closes)
    if len(labeled) < min_train + 2:
        return positions

    counts = [[0.0, 0.0, 0.0] for _ in range(3)]
    for cursor in range(min_train - 1):
        left = labels[labeled[cursor]]
        right = labels[labeled[cursor + 1]]
        counts[left][right] += 1.0

    for cursor in range(min_train, len(labeled) - 1):
        state = labels[labeled[cursor]]
        total = sum(counts[state])
        if total > 0:
            bull = counts[state][2] / total
            bear = counts[state][0] / total
            positions[labeled[cursor]] = sign(bull - bear)
        prior = labels[labeled[cursor - 1]]
        counts[prior][state] += 1.0
    return positions


def orthrus_positions(closes: list[float], ma_window: int) -> list[float]:
    positions = [0.0] * len(closes)
    if ma_window <= 1:
        raise ValueError("ma_window must be greater than 1")
    rolling = 0.0
    for index, price in enumerate(closes):
        rolling += price
        if index >= ma_window:
            rolling -= closes[index - ma_window]
        if index >= ma_window - 1:
            average = rolling / ma_window
            positions[index] = 1.0 if price > average else 0.0
    return positions


def hydra_positions(closes: list[float], lookback: int) -> list[float]:
    positions = [0.0] * len(closes)
    for index in range(lookback, len(closes)):
        base = closes[index - lookback]
        if base == 0:
            continue
        positions[index] = 1.0 if closes[index] / base - 1.0 > 0 else 0.0
    return positions


def sisyphus_positions(closes: list[float], window: int, zscore: float) -> list[float]:
    positions = [0.0] * len(closes)
    if window < 2:
        raise ValueError("window must be at least 2")
    for index in range(window - 1, len(closes)):
        start = index - window + 1
        chunk = closes[start : index + 1]
        mid = sum(chunk) / window
        sd = rolling_sample_std(closes, start, index + 1)
        if sd == 0:
            continue
        if closes[index] < mid - zscore * sd:
            positions[index] = 1.0
    return positions


def positions_for(engine_id: str, closes: list[float], settings: dict) -> list[float]:
    if engine_id == "cerberus":
        return cerberus_positions(
            closes,
            int(settings["window"]),
            float(settings["threshold"]),
            int(settings["min_train"]),
        )
    if engine_id == "orthrus":
        return orthrus_positions(closes, int(settings["ma_window"]))
    if engine_id == "hydra":
        return hydra_positions(closes, int(settings["momentum_lookback"]))
    if engine_id == "sisyphus":
        return sisyphus_positions(closes, int(settings["window"]), float(settings["zscore"]))
    raise ValueError(f"unknown engine {engine_id}")


def score_window(
    dates: list[date],
    closes: list[float],
    positions: list[float],
    eval_start: date,
    eval_end: date,
    fee_per_side: float,
    min_bars: int = 30,
) -> dict:
    """Score next-bar positions on an inclusive date window."""
    count = len(closes)
    if not (count == len(dates) == len(positions)) or count < 3:
        raise ValueError("dates, closes, and positions must be the same length")

    returns = [0.0] * count
    for index in range(1, count):
        previous = closes[index - 1]
        returns[index] = 0.0 if previous == 0 else closes[index] / previous - 1.0

    held = [0.0] * count
    for index in range(1, count):
        held[index] = float(positions[index - 1])

    strategy = [0.0] * count
    previous_held = 0.0
    for index in range(count):
        turnover = abs(held[index] - previous_held)
        strategy[index] = held[index] * returns[index] - fee_per_side * turnover
        previous_held = held[index]

    chosen = [index for index, day in enumerate(dates) if index > 0 and eval_start <= day <= eval_end]
    if len(chosen) < min_bars:
        raise ValueError(f"only {len(chosen)} bars inside the evaluation window")

    equity = 1.0
    benchmark = 1.0
    peak = 1.0
    max_drawdown = 0.0
    active_days = 0
    hits = 0
    in_market = 0
    trades = 0
    up_days = 0
    net_returns: list[float] = []

    for index in chosen:
        equity *= 1.0 + strategy[index]
        benchmark *= 1.0 + returns[index]
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = min(max_drawdown, equity / peak - 1.0)
        net_returns.append(strategy[index])
        if returns[index] > 0:
            up_days += 1
        if abs(held[index]) > 1e-12:
            in_market += 1
            active_days += 1
            if held[index] * returns[index] > 0:
                hits += 1
        previous_sign = sign(held[index - 1])
        current_sign = sign(held[index])
        if current_sign != 0 and current_sign != previous_sign:
            trades += 1

    total_return = equity - 1.0
    benchmark_return = benchmark - 1.0
    return {
        "bars": len(chosen),
        "start": dates[chosen[0]].isoformat(),
        "end": dates[chosen[-1]].isoformat(),
        "hit_rate_active": (hits / active_days) if active_days else None,
        "active_days": active_days,
        "market_up_day_rate": up_days / len(chosen),
        "total_return": total_return,
        "benchmark_return": benchmark_return,
        "excess_return": total_return - benchmark_return,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe(net_returns),
        "trades": trades,
        "pct_in_market": in_market / len(chosen),
    }


def download_yahoo(symbol: str, start: date, end: date) -> tuple[list[date], list[float]]:
    period1 = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())
    period2 = int(datetime(end.year, end.month, end.day, tzinfo=timezone.utc).timestamp())
    url = (
        f"{YAHOO_CHART.format(symbol=symbol)}"
        f"?interval=1d&period1={period1}&period2={period2}&events=history"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "nexus-grid-scorecard/1.0"})
    last_error: Exception | None = None
    payload = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    if payload is None:
        raise RuntimeError(f"{symbol}: download failed: {last_error}")

    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        error = (payload.get("chart") or {}).get("error") or {}
        raise RuntimeError(f"{symbol}: {error.get('description') or 'no price data'}")
    block = result[0]
    stamps = block.get("timestamp") or []
    closes = ((block.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    by_day: dict[date, float] = {}
    for stamp, close in zip(stamps, closes):
        if close is None or not math.isfinite(float(close)):
            continue
        day = datetime.fromtimestamp(int(stamp), timezone.utc).date()
        by_day[day] = float(close)
    if len(by_day) < 100:
        raise RuntimeError(f"{symbol}: only {len(by_day)} daily closes")
    ordered = sorted(by_day)
    return ordered, [by_day[day] for day in ordered]


def aggregate(rows: list[dict]) -> dict:
    def pick(key: str) -> float | None:
        return mean([row.get(key) for row in rows])

    hit_rates = [row["hit_rate_active"] for row in rows if row.get("hit_rate_active") is not None]
    return {
        "assets_tested": len(rows),
        "hit_rate_active": pick("hit_rate_active"),
        "hit_rate_min": min(hit_rates) if hit_rates else None,
        "hit_rate_max": max(hit_rates) if hit_rates else None,
        "assets_hit_rate_at_least_60": sum(1 for rate in hit_rates if rate >= 0.60),
        "market_up_day_rate": pick("market_up_day_rate"),
        "total_return": pick("total_return"),
        "benchmark_return": pick("benchmark_return"),
        "excess_return": pick("excess_return"),
        "max_drawdown": pick("max_drawdown"),
        "sharpe": pick("sharpe"),
        "trades": pick("trades"),
        "pct_in_market": pick("pct_in_market"),
    }


def build_scorecard(universe: dict, series: dict[str, tuple[list[date], list[float]]]) -> dict:
    eval_start = parse_iso(universe["eval_start"])
    eval_end = parse_iso(universe["eval_end"])
    fee = float(universe["fee_per_side"])
    settings = universe["engines"]
    asset_rows: list[dict] = []
    skipped: list[dict] = []
    per_engine: dict[str, list[dict]] = {engine_id: [] for engine_id in ENGINE_COPY}

    for symbol in universe["symbols"]:
        dates, closes = series[symbol]
        asset_engines = []
        asset_error = None
        for engine_id in ENGINE_COPY:
            try:
                positions = positions_for(engine_id, closes, settings[engine_id])
                metrics = score_window(dates, closes, positions, eval_start, eval_end, fee)
            except Exception as exc:  # noqa: BLE001 - one bad coin should not drop the run
                asset_error = str(exc)
                break
            metrics["engine"] = engine_id
            per_engine[engine_id].append({"symbol": symbol, **metrics})
            asset_engines.append({"engine": engine_id, **metrics})
        if asset_error or len(asset_engines) != len(ENGINE_COPY):
            skipped.append({"symbol": symbol, "reason": asset_error or "incomplete"})
            for engine_id in ENGINE_COPY:
                per_engine[engine_id] = [row for row in per_engine[engine_id] if row["symbol"] != symbol]
            continue
        asset_rows.append(
            {
                "symbol": symbol,
                "start": asset_engines[0]["start"],
                "end": asset_engines[0]["end"],
                "bars": asset_engines[0]["bars"],
                "market_up_day_rate": asset_engines[0]["market_up_day_rate"],
                "benchmark_return": asset_engines[0]["benchmark_return"],
                "engines": asset_engines,
            }
        )

    engines = []
    for engine_id, copy in ENGINE_COPY.items():
        summary = aggregate(per_engine[engine_id])
        engines.append(
            {
                "id": engine_id,
                "name": copy["name"],
                "rule": copy["rule"],
                "settings": settings[engine_id],
                **summary,
            }
        )

    return {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "universe": list(universe["symbols"]),
        "history_start": universe["history_start"],
        "eval_start": universe["eval_start"],
        "eval_end": universe["eval_end"],
        "fee_per_side": fee,
        "assets_tested": len(asset_rows),
        "skipped": skipped,
        "engines": engines,
        "assets": asset_rows,
        "method": {
            "price_source": "Yahoo Finance daily closes",
            "position_timing": "Signal on today's close is applied to the next day's return.",
            "hit_rate": "Share of in-market days where the position and the day's price move had the same sign. Fees are not part of the hit test.",
            "fee": "0.40% each time the held position changes, including a long-to-short flip.",
            "benchmark": "Buy and hold over the same days, with no fee.",
            "presets": "Rules are the archived fixed presets. This run does not search for better settings.",
            "rebuild": "python3 scripts/build_regime_scorecard.py",
        },
    }


def load_universe(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = ["history_start", "eval_start", "eval_end", "fee_per_side", "symbols", "engines"]
    missing = [key for key in required if key not in payload]
    if missing:
        raise SystemExit(f"{path} is missing {', '.join(missing)}")
    for engine_id in ENGINE_COPY:
        if engine_id not in payload["engines"]:
            raise SystemExit(f"{path} is missing engines.{engine_id}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild the regime scorecard JSON used by the dashboard.")
    parser.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    universe = load_universe(args.universe)
    history_start = parse_iso(universe["history_start"])
    history_end = parse_iso(universe["eval_end"]) + timedelta(days=1)
    series: dict[str, tuple[list[date], list[float]]] = {}
    for symbol in universe["symbols"]:
        print(f"downloading {symbol}")
        series[symbol] = download_yahoo(symbol, history_start, history_end)
        time.sleep(0.25)

    scorecard = build_scorecard(universe, series)
    args.output.write_text(json.dumps(scorecard, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(f"assets {scorecard['assets_tested']} skipped {len(scorecard['skipped'])}")
    for engine in scorecard["engines"]:
        hit = engine["hit_rate_active"]
        excess = engine["excess_return"]
        hit_text = "n/a" if hit is None else f"{hit:.1%}"
        excess_text = "n/a" if excess is None else f"{excess:+.1%}"
        print(f"{engine['name']:10s} hit {hit_text:>7s}  vs buy-hold {excess_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
