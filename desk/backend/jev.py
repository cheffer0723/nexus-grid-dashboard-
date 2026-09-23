"""Optional TypeSafe Jev client. Paper research only — never arms live."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any


JEV_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"


def build_state(signal: dict[str, Any], market: dict[str, Any]) -> dict[str, Any]:
    """Compact market state for one System One evaluation."""
    return {
        "desk": "Nexus Desk paper observer",
        "mode": "paper",
        "symbol": signal.get("symbol") or market.get("symbol"),
        "price": market.get("price") if market.get("price") is not None else signal.get("current_price"),
        "changePercent24h": market.get("changePercent24h"),
        "bid": market.get("bid"),
        "ask": market.get("ask"),
        "vwap": signal.get("vwap") or market.get("vwap"),
        "ema9": signal.get("ema9"),
        "ema21": signal.get("ema21"),
        "rsi14": signal.get("rsi14"),
        "volatility": signal.get("volatility_state"),
        "desk_action": signal.get("action"),
        "desk_confidence": signal.get("confidence"),
        "desk_reason": signal.get("execution_reason"),
        "horizon": "next few minutes scalp window on public Kraken spot",
        "constraint": "Paper only. Do not assume live capital or leverage.",
    }


def build_questions() -> dict[str, Any]:
    return {
        "direction": {
            "type": "choice",
            "instructions": (
                "For this paper scalp window, which side is more likely to work "
                "over the next few minutes on this spot pair?"
            ),
            "criteria": {
                "long": "Price more likely up; favor a long bias.",
                "short": "Price more likely down; favor a short bias.",
                "flat": "No clear edge; stay flat / wait.",
            },
        },
        "conviction": {
            "type": "score",
            "instructions": "How strong is the edge for that direction right now?",
            "criteria": [
                "No edge — noise only",
                "Weak lean",
                "Moderate setup",
                "Strong setup",
                "Very strong, unusual clarity",
            ],
        },
        "take_trade": {
            "type": "noul",
            "instructions": (
                "Should a conservative paper desk take a trade on this bar "
                "(yes) or stand aside (no)?"
            ),
            "criteria": {
                "true": "Take the paper trade.",
                "false": "Stand aside.",
            },
        },
    }


def evaluate(
    *,
    api_key: str,
    state: dict[str, Any],
    model: str = DEFAULT_MODEL,
    timeout: float = 25.0,
) -> dict[str, Any]:
    """POST one System One round-trip. Raises RuntimeError on transport/API failure."""
    payload = {
        "model": model or DEFAULT_MODEL,
        "state": state,
        "questions": build_questions(),
    }
    req = urllib.request.Request(
        JEV_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "nexus-desk-template/1.0",
            "Accept": "application/json",
        },
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"Jev HTTP {exc.code}: {detail}") from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Jev request failed: {exc}") from exc
    latency_ms = int((time.perf_counter() - started) * 1000)

    answers = body.get("answers") or {}
    direction = answers.get("direction") or {}
    conviction = answers.get("conviction") or {}
    take = answers.get("take_trade") or {}

    choice = str(direction.get("choice") or "flat").lower()
    if choice not in {"long", "short", "flat"}:
        choice = "flat"

    return {
        "model": body.get("model") or model,
        "direction": choice,
        "directionConfidence": direction.get("confidence"),
        "directionProbabilities": direction.get("probabilities"),
        "conviction": conviction.get("score"),
        "convictionConfidence": conviction.get("confidence"),
        "takeTrade": take.get("noul"),
        "usage": body.get("usage"),
        "latencyMs": latency_ms,
        "rawAnswers": answers,
    }


def agreement(desk_action: str, jev_direction: str) -> str:
    desk = (desk_action or "WAIT").upper()
    jev = (jev_direction or "flat").lower()
    desk_side = {
        "LONG": "long",
        "SHORT": "short",
        "WAIT": "flat",
        "FLAT": "flat",
    }.get(desk, "flat")
    if desk_side == jev:
        return "agree"
    if desk_side == "flat" or jev == "flat":
        return "partial"
    return "disagree"
