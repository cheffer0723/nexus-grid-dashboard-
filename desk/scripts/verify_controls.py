"""Checks every Desk control end to end against a RUNNING Desk (local or Railway).

Usage:  python scripts/verify_controls.py https://your-desk.up.railway.app  YOUR_CONTROL_PASSWORD  [--record]

--record  leaves the result in the Desk's history (counts toward the "verification" readiness check).
          It is self-reported: it shows the check was run, not that anyone audited it.

For each control it does the action, then reads the Desk back to confirm the thing
really changed (not just that the server said "ok"). It prints PASS/FAIL per line and
exits non-zero if anything failed. It changes only paper settings and puts them back.
No live trading exists in this Desk, so nothing here can place a real order.
"""
import sys, time, httpx

args = [a for a in sys.argv[1:] if a != "--record"]
record = "--record" in sys.argv
base, password = args[0].rstrip("/"), args[1]
H = {"x-nexus-control-password": password}
results = []

def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))

c = httpx.Client(timeout=30)
get = lambda p: c.get(base + p).json()
post = lambda p, body, h=H: c.post(base + p, json=body, headers=h)
status = lambda: get("/api/engine/status")["status"]

# 1. The Desk is alive and honest about being paper-only
st = get("/api/engine/status")
check("engine reports paper mode", st["mode"] == "paper", st["mode"])
check("no live keys configured", st.get("liveKeysConfigured") is False)

# 2. Password gate
check("write without password refused", post("/api/command", {"action": "REFRESH"}, {}).status_code in (401, 503))
check("write with wrong password refused", post("/api/command", {"action": "REFRESH"}, {"x-nexus-control-password": "wrong"}).status_code == 401)

# 3. Every Control Deck button: send the EXACT name the button sends, then confirm the engine changed
for sent, want in (("paper_pause", "paused"), ("paper_resume", "running"), ("emergency_stop", "paused"),
                   ("paper_restart", "running"), ("refresh", "running")):
    r = post("/api/command", {"action": sent})
    time.sleep(2)
    check(f"button '{sent}' -> engine {want}", r.status_code == 200 and status() == want, f"http {r.status_code}, engine {status()}")

# 4. Command history records what was pressed
hist = [x["action"] for x in get("/api/commands?limit=20")["commands"]]
check("command history lists the presses", all(a in hist for a in ("PAUSE", "RESUME", "RESTART", "REFRESH")), str(hist[:6]))

# 5. Live trading cannot be switched on
check("live arm refused", post("/api/command", {"action": "LIVE_ARM"}).status_code == 400)

# 6. Settings dials: change each runtime dial, read it back, then restore
opts = {o["key"]: o["value"] for o in get("/api/settings")["options"]}
for key, newval in (("NEXUS_SCALP_SL_PCT", "0.5"), ("NEXUS_SCALP_TP_PCT", "1.0"), ("NEXUS_SCALP_POSITION_USD", "10")):
    if key not in opts:
        check(f"dial {key} exists", False); continue
    old = opts[key]
    r = post("/api/settings", {"changes": {key: newval}, "confirmation": "I_ACCEPT_CONFIG_RISK"})
    back = {o["key"]: o["value"] for o in get("/api/settings")["options"]}.get(key)
    check(f"dial {key} saves and reads back", r.status_code == 200 and float(back) == float(newval), f"sent {newval}, got {back}")
    post("/api/settings", {"changes": {key: old}, "confirmation": "I_ACCEPT_CONFIG_RISK"})
check("safety flags cannot be changed from the screen",
      post("/api/settings", {"changes": {"KRAKEN_API_KEY": "x"}, "confirmation": "I_ACCEPT_CONFIG_RISK"}).status_code == 400)

# 7. Data collection: every page's data source answers and has content
for path in ("/api/market/snapshot", "/api/market/ohlc?symbol=BTC/USD&interval=5", "/api/decisions", "/api/paper/events", "/api/logs", "/api/paper/events"):
    r = c.get(base + path)
    check(f"data feed {path.split('?')[0]} answers", r.status_code == 200, f"http {r.status_code}")

# 8. History and readiness
hist = get("/api/history?kind=command&limit=5")
check("history is recording button presses", hist.get("enabled") is True and len(hist.get("events", [])) > 0,
      "turn on NEXUS_STATE_DB" if not hist.get("enabled") else "")
check("history CSV downloads", c.get(base + "/api/history.csv").status_code == 200)
check("settings changes are in the history", any(e["data"].get("changes") for e in get("/api/history?kind=settings_change&limit=5").get("events", [])))
ready = get("/api/live/readiness")
check("live trading reports itself as blocked", ready.get("liveAllowed") is False)

if record:
    r = post("/api/verification", {"ok": all(results), "passed": sum(results), "failed": len(results) - sum(results)})
    check("result recorded in history", r.status_code == 200, f"http {r.status_code}")

sys.exit(0 if all(results) else 1)
