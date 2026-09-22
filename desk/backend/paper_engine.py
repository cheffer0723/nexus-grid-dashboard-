"""In-process paper observer. Public OHLC only; no exchange keys."""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from . import kraken_public
from .config import Settings, load_settings


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _ema(values: list[float], period: int) -> float:
    if not values:
        return 0.0
    alpha = 2.0 / (period + 1.0)
    out = values[0]
    for value in values[1:]:
        out = alpha * value + (1.0 - alpha) * out
    return out


def _rsi(closes: list[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains = []
    losses = []
    for i in range(-period, 0):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(abs(min(delta, 0.0)))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _vwap(closes: list[float], volumes: list[float]) -> float:
    num = sum(c * v for c, v in zip(closes, volumes))
    den = sum(volumes) or 1.0
    return num / den


@dataclass
class PaperEngine:
    settings: Settings
    lock: threading.Lock = field(default_factory=threading.Lock)
    running: bool = True
    cycle: int = 0
    last_heartbeat: str = field(default_factory=utc_now)
    latest_signal: dict[str, Any] = field(default_factory=dict)
    latest_execution: dict[str, Any] = field(default_factory=dict)
    open_positions: list[dict[str, Any]] = field(default_factory=list)
    closed_count: int = 0
    realized_pnl: float = 0.0
    decisions: list[dict[str, Any]] = field(default_factory=list)
    logs: list[dict[str, Any]] = field(default_factory=list)
    commands: list[dict[str, Any]] = field(default_factory=list)
    _thread: threading.Thread | None = field(default=None, repr=False)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, name="nexus-paper", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.running = False

    def restart(self) -> None:
        self.stop()
        time.sleep(0.2)
        self.settings = load_settings()
        self.start()
        self._command("RESTART", "Paper observer restarted.")

    def pause(self) -> None:
        self.running = False
        self._command("PAUSE", "Paper observer paused.")

    def resume(self) -> None:
        if not self.running:
            self.start()
        self._command("RESUME", "Paper observer resumed.")

    def refresh(self) -> None:
        self._cycle_once()
        self._command("REFRESH", "Status refreshed.")

    def _command(self, action: str, detail: str) -> None:
        row = {"at": utc_now(), "action": action, "detail": detail}
        with self.lock:
            self.commands.insert(0, row)
            self.commands = self.commands[:40]

    def _log(self, message: str, level: str = "info", source: str = "engine_cycle") -> None:
        row = {
            "id": int(time.time() * 1000),
            "level": level,
            "message": message,
            "source": source,
            "timestamp": utc_now(),
            "metadata": "{}",
        }
        with self.lock:
            self.logs.insert(0, row)
            self.logs = self.logs[:500]
            self.decisions.insert(
                0,
                {
                    "id": row["id"],
                    "systemStatus": "go",
                    "reason": message,
                    "primaryRisk": "Paper-only template. Live arming stays off until keys and flags are set.",
                    "recommendedAction": "monitor",
                    "createdAt": row["timestamp"],
                },
            )
            self.decisions = self.decisions[:500]

    def _loop(self) -> None:
        while self.running:
            try:
                self._cycle_once()
            except Exception as exc:  # noqa: BLE001 — keep the loop alive in the template
                self._log(f"Cycle error: {exc}", level="error")
            for _ in range(max(1, self.settings.loop_interval)):
                if not self.running:
                    break
                time.sleep(1)

    def _cycle_once(self) -> None:
        settings = self.settings
        symbol = settings.trade_symbol
        rows = kraken_public.ohlc(symbol, interval=settings.ohlc_interval_min)
        if len(rows) < 40:
            raise RuntimeError("Not enough OHLC history yet")
        closes = [float(r[4]) for r in rows]
        volumes = [float(r[6]) for r in rows]
        price = closes[-1]
        ema9 = _ema(closes[-60:], 9)
        ema21 = _ema(closes[-120:], 21)
        rsi14 = _rsi(closes, 14)
        vwap = _vwap(closes[-settings.vwap_window :], volumes[-settings.vwap_window :])
        bullish = ema9 > ema21
        bearish = ema9 < ema21
        action = "WAIT"
        reason = f"No scalp trigger. Trend={'up' if bullish else 'down' if bearish else 'flat'}, rsi14={rsi14:.1f}, vwap={vwap:.2f}."
        confidence = 0.25
        if bullish and 10.0 < rsi14 < 75.0:
            action = "LONG"
            confidence = min(0.85, 0.5 + abs(ema9 - ema21) / max(ema21, 1.0) * 10.0)
            reason = f"Exploration long: ema9({ema9:.2f})>ema21({ema21:.2f}), rsi14={rsi14:.1f}, vwap={vwap:.2f}."
        elif bearish and 10.0 < rsi14 < 75.0:
            action = "SHORT"
            confidence = min(0.85, 0.5 + abs(ema9 - ema21) / max(ema21, 1.0) * 10.0)
            reason = f"Exploration short: ema9({ema9:.2f})<ema21({ema21:.2f}), rsi14={rsi14:.1f}, vwap={vwap:.2f}."

        signal = {
            "timestamp_utc": utc_now(),
            "strategy_version": "desk_template_scalper_v1",
            "trade_id": f"desk_template:{uuid.uuid4().hex[:16]}",
            "symbol": symbol,
            "action": action,
            "market_bias": "BULLISH" if action == "LONG" else "BEARISH" if action == "SHORT" else "NEUTRAL",
            "confidence": confidence,
            "volatility_state": "HIGH" if abs(closes[-1] - closes[-5]) / max(closes[-5], 1.0) > 0.003 else "NORMAL",
            "allowed_side": "longs_only" if settings.paper_only else "both",
            "can_trade": action == "LONG" or (action == "SHORT" and not settings.paper_only),
            "execution_reason": reason,
            "stop_loss_pct": settings.stop_loss_pct,
            "take_profit_pct_min": settings.take_profit_pct,
            "take_profit_pct_max": settings.take_profit_pct,
            "position_size_usd": settings.position_usd,
            "current_price": price,
            "ema9": ema9,
            "ema21": ema21,
            "rsi14": rsi14,
            "vwap": vwap,
            "shadow_eod_only": True,
        }

        with self.lock:
            self.cycle += 1
            self.last_heartbeat = utc_now()
            self._manage_positions(signal, price)
            self.latest_signal = signal
            unrealized = sum(float(p.get("pnl_abs") or 0.0) for p in self.open_positions)
            self.latest_execution = {
                "timestamp_utc": utc_now(),
                "mode": "paper_spot",
                "shorting_enabled": not settings.paper_only,
                "leverage_enabled": False,
                "bearish_signal_behavior": "close_long_or_flat",
                "status": "MANAGED" if self.open_positions else "NO_ACTION",
                "signal_timestamp_utc": signal["timestamp_utc"],
                "trade_id": signal["trade_id"],
                "strategy_version": signal["strategy_version"],
                "symbol": symbol,
                "action": action,
                "current_price": price,
                "open_position_count": len(self.open_positions),
                "open_positions": list(self.open_positions),
                "summary": {
                    "open_position_count": len(self.open_positions),
                    "closed_position_count": self.closed_count,
                    "realized_pnl_abs": round(self.realized_pnl, 8),
                    "realized_pnl_pct": round(self.realized_pnl / max(settings.position_usd, 1.0), 8),
                    "unrealized_pnl_abs": round(unrealized, 8),
                    "unrealized_pnl_pct": round(unrealized / max(settings.position_usd, 1.0), 8),
                },
                "latest_event": {
                    "timestamp_utc": utc_now(),
                    "symbol": symbol,
                    "status": "MANAGED" if self.open_positions else "NO_ACTION",
                    "side": action,
                },
            }
        self._log(f"{symbol} {action}: {reason}")

    def _manage_positions(self, signal: dict[str, Any], price: float) -> None:
        settings = self.settings
        kept: list[dict[str, Any]] = []
        for position in self.open_positions:
            entry = float(position["entry_price"])
            side = position["side"]
            size = float(position["size"])
            pnl_abs = (price - entry) / entry * size if side == "LONG" else (entry - price) / entry * size
            position = {
                **position,
                "last_mark_price": price,
                "pnl_abs": round(pnl_abs, 8),
                "pnl_pct": round(pnl_abs / size, 8),
            }
            reason = None
            if side == "LONG":
                if price <= float(position["stop_loss_price"]):
                    reason = "stop_loss_hit"
                elif price >= float(position["take_profit_price"]):
                    reason = "take_profit_hit"
                elif signal.get("action") == "SHORT":
                    reason = "bearish_exit"
            if reason:
                self.closed_count += 1
                self.realized_pnl += float(position["pnl_abs"])
                continue
            kept.append(position)

        symbol = signal["symbol"]
        has_symbol = any(p.get("symbol") == symbol for p in kept)
        if signal.get("action") == "LONG" and signal.get("can_trade") and not has_symbol:
            entry = price
            kept.append(
                {
                    "position_id": signal["trade_id"],
                    "trade_id": signal["trade_id"],
                    "strategy_version": signal["strategy_version"],
                    "symbol": symbol,
                    "side": "LONG",
                    "status": "OPEN",
                    "entry_price": entry,
                    "entry_timestamp_utc": utc_now(),
                    "size": settings.position_usd,
                    "stop_loss_price": round(entry * (1.0 - settings.stop_loss_pct), 8),
                    "take_profit_price": round(entry * (1.0 + settings.take_profit_pct), 8),
                    "pnl_abs": 0.0,
                    "pnl_pct": 0.0,
                }
            )
        self.open_positions = kept


_ENGINE: PaperEngine | None = None


def get_engine() -> PaperEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = PaperEngine(settings=load_settings())
        _ENGINE.start()
    return _ENGINE
