"""Nexus Desk template API + static UI. One Railway service. Paper needs no keys."""
from __future__ import annotations

import hmac
import json
import os
import threading
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import load_settings
from . import kraken_public
from . import jev as jev_client
from .paper_engine import get_engine, utc_now

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"

app = FastAPI(title="Nexus Desk", version="1.0.0")

# Paper research only — last Jev compares (never drives live).
_JEV_HISTORY: list[dict[str, Any]] = []
_JEV_HISTORY_LOCK = threading.Lock()
_JEV_HISTORY_MAX = 12
_ANALYTICS_PAGES = {"/", "/status", "/core", "/market", "/controls", "/settings", "/instance", "/logs", "/analytics"}


class AnalyticsPageView(BaseModel):
    path: str = "/"
    referrer: str = ""
    screen: str = "unknown"


def _settings():
    return load_settings()


@app.on_event("startup")
def _startup() -> None:
    get_engine()


def _check_control_password(password: str | None) -> None:
    expected = _settings().control_password
    if not expected:
        raise HTTPException(status_code=503, detail="Controls are disabled until NEXUS_CONTROL_PASSWORD is configured")
    if not hmac.compare_digest((password or "").strip(), expected):
        raise HTTPException(status_code=401, detail="Control password required")


def _analytics_store():
    store = get_engine().store
    if not store:
        raise HTTPException(status_code=503, detail="Analytics needs NEXUS_STATE_DB on persistent storage")
    return store


def _analytics_page(path: str) -> str:
    parsed = urlsplit(path)
    candidate = parsed.path if parsed.path.startswith("/") else "/"
    return candidate if candidate in _ANALYTICS_PAGES else "/other"


def _analytics_referrer(raw: str) -> str:
    try:
        domain = (urlsplit(raw).hostname or "").lower().rstrip(".")
    except ValueError:
        domain = ""
    return domain[:253] or "direct"


@app.get("/api/health")
def health() -> JSONResponse:
    engine = get_engine()
    state = engine.health_snapshot()
    return JSONResponse({
        "ok": state["status"] in {"running", "starting", "paused"},
        "engine": state,
        "product": _settings().product_name,
        "paper_only": _settings().paper_only,
        "cycle": engine.cycle,
        "heartbeat": engine.last_heartbeat,
    }, status_code=503 if state["status"] == "degraded" else 200)


@app.post("/api/analytics/pageview", status_code=204)
def analytics_pageview(event: AnalyticsPageView) -> Response:
    """Record one aggregate page view; never retain IPs, user agents, or IDs."""
    screen = event.screen if event.screen in {"compact", "wide", "unknown"} else "unknown"
    _analytics_store().record_pageview(
        datetime.now(timezone.utc).date().isoformat(),
        _analytics_page(event.path),
        _analytics_referrer(event.referrer),
        screen,
    )
    return Response(status_code=204)


@app.get("/api/analytics")
def analytics_report(
    days: int = Query(default=30, ge=1, le=365),
    x_nexus_control_password: str | None = Header(default=None),
) -> dict[str, Any]:
    """Return protected aggregate traffic analytics for the requested UTC-day window."""
    _check_control_password(x_nexus_control_password)
    report = _analytics_store().analytics_report(days)
    report["privacy"] = {
        "ipAddressesStored": False,
        "userAgentsStored": False,
        "cookiesUsed": False,
        "visitorIdentifiersStored": False,
        "data": "Aggregate page-view counters only.",
    }
    return report


@app.get("/api/engine/status")
def engine_status() -> dict[str, Any]:
    settings = _settings()
    engine = get_engine()
    state = engine.health_snapshot()
    return {
        "engineId": "nexus-paper",
        "status": state["status"],
        "mode": "paper",
        "lastHeartbeat": engine.last_heartbeat,
        "riskState": "degraded" if state["status"] == "degraded" else "normal",
        "riskLevel": "high" if state["status"] == "degraded" else "normal",
        "activeAlerts": 1 if state["status"] == "degraded" else 0,
        "health": state,
        "uptime": f"cycle {engine.cycle}",
        "version": "desk-template-1",
        "isMock": False,
        "paperOnly": settings.paper_only,
        "liveKeysConfigured": settings.live_keys_configured,
    }


