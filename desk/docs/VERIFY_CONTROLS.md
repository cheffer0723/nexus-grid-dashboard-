# How to check that every control on the Nexus Desk really works

Written for a person who has just deployed the Desk and wants proof, not promises.
The Desk is paper-only: nothing here can place a real order.

## The idea in one line
For every button or dial: **do it, then look somewhere else to see if it really happened.**
A green "OK" from the screen proves nothing; the engine's own status, the saved setting, and the history log are the proof.

## Step 1 — Run the automatic check (2 minutes)
    python scripts/verify_controls.py https://YOUR-DESK-ADDRESS YOUR_CONTROL_PASSWORD
It presses every Control Deck button by the exact name the screen sends, changes the risk dials and puts them back,
and prints PASS or FAIL on each line. Any FAIL means that control is broken. Save the output with the date.

## Step 2 — Eyes-on check in the browser (5 minutes)
| Control (where) | Do this | You should see | Where to confirm |
|---|---|---|---|
| Protected controls tab (bottom right) | Open it, type the password, Save | "Password available in this tab" | Pause button now works (below) |
| Pause (Control) | Press | Engine state turns PAUSED; Resume lights up | Status page, Command history row "PAUSE" |
| Resume (Control) | Press | Engine state RUNNING again within ~2 min tick | Command history "RESUME" |
| Emergency stop (Control) | Press | Engine PAUSED | Command history "EMERGENCY_STOP"; no new paper trades after it |
| Restart (Control) | Press | RUNNING, cycle count restarts | History "RESTART" |
| Refresh (Control) | Press | Heartbeat time jumps to now | History "REFRESH" |
| Risk dials (Settings): stop loss, take profit, position size, loop interval, symbol | Change one, Save, reload the page | The new value is still there | Next paper trade uses it (Engine page); restore afterwards |
| Chart pair and time buttons (Market) | Click BTC/ETH and 1M/5M/15M/1H | Chart redraws; "last price" and range change | Compare price with kraken.com for the same pair |
| Regime scorecard tab | Open it | Four engines listed with hit rate and points | Matches `/scorecard.json` |
| Left menu / phone tab bar | Visit all 7 pages | Each loads real data, no empty boxes | Network tab shows `/api/...` calls answering 200 |

## Step 3 — Follow one decision from start to finish (the audit trail)
Pick one paper trade the Desk makes and confirm all four places agree:
1. **Decision** — Engine page / `/api/decisions`: why it entered (EMA/RSI reading, price).
2. **Event** — `/api/paper/events`: the simulated order, with entry price and time.
3. **Log** — Logs page / `/api/logs`: the matching line at the same time.
4. **Result** — when it closes (stop or target), realised profit/loss matches `(exit-entry)/entry × size`.
If one place is missing, data collection is broken. Note: the Desk simulation leaves out fees, spread and slippage, so its profit numbers are better than real trading would be.

## Step 4 — Survive a restart
Note cycle count and closed-trade count. Redeploy/restart the Railway service. Both numbers should carry on, not reset to zero (the journal lives on the `/data` volume). If they reset, the volume is not attached.

## Step 5 — Things that must be refused
- Any button without the password: refused (401).
- "Arm live trading": refused. Changing Kraken keys or the paper-only flag from the screen: refused.
If any of these succeed, stop and do not use the Desk.

## Known gaps found while writing this (as of 2026-11-14)
- The "Emergency stop" button pauses the engine but the screen's "Emergency stop clear / active" badge always reads clear, because the server never records it. Treat PAUSED as the truth.
- Page text is baked into a compiled bundle with no readable source in the repo, so layout can only be adjusted through the add-on stylesheet, not by editing the page itself.
- Verifying against the live Railway address has not been done in this write-up; run Step 1 against it.
