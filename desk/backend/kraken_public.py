"""Public Kraken REST helpers. No API keys required."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

PAIR_MAP = {
    "BTC/USD": "XBTUSD",
    "XBT/USD": "XBTUSD",
    "ETH/USD": "ETHUSD",
}

DISPLAY = {
    "BTC/USD": ("Bitcoin", "BTC/USD"),
    "ETH/USD": ("Ethereum", "ETH/USD"),
}


def to_pair(symbol: str) -> str:
    key = symbol.upper().replace("-", "/")
    return PAIR_MAP.get(key, key.replace("/", ""))


def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    query = urllib.parse.urlencode(params or {})
    url = f"https://api.kraken.com{path}"
    if query:
        url = f"{url}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "nexus-desk-template/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode())
    if payload.get("error"):
        raise RuntimeError("; ".join(payload["error"]))
    return payload.get("result") or {}


def ticker(symbol: str) -> dict[str, Any]:
    pair = to_pair(symbol)
    result = _get("/0/public/Ticker", {"pair": pair})
    row = next(iter(result.values()))
    last = float(row["c"][0])
    bid = float(row["b"][0])
    ask = float(row["a"][0])
    vwap = float(row["p"][1])
    low = float(row["l"][1])
    high = float(row["h"][1])
    vol = float(row["v"][1])
    trades = int(float(row["t"][1]))
    open_px = float(row["o"])
    change = last - open_px
    change_pct = (change / open_px) if open_px else 0.0
    spread_bps = ((ask - bid) / last * 10000.0) if last else 0.0
    name, market = DISPLAY.get(symbol.upper().replace("-", "/"), (symbol, symbol))
    return {
        "symbol": symbol.upper().replace("-", "/"),
        "name": name,
        "market": market,
        "pair": pair,
        "venue": "Kraken",
        "price": last,
        "change24h": change,
        "changePercent24h": change_pct * 100.0,
        "bid": bid,
        "ask": ask,
        "vwap": vwap,
        "low": low,
        "high": high,
        "volume": vol,
        "trades": trades,
        "spreadBps": spread_bps,
    }


def ohlc(symbol: str, interval: int = 1) -> list[list[Any]]:
    pair = to_pair(symbol)
    result = _get("/0/public/OHLC", {"pair": pair, "interval": interval})
    key = next((k for k in result.keys() if k != "last"), None)
    if not key:
        return []
    return result.get(key) or []