@app.get("/api/core/summary")
def core_summary() -> dict[str, Any]:
    settings = _settings()
    engine = get_engine()
    state = engine.health_snapshot()
    signal = engine.latest_signal or {}
    symbol = signal.get("symbol") or settings.trade_symbol
    try:
        market = kraken_public.ticker(symbol)
    except Exception:  # noqa: BLE001
        market = {"symbol": symbol, "price": signal.get("current_price"), "name": symbol, "market": symbol, "venue": "Kraken"}
    action = signal.get("action") or "WAIT"
    recommendation = "monitor" if action != "WAIT" else "stand aside"
    return {
        "summary": (
            f"Paper runner is {state['status']}; "
            "This Desk has no live order path.\n"
            f"Kraken public {symbol}: last ${market.get('price')}.\n"
            f"Latest signal: {symbol} {action}; confidence {round(float(signal.get('confidence') or 0) * 100)}%."
        ),
        "generatedAt": utc_now(),
        "confidence": signal.get("confidence") or 0.0,
        "tags": ["paper", symbol, action, "kraken-public"],
        "engine": {
            "engineId": "nexus-paper",
            "status": state["status"],
            "mode": "paper",
            "lastHeartbeat": engine.last_heartbeat,
        },
        "latestSignal": {
            "symbol": symbol,
            "action": action,
            "confidence": signal.get("confidence"),
            "volatilityState": signal.get("volatility_state"),
            "allowedSide": signal.get("allowed_side"),
            "canTrade": signal.get("can_trade"),
            "reason": signal.get("execution_reason"),
        },
        "marketContext": market,
        "recommendation": recommendation,
        "isMock": False,
    }


def _desk_signal_payload() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    settings = _settings()
    engine = get_engine()
    signal = dict(engine.latest_signal or {})
    symbol = signal.get("symbol") or settings.trade_symbol
    try:
        market = kraken_public.ticker(symbol)
    except Exception:  # noqa: BLE001
        market = {
            "symbol": symbol,
            "price": signal.get("current_price"),
            "name": symbol,
            "market": symbol,
            "venue": "Kraken",
        }
    desk = {
        "symbol": symbol,
        "action": signal.get("action") or "WAIT",
        "confidence": signal.get("confidence"),
        "reason": signal.get("execution_reason"),
        "ema9": signal.get("ema9"),
        "ema21": signal.get("ema21"),
        "rsi14": signal.get("rsi14"),
        "vwap": signal.get("vwap"),
        "price": market.get("price") if market.get("price") is not None else signal.get("current_price"),
        "cycle": engine.cycle,
        "heartbeat": engine.last_heartbeat,
        "strategy": signal.get("strategy_version") or "desk_template_scalper_v1",
    }
    return settings, desk, {**signal, "symbol": symbol}, market


@app.get("/api/jev/status")
def jev_status() -> dict[str, Any]:
    settings = _settings()
    return {
        "configured": settings.jev_configured,
        "callsEnabled": settings.jev_calls_enabled and bool(settings.control_password) and settings.jev_max_calls_per_day > 0 and bool(get_engine().store),
        "maxCallsPerDay": settings.jev_max_calls_per_day,
        "provider": settings.jev_provider or None,
        "model": settings.jev_model,
        "paperOnly": True,
        "armsLive": False,
        "disclaimer": (
            "Optional research compare. Jev never arms live on this desk. "
            "Paper mode stays zero-secret until you set OPENROUTER_API_KEY "
            "(or TYPESAFE_API_KEY)."
        ),
        "setup": {
            "env": [
                "OPENROUTER_API_KEY (preferred)",
                "TYPESAFE_API_KEY or NEXUS_JEV_API_KEY",
                "NEXUS_JEV_MODEL=jev-latest",
            ],
            "docs": "https://openrouter.ai/docs/guides/community/jev",
        },
    }


