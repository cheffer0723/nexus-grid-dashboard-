"""Live-trading readiness checks (spec: docs/LIVE_READINESS_SPEC.md).

This only REPORTS what is missing. This Desk has no live-order code, so `live_allowed`
is always False no matter how many checks pass. Each gate says plainly what is missing
and where to set it. Anything that needs an exchange adapter that does not exist yet
is reported as "not checked", never as passed.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from .config import Settings

_DAYS_VERIFICATION_VALID = 30


def _positive(env: Mapping[str, str], name: str) -> bool:
    try:
        return float(str(env.get(name, "")).strip()) > 0
    except ValueError:
        return False


def _verification_ok(store: Any) -> tuple[bool, str]:
    if store is None:
        return False, "No journal is attached (set NEXUS_STATE_DB), so no verification record can be kept."
    try:
        rows = store.history(kind="verification", limit=1)
    except Exception:  # noqa: BLE001
        return False, "The journal could not be read."
    if not rows:
        return False, "No verification run has been recorded."
    row = rows[0]
    try:
        when = datetime.fromisoformat(row["at"].replace("Z", "+00:00"))
    except ValueError:
        return False, "The last verification record has an unreadable date."
    if datetime.now(timezone.utc) - when > timedelta(days=_DAYS_VERIFICATION_VALID):
        return False, f"The last verification run ({row['at']}) is older than {_DAYS_VERIFICATION_VALID} days."
    if not row["data"].get("ok"):
        return False, f"The last verification run ({row['at']}) had failures."
    return True, f"Passed on {row['at']}."


def evaluate(settings: Settings, store: Any = None, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    env = os.environ if env is None else env
    gates: list[dict[str, str]] = []

    def gate(key: str, label: str, status: str, detail: str, fix: str = "") -> None:
        gates.append({"key": key, "label": label, "status": status, "detail": detail, "fix": fix})

    gate(
        "exchange_keys", "Exchange keys present",
        "pass" if settings.live_keys_configured else "fail",
        "Kraken key and secret are set on the server." if settings.live_keys_configured
        else "No exchange keys are set on the server.",
        "" if settings.live_keys_configured
        else "Add KRAKEN_API_KEY and KRAKEN_API_SECRET in the Railway variables panel (never in the browser). Other exchanges arrive with their adapters.",
    )
    gate("keys_work", "Keys work", "not_checked",
         "Not checked: the exchange adapter that makes a harmless test call does not exist yet.")
    gate("key_permissions", "Key permissions: trade on, withdrawals off", "not_checked",
         "Not checked: needs the exchange adapter. Until then, confirm this yourself in the exchange's key settings.")
    fee_ok = _positive(env, "NEXUS_FEE_MAKER_PCT") and _positive(env, "NEXUS_FEE_TAKER_PCT")
    gate("fees", "Fee tier entered", "pass" if fee_ok else "fail",
         "Maker and taker fees are set." if fee_ok else "Maker and taker fees are not both set.",
         "" if fee_ok else "Set NEXUS_FEE_MAKER_PCT and NEXUS_FEE_TAKER_PCT in Railway (for example 0.25 and 0.40, as a percent).")
    missing = [n for n in ("NEXUS_MAX_ORDER_USD", "NEXUS_MAX_DAILY_LOSS_USD", "NEXUS_MAX_OPEN_EXPOSURE_USD")
               if not _positive(env, n)]
    gate("risk_caps", "Risk caps set", "pass" if not missing else "fail",
         "Max order size, max daily loss and max open exposure are set." if not missing
         else "Missing: " + ", ".join(missing) + ".",
         "" if not missing else "Set the missing variable(s) in Railway to a number above zero.")
    pw = settings.control_password
    weak = len(pw) < 12
    gate("control_password", "Control password set", "pass" if pw and not weak else "fail",
         "A control password of 12 or more characters is set." if pw and not weak
         else ("No control password is set." if not pw else "The control password is shorter than 12 characters."),
         "" if pw and not weak else "Set NEXUS_CONTROL_PASSWORD in Railway to a long, unique value.")
    gate("balance", "Balance readable", "not_checked",
         "Not checked: needs the exchange adapter to read the account balance.")
    ok, detail = _verification_ok(store)
    gate("verification", "Control verification passed recently", "pass" if ok else "fail", detail,
         "" if ok else "Run scripts/verify_controls.py against this Desk with --record.")
    gate("switch_on", "Deliberate switch-on", "fail",
         "Live trading has never been switched on, and the switch does not exist in this version.")

    passed = sum(1 for g in gates if g["status"] == "pass")
    return {
        "liveAllowed": False,
        "liveBlockedBecause": "This version has no live-order code. The checks below show what a user would need to set up first.",
        "gatesPassed": passed,
        "gatesTotal": len(gates),
        "gates": gates,
    }
