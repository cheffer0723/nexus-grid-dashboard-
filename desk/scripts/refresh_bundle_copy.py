"""Apply audited paper-only copy to the checked-in minified UI bundle.

The original React source is not in this repository. Keep every replacement
explicit and count-checked until the source is recovered and rebuilt properly.
"""

from pathlib import Path


BUNDLE = Path(__file__).resolve().parents[1] / "public" / "assets" / "index-app.js"
REPLACEMENTS = (
    ("Connected · Integrated · Limitless — paper desk, live arming gated.", "Connected · Integrated · Paper-only desk — no real orders.", 1),
    ("Live arming gated", "Live orders unavailable", 1),
    ("DigitalOcean Runtime", "Railway Runtime", 1),
    ("Read-only view into the Nexus droplet: services, latest engine artifact, current cycle, and recent system journal lines.", "Read-only view of this Railway desk: service status, current paper cycle, and recent application log lines.", 1),
    ("Check Droplet", "Refresh Status", 1),
    ("Values are intentionally hidden. Update secrets directly on the droplet env file over SSH.", "Values are hidden here. Manage secrets in your Railway service Variables tab.", 1),
    ("Live Trading Arm", "Live orders unavailable", 1),
    ("Nexus Services", "Runtime Components", 1),
    ("Configuration changes do not authorize live trading. Live orders still require the Control Deck live-arm flow, the exact real-order phrase, a market, direction, exposure cap, and max orders.", "This Desk never sends real orders. Adding exchange keys or flags cannot enable trading.", 1),
    ("Use Control Deck live-arm/stop controls instead of editing these directly.", "Live-order flags are read-only and have no execution path in this template.", 1),
    ("Paper stays active until you deliberately opt in to live.", "Paper mode is the only mode in this template.", 1),
    ("Live Service", "Order Service (absent)", 1),
    ("Arming Available", "Unavailable", 1),
    ("Server Locked", "Not implemented", 1),
    ("GO LIVE", "PAPER REVIEW", 2),
    ("Read-only Live Tripwires", "Live-order safeguards (read-only)", 1),
    ("Paper restart is blocked while the live service is active.", "Paper restart is temporarily unavailable.", 1),
    ("These settings can affect risk, live arming, external calls, or paper execution behavior. Type the exact phrase below to save.", "These settings can affect paper risk, external calls, or paper execution behavior. Type the exact phrase below to save.", 1),
)

DOUBLE_LABELS = (
    ("Real Orders (none) (none)", "Real Orders"),
    ("Live broker (none) (none)", "Live broker"),
    ("Stop Live (unavailable) (unavailable)", "Stop Live"),
    ("Arm Live (unavailable) (unavailable)", "Arm Live"),
)


def main() -> None:
    text = BUNDLE.read_text(encoding="utf-8")
    for doubled, correct in DOUBLE_LABELS:
        text = text.replace(doubled, correct)
    for old, new, count in REPLACEMENTS:
        actual = text.count(old)
        if actual == 0 and text.count(new) >= count:
            continue
        if actual != count:
            raise SystemExit(f"Expected {count} occurrences of {old!r}; found {actual}")
        text = text.replace(old, new)
    BUNDLE.write_text(text, encoding="utf-8", newline="")


if __name__ == "__main__":
    main()