@app.api_route("/api/jev/compare", methods=["GET", "POST"])
def jev_compare(
    request: Request,
    run: int = 0,
    x_nexus_control_password: str | None = Header(default=None),
) -> dict[str, Any]:
    """Compare desk paper signal vs optional Jev System One call. Never executes."""
    if run:
        if request.method != "POST":
            raise HTTPException(status_code=405, detail="Use POST to request a Jev comparison")
        _check_control_password(x_nexus_control_password)
    settings, desk, signal, market = _desk_signal_payload()
    with _JEV_HISTORY_LOCK:
        history = list(_JEV_HISTORY)

    route = jev_client.resolve_route(
        openrouter_api_key=settings.openrouter_api_key,
        typesafe_api_key=_env_typesafe_only(),
        model=settings.jev_model,
    )

    base = {
        "paperOnly": True,
        "armsLive": False,
        "configured": settings.jev_configured and settings.jev_calls_enabled and bool(settings.control_password) and settings.jev_max_calls_per_day > 0 and bool(get_engine().store),
        "provider": settings.jev_provider or None,
        "model": settings.jev_model,
        "desk": desk,
        "market": {
            "symbol": market.get("symbol"),
            "price": market.get("price"),
            "changePercent24h": market.get("changePercent24h"),
            "venue": market.get("venue") or "Kraken",
        },
        "jev": None,
        "agreement": "n/a",
        "history": history,
        "disclaimer": (
            "Paper research only. This endpoint never places orders and never "
            "flips live-arm flags."
        ),
        "updatedAt": utc_now(),
    }

    if not settings.jev_configured or not route:
        base["status"] = "unconfigured"
        base["message"] = (
            "Set OPENROUTER_API_KEY on the service to ask Jev (or TYPESAFE_API_KEY "
            "if you have TypeSafe access). Until then the desk signal still runs "
            "on public Kraken data alone."
        )
        return base

    if not run:
        base["status"] = "ready" if base["configured"] else "disabled"
        base["message"] = (
            f"Configured via {route['provider']}. Ask Jev spends one evaluation."
            if base["configured"] else
            "Jev calls are disabled. Set a control password, durable state database, and NEXUS_JEV_CALLS_ENABLED to allow up to the daily cap."
        )
        return base

    if not settings.jev_calls_enabled or settings.jev_max_calls_per_day <= 0:
        raise HTTPException(status_code=503, detail="Jev calls are disabled")
    store = get_engine().store
    if not store:
        raise HTTPException(status_code=503, detail="Jev calls require durable storage for the daily budget")
    day = datetime.now(timezone.utc).date().isoformat()
    if not store.reserve_jev_call(day, settings.jev_max_calls_per_day):
        raise HTTPException(status_code=429, detail="Jev daily call budget reached")

    try:
        state = jev_client.build_state(signal, market)
        result = jev_client.evaluate(
            api_key=route["api_key"],
            state=state,
            model=route["model"],
            url=route["url"],
            provider=route["provider"],
        )
    except Exception as exc:  # noqa: BLE001
        base["status"] = "error"
        base["message"] = str(exc)
        return base

    agree = jev_client.agreement(str(desk.get("action") or "WAIT"), str(result.get("direction") or "flat"))
    row = {
        "at": utc_now(),
        "deskAction": desk.get("action"),
        "jevDirection": result.get("direction"),
        "agreement": agree,
        "conviction": result.get("conviction"),
        "takeTrade": result.get("takeTrade"),
        "latencyMs": result.get("latencyMs"),
        "provider": result.get("provider"),
        "symbol": desk.get("symbol"),
        "price": desk.get("price"),
    }
    with _JEV_HISTORY_LOCK:
        _JEV_HISTORY.insert(0, row)
        del _JEV_HISTORY[_JEV_HISTORY_MAX:]
        history = list(_JEV_HISTORY)

    base.update(
        {
            "status": "ok",
            "message": "Jev answered. Compare only — desk still owns paper execution.",
            "jev": result,
            "agreement": agree,
            "history": history,
            "statePreview": state,
        }
    )
    return base


