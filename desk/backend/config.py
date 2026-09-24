"""Single env config for the desk template. Paper needs no secrets."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str = "") -> str:
    return str(os.getenv(name, default) or "").strip()


def _env_float(name: str, default: float) -> float:
    raw = _env(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if not raw:
        return default
    try:
        return int(float(raw))
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    product_name: str
    paper_only: bool
    trade_symbol: str
    loop_interval: int
    stop_loss_pct: float
    take_profit_pct: float
    position_usd: float
    ohlc_interval_min: int
    vwap_window: int
    kraken_api_key: str
    kraken_api_secret: str
    allow_live_arm: bool
    control_password: str
    scorecard_url: str
    jev_api_key: str
    jev_model: str
    jev_provider: str
    openrouter_api_key: str
    port: int

    @property
    def live_keys_configured(self) -> bool:
        return bool(self.kraken_api_key and self.kraken_api_secret)

    @property
    def jev_configured(self) -> bool:
        return bool(self.openrouter_api_key or self.jev_api_key)

    @property
    def can_arm_live(self) -> bool:
        return (
            not self.paper_only
            and self.allow_live_arm
            and self.live_keys_configured
        )


def load_settings() -> Settings:
    # OpenRouter preferred when TypeSafe console is full; TypeSafe direct still works.
    openrouter_key = _env("OPENROUTER_API_KEY")
    typesafe_key = _env("TYPESAFE_API_KEY") or _env("NEXUS_JEV_API_KEY")
    if openrouter_key:
        provider = "openrouter"
        jev_key = openrouter_key
    elif typesafe_key:
        provider = "typesafe"
        jev_key = typesafe_key
    else:
        provider = ""
        jev_key = ""
    return Settings(
        product_name=_env("NEXUS_PRODUCT_NAME", "Nexus Desk"),
        paper_only=_env_bool("NEXUS_PAPER_ONLY", True),
        trade_symbol=_env("NEXUS_TRADE_SYMBOL", "BTC/USD") or "BTC/USD",
        loop_interval=max(15, _env_int("NEXUS_LOOP_INTERVAL", 120)),
        stop_loss_pct=_env_float("NEXUS_SCALP_SL_PCT", 0.0035),
        take_profit_pct=_env_float("NEXUS_SCALP_TP_PCT", 0.008),
        position_usd=_env_float("NEXUS_SCALP_POSITION_USD", 25.0),
        ohlc_interval_min=max(1, _env_int("NEXUS_SCALP_INTERVAL_MIN", 1)),
        vwap_window=max(5, _env_int("NEXUS_SCALP_VWAP_WINDOW", 20)),
        kraken_api_key=_env("KRAKEN_API_KEY"),
        kraken_api_secret=_env("KRAKEN_API_SECRET"),
        allow_live_arm=_env_bool("NEXUS_DASHBOARD_ALLOW_LIVE_ARM", False),
        control_password=_env("NEXUS_CONTROL_PASSWORD"),
        scorecard_url=_env("NEXUS_SCORECARD_URL"),
        jev_api_key=jev_key,
        jev_model=_env("NEXUS_JEV_MODEL", "jev-latest") or "jev-latest",
        jev_provider=provider,
        openrouter_api_key=openrouter_key,
        port=_env_int("PORT", 8080),
    )