def _env_typesafe_only() -> str:
    """TypeSafe-only key (exclude OpenRouter) for resolve_route fallback."""
    import os

    return str(os.getenv("TYPESAFE_API_KEY") or os.getenv("NEXUS_JEV_API_KEY") or "").strip()

@app.get("/api/market/snapshot")
def market_snapshot() -> dict[str, Any]:
    symbols = ["BTC/USD", "ETH/USD"]
    assets = []
    for symbol in symbols:
        try:
            assets.append(kraken_public.ticker(symbol))
        except Exception as exc:  # noqa: BLE001
            assets.append({"symbol": symbol, "error": str(exc), "venue": "Kraken"})
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "assets": assets,
        "volatilityStatus": "normal",
        "sentimentScore": None,
        "sentimentLabel": None,
        "fearGreedIndex": None,
        "source": "kraken_rest_public_ticker",
        "sourceLabel": "Kraken REST public ticker",
        "refreshSeconds": 15,
        "changeBasis": "Kraken UTC day open",
        "isMock": False,
    }


@app.get("/api/market/ohlc")
def market_ohlc(
    symbol: str = "BTC/USD",
    interval: int = 5,
    limit: int = 120,
) -> dict[str, Any]:
    """Public Kraken OHLC series for the Market page chart. No API keys."""
    allowed = {1, 5, 15, 30, 60, 240, 1440}
    if interval not in allowed:
        raise HTTPException(status_code=400, detail=f"interval must be one of {sorted(allowed)}")
    limit = max(20, min(int(limit), 320))
    sym = (symbol or "BTC/USD").upper().replace("-", "/")
    try:
        rows = kraken_public.ohlc(sym, interval=interval)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Kraken OHLC failed: {exc}") from exc
    candles = []
    for row in rows[-limit:]:
        # Kraken: [time, open, high, low, close, vwap, volume, count]
        candles.append(
            {
                "t": int(row[0]),
                "o": float(row[1]),
                "h": float(row[2]),
                "l": float(row[3]),
                "c": float(row[4]),
                "v": float(row[6]),
            }
        )
    last = candles[-1]["c"] if candles else None
    first = candles[0]["c"] if candles else None
    change = (last - first) if last is not None and first is not None else None
    change_pct = ((change / first) * 100.0) if change is not None and first else None
    return {
        "symbol": sym,
        "interval": interval,
        "venue": "Kraken",
        "source": "kraken_rest_public_ohlc",
        "sourceLabel": "Kraken REST public OHLC",
        "candles": candles,
        "last": last,
        "change": change,
        "changePercent": change_pct,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "isMock": False,
    }


@app.get("/api/mission_control")
def mission_control() -> dict[str, Any]:
    engine = get_engine()
    settings = _settings()
    state = engine.health_snapshot()
    active = state["status"] == "running"
    return {
        "activeAgentCount": 3 if active else 0,
        "degradedAgentCount": 3 if state["status"] == "degraded" else 0,
        "offlineAgentCount": 3 if state["status"] == "paused" else 0,
        "engineStatus": state["status"],
        "currentMode": "paper",
        "riskLevel": "high" if state["status"] == "degraded" else "normal",
        "tradingAllowed": False,
        "systemStatus": "go" if active else "blocked",
        "reason": "Paper monitoring is active; live order execution is not implemented.",
        "lastDecision": engine.last_heartbeat,
        "decisionContext": "Dashboard controls manage the in-process paper observer. Live orders stay gated.",
        "primaryRisk": "Paper uses public market data. Simulated results omit trading costs.",
        "recommendedAction": "monitor",
    }


@app.get("/api/decisions")
def decisions(limit: int = 30) -> dict[str, Any]:
    engine = get_engine()
    rows = engine.decisions[: max(1, min(limit, 100))]
    return {"decisions": rows, "total": len(engine.decisions)}


@app.get("/api/paper/events")
def paper_events(kind: str | None = None, limit: int = 100) -> dict[str, Any]:
    """Recorded cycles and simulated trade entries/exits on the configured volume."""
    store = get_engine().store
    if not store:
        return {"durable": False, "events": [], "message": "Set NEXUS_STATE_DB on a persistent volume."}
    if kind not in {None, "cycle", "trade"}:
        raise HTTPException(status_code=400, detail="kind must be cycle or trade")
    return {"durable": True, "events": store.events(kind=kind, limit=limit)}


@app.get("/api/agents")
def agents() -> dict[str, Any]:
    engine = get_engine()
    hb = engine.last_heartbeat
    state = engine.health_snapshot()
    status = "active" if state["status"] == "running" else state["status"]
    return {
        "updatedAt": utc_now(),
        "agents": [
            {"name": "Paper cycle runner", "status": status, "lastHeartbeat": hb, "description": "In-process paper loop.", "latencyMs": 0},
            {"name": "Signal packet", "status": status, "lastHeartbeat": hb, "description": "Latest engine signal artifact.", "latencyMs": 0},
            {"name": "Paper execution ledger", "status": status, "lastHeartbeat": hb, "description": "Simulated execution ledger.", "latencyMs": 0},
        ],
    }


@app.get("/api/logs")
def logs(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    engine = get_engine()
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    rows = engine.logs[offset : offset + limit]
    return {"logs": rows, "total": len(engine.logs), "limit": limit, "offset": offset}


@app.get("/api/control/status")
def control_status() -> dict[str, Any]:
    settings = _settings()
    engine = get_engine()
    state = engine.health_snapshot()
    return {
        "paperService": {
            "unit": "in-process",
            "active": state["status"] == "running",
            "activeState": state["status"],
            "enabled": True,
            "enabledState": "enabled",
        },
        "liveService": {
            "unit": "disabled-in-template",
            "active": False,
            "activeState": "inactive",
            "enabled": False,
            "enabledState": "disabled",
        },
        "emergencyStop": {"active": False, "reason": None, "updatedAt": None},
        "liveControls": {
            "serverLiveArmAllowed": settings.can_arm_live,
            "krakenCredentialsConfigured": settings.live_keys_configured,
            "limits": {
                "maxExposureUsd": 100.0,
                "maxOrders": 3,
                "allowedMarkets": ["BTC/USD", "ETH/USD"],
                "allowedDirections": ["BUY_ONLY", "SELL_ONLY"],
            },
            "activeSession": {},
        },
        "updatedAt": utc_now(),
    }


@app.get("/api/commands")
def commands(limit: int = 8) -> dict[str, Any]:
    engine = get_engine()
    return {"commands": engine.commands[: max(1, min(limit, 40))]}


@app.post("/api/command")
async def command(
    request: Request,
    x_nexus_control_password: str | None = Header(default=None),
) -> dict[str, Any]:
    _check_control_password(x_nexus_control_password)
    body = await request.json()
    action = str(body.get("action") or body.get("command") or "").upper()
    engine = get_engine()
    if action in {"REFRESH", "SYNC"}:
        engine.refresh()
    elif action in {"RESTART"}:
        engine.restart()
    elif action in {"PAUSE", "STOP"}:
        engine.pause()
    elif action in {"RESUME", "START"}:
        engine.resume()
    elif action in {"LIVE_ARM", "ARM_LIVE"}:
        raise HTTPException(
            status_code=400,
            detail="Live order execution is not implemented in this Desk.",
        )
    else:
        engine._command(action or "UNKNOWN", "No-op in template.")
    return {"ok": True, "action": action, "at": utc_now()}


@app.get("/api/settings")
def settings_get() -> dict[str, Any]:
    settings = _settings()
    engine = get_engine()
    state = engine.health_snapshot()
    live_active = False
    return {
        "updatedAt": utc_now(),
        "envPath": "Railway variables / .env",
        "confirmationPhrase": "I_ACCEPT_CONFIG_RISK",
        "restartableServices": ["nexus-paper.service", "in-process-paper"],
        "control": {
            "paperService": {
                "unit": "in-process",
                "active": state["status"] == "running",
                "activeState": state["status"],
                "enabled": True,
                "enabledState": "enabled",
            },
            "liveService": {
                "unit": "disabled",
                "active": live_active,
                "activeState": "inactive",
                "enabled": False,
                "enabledState": "disabled",
            },
        },
        "options": [
            {
                "key": "NEXUS_TRADE_SYMBOL",
                "label": "Trade Symbol",
                "value": settings.trade_symbol,
                "group": "market",
                "category": "market",
                "type": "string",
                "default": "BTC/USD",
                "description": "Kraken pair the paper observer watches.",
                "effectiveSource": "process",
                "restartServices": ["nexus-paper.service"],
            },
            {
                "key": "NEXUS_LOOP_INTERVAL",
                "label": "Engine Loop Interval",
                "value": str(settings.loop_interval),
                "group": "timing",
                "category": "timing",
                "type": "integer",
                "min": 15,
                "max": 3600,
                "unit": "sec",
                "default": "120",
                "description": "Seconds between paper observer ticks.",
                "effectiveSource": "process",
                "restartServices": ["nexus-paper.service"],
            },
            {
                "key": "NEXUS_SCALP_SL_PCT",
                "label": "Stop Loss %",
                "value": str(settings.stop_loss_pct),
                "group": "risk",
                "category": "risk",
                "type": "number",
                "step": 0.0001,
                "default": "0.0035",
                "description": "Paper stop-loss as a fraction of entry (0.0035 = 0.35%).",
                "effectiveSource": "process",
                "guard": "risk",
                "restartServices": ["nexus-paper.service"],
            },
            {
                "key": "NEXUS_SCALP_TP_PCT",
                "label": "Take Profit %",
                "value": str(settings.take_profit_pct),
                "group": "risk",
                "category": "risk",
                "type": "number",
                "step": 0.0001,
                "default": "0.008",
                "description": "Paper take-profit as a fraction of entry (0.008 = 0.8%).",
                "effectiveSource": "process",
                "guard": "risk",
                "restartServices": ["nexus-paper.service"],
            },
            {
                "key": "NEXUS_SCALP_POSITION_USD",
                "label": "Paper Position Size",
                "value": str(settings.position_usd),
                "group": "risk",
                "category": "risk",
                "type": "number",
                "step": 1,
                "unit": "USD",
                "default": "25",
                "description": "Notional size for each paper scalp.",
                "effectiveSource": "process",
                "guard": "risk",
                "restartServices": ["nexus-paper.service"],
            },
            {
                "key": "NEXUS_PAPER_ONLY",
                "label": "Paper Only",
                "value": "1" if settings.paper_only else "0",
                "group": "safety",
                "category": "safety",
                "type": "boolean",
                "default": "1",
                "description": "Railway-only. This Desk has no live order execution path.",
                "effectiveSource": "env_file",
                "guard": "live",
            },
        ],
        "secretStatuses": [
            {"key": "KRAKEN_API_KEY", "configured": bool(settings.kraken_api_key)},
            {"key": "KRAKEN_API_SECRET", "configured": bool(settings.kraken_api_secret)},
        ],
        "readOnlyModeFlags": [
            {
                "key": "NEXUS_PAPER_ONLY",
                "value": "1" if settings.paper_only else "0",
                "configured": True,
                "editable": False,
                "reason": "Change in Railway variables, then redeploy. Paper is the default for buyers.",
            },
            {
                "key": "NEXUS_DASHBOARD_ALLOW_LIVE_ARM",
                "value": "1" if settings.allow_live_arm else "0",
                "configured": True,
                "editable": False,
                "reason": "Live order execution is not implemented in this Desk.",
            },
        ],
        "buyerHint": "Paper needs no exchange keys. This Desk cannot place live orders.",
    }


_RUNTIME_SETTINGS = {
    "NEXUS_TRADE_SYMBOL",
    "NEXUS_LOOP_INTERVAL",
    "NEXUS_SCALP_SL_PCT",
    "NEXUS_SCALP_TP_PCT",
    "NEXUS_SCALP_POSITION_USD",
}


@app.post("/api/settings")
async def settings_post(request: Request, x_nexus_control_password: str | None = Header(default=None)) -> dict[str, Any]:
    """Apply runtime paper knobs in-process. Safety flags stay Railway-only."""
    _check_control_password(x_nexus_control_password)
    body = await request.json()
    changes = body.get("changes") or {}
    if not isinstance(changes, dict) or not changes:
        raise HTTPException(status_code=400, detail="No changes provided")

    confirmation = str(body.get("confirmation") or "").strip()
    blocked = []
    applied = {}
    for key, raw in changes.items():
        key = str(key)
        value = "" if raw is None else str(raw).strip()
        if key in {"NEXUS_PAPER_ONLY", "NEXUS_DASHBOARD_ALLOW_LIVE_ARM", "KRAKEN_API_KEY", "KRAKEN_API_SECRET"}:
            blocked.append(key)
            continue
        if key not in _RUNTIME_SETTINGS:
            blocked.append(key)
            continue
        if key == "NEXUS_LOOP_INTERVAL":
            try:
                value = str(max(15, int(float(value))))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"Invalid {key}") from exc
        os.environ[key] = value
        applied[key] = value

    if blocked and confirmation != "I_ACCEPT_CONFIG_RISK" and not applied:
        raise HTTPException(
            status_code=400,
            detail="Those flags are Railway-only on this template. Change them in the Railway variables panel, then redeploy.",
        )
    if blocked and not applied:
        raise HTTPException(
            status_code=400,
            detail=f"Blocked (set in Railway, not here): {', '.join(blocked)}",
        )
    if not applied:
        raise HTTPException(status_code=400, detail="No runtime-safe changes to apply")

    engine = get_engine()
    restart_raw = body.get("restartServices")
    restart = bool(restart_raw) if not isinstance(restart_raw, list) else len(restart_raw) > 0
    if restart:
        engine.restart()
    else:
        engine.settings = load_settings()

    payload = settings_get()
    msg = f"Applied {', '.join(applied)}."
    if blocked:
        msg += f" Skipped Railway-only keys: {', '.join(blocked)}."
    if restart:
        msg += " Paper observer restarted."
    return {"ok": True, "message": msg, "settings": payload, "applied": applied, "blocked": blocked}


@app.get("/api/instance/workload")
def instance_workload() -> dict[str, Any]:
    settings = _settings()
    engine = get_engine()
    state = engine.health_snapshot()
    signal = engine.latest_signal or {}
    execution = engine.latest_execution or {}
    return {
        "generatedAt": utc_now(),
        "instance": {
            "hostname": "nexus-desk-railway",
            "runtimeRoot": "/app",
            "pythonVersion": "3.12",
            "uptime": f"cycle {engine.cycle}",
        },
        "summary": {
            "mode": "paper_only" if settings.paper_only else "mixed",
            "paperState": state["status"],
            "liveState": "inactive",
            "realOrdersEnabled": False,
            "cycle": engine.cycle,
            "symbol": signal.get("symbol"),
            "action": signal.get("action"),
            "confidence": signal.get("confidence"),
            "currentPrice": signal.get("current_price"),
            "executionReason": signal.get("execution_reason"),
        },
        "services": [
            {
                "ok": True,
                "unit": "Railway desk process",
                "active": True,
                "activeState": "active",
                "subState": "running",
                "enabledState": "n/a",
                "mainPid": os.getpid(),
                "message": "Single Railway service: UI + paper observer.",
            },
            {
                "ok": state["status"] == "running",
                "unit": "In-process paper loop",
                "active": state["status"] == "running",
                "activeState": state["status"],
                "subState": state["status"],
                "enabledState": "n/a",
                "mainPid": os.getpid(),
                "message": "In-process paper loop (no second host).",
            },
        ],
        "artifacts": {
            "runtimeStatus": {
                "ok": True,
                "updatedAt": engine.last_heartbeat,
                "data": {
                    "state": state["status"],
                    "mode": "paper_only",
                    "real_orders_enabled": False,
                    "current_cycle": engine.cycle,
                },
            },
            "latestSignal": {"ok": bool(signal), "updatedAt": signal.get("timestamp_utc"), "data": signal},
            "latestExecution": {"ok": bool(execution), "updatedAt": execution.get("timestamp_utc"), "data": execution},
            "openPositions": {
                "ok": True,
                "updatedAt": engine.last_heartbeat,
                "data": {"position_count": len(engine.open_positions), "active_symbols": ", ".join(sorted({str(p.get("symbol", "")) for p in engine.open_positions if p.get("symbol")})) or "none"},
            },
        },
        "journals": {},
    }


@app.get("/api/research/status")
def research_status() -> dict[str, Any]:
    return {
        "state": "not_started",
        "message": "Research lane lives in Critical-Mass-Lab. Point NEXUS_SCORECARD_URL at a lab scorecard when you want it on the desk.",
        "research_only": True,
        "orders_possible": False,
    }


@app.get("/scorecard.json")
def scorecard_proxy() -> Any:
    settings = _settings()
    local = ROOT / "scorecard.json"
    if settings.scorecard_url:
        req = urllib.request.Request(
            settings.scorecard_url,
            headers={"User-Agent": "nexus-desk-template/1.0"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return JSONResponse(json.loads(resp.read().decode()))
    if local.exists():
        return FileResponse(local)
    sibling = ROOT.parent / "scorecard.json"
    if sibling.exists():
        return FileResponse(sibling)
    raise HTTPException(status_code=404, detail="No scorecard configured")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(PUBLIC / "index.html")


@app.get("/status")
@app.get("/core")
@app.get("/market")
@app.get("/controls")
@app.get("/settings")
@app.get("/instance")
@app.get("/logs")
@app.get("/analytics")
def spa_routes() -> FileResponse:
    return FileResponse(PUBLIC / "index.html")


if (PUBLIC / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(PUBLIC / "assets")), name="assets")

if (PUBLIC / "images").exists():
    app.mount("/images", StaticFiles(directory=str(PUBLIC / "images")), name="images")

if (PUBLIC / "brand").exists():
    app.mount("/brand", StaticFiles(directory=str(PUBLIC / "brand")), name="brand")


@app.get("/favicon.svg")
def favicon() -> FileResponse:
    mark = PUBLIC / "brand" / "nexus-mark.svg"
    if mark.exists():
        return FileResponse(mark)
    return FileResponse(PUBLIC / "favicon.svg")


@app.get("/control-auth.js")
def control_auth() -> FileResponse:
    return FileResponse(PUBLIC / "control-auth.js")


@app.get("/analytics.js")
def analytics_script() -> FileResponse:
    return FileResponse(PUBLIC / "analytics.js")


@app.get("/paper-only-ui.js")
def paper_only_ui() -> FileResponse:
    return FileResponse(PUBLIC / "paper-only-ui.js")
