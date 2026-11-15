# Live-trading readiness and record keeping: design spec (draft, nothing built)

Status: proposal for the owner's review, 2026-11-14 (exchange section revised 2026-11-15). No live-order code exists in the Desk and this spec does not add any.

## 1. Principle
Live trading cannot be switched on until the Desk itself confirms the setup is complete. Paper time served is NOT a gate: paper results say only part of what real money will do, so the gates check configuration, and a small-size ramp gives the real-money evidence.

## 2. Readiness gates
The Desk shows a "Live readiness" panel: one line per gate, each green or red, and a red line says exactly what is missing and where to set it.

| # | Gate | How the server checks it |
|---|---|---|
| 1 | Exchange keys present | Read from the server's environment only; never entered in the browser |
| 2 | Keys work | A harmless read call to the exchange succeeds |
| 3 | Key permissions correct | Trade allowed, withdrawals off (exchange reports this) |
| 4 | Fee tier entered | Maker and taker fee set by the user; paper results then include fees |
| 5 | Risk caps set | Max order size, max daily loss, max open exposure, all above zero |
| 6 | Control password set | Present and not a default |
| 7 | Balance readable | Account balance fetched and at least the user's stated minimum |
| 8 | Verification passed | `scripts/verify_controls.py` result on file for this deployment, recent |
| 9 | Deliberate switch-on | Typed confirmation plus control password; logged |

Rules that hold at all times:
- All gates are re-checked on the server before EVERY live order, not just at switch-on. Removing a key or lowering a cap later stops live orders immediately.
- A failed or unreachable check means refuse (fail closed).
- Going back to paper is always instant. Emergency Stop must work in live mode, cancel open orders, and be recorded.
- First live period is capped at a small order size set by the user, raised only by a deliberate step.

## 3. Record keeping: what is true today
- Durable (survives restart): paper trade events, open positions, closed count and realised result, saved in the SQLite journal on the /data volume.
- Now also durable (built on branch desk-journal-and-history): the decision list, log lines, button presses and every settings change are saved to the journal and restored on restart. The History page (`/history`) and CSV export (`/api/history.csv`) read them. Still missing: retention limits / a size meter for the journal, a tax-style export, and a nav link to History inside the main app.
- Not recorded at all: settings changes, readiness checks, and the settings in force when each trade was made.

## 4. Record keeping: proposed
One append-only journal (new table, never edited or deleted by the app), every row stamped with time and a settings snapshot id:
1. **Decisions**: every signal evaluated, entered or skipped, with inputs (prices, EMA, RSI) and the reason.
2. **Orders and fills**: paper and live kept apart and clearly labelled. For live: requested price, filled price, fee charged, exchange order id.
3. **Commands**: every button press, who authenticated, the result.
4. **Settings changes**: old value, new value, time.
5. **Readiness checks**: each gate result at switch-on and at every live order.
6. **Daily snapshot**: balance, open positions, day result, settings in force.
7. **Errors**: exchange rejections, timeouts, data gaps.

User-facing history:
- A History page with date range, filter by event type, and per-trade drill-down (decision, order, fill, result).
- Download everything as CSV, so a user keeps their own records and tax data without needing us.
- Paper versus live results shown side by side, with the gap between expected and actual fill prices (slippage) reported. This is the most useful honesty feature a paper-to-live product can offer.
- Retention: keep everything by default; a user-visible size meter; export before any purge. Never record the exchange secret in any log.

## 5. Build order (each step small, with its own test)
1. Persist decisions, logs and commands to the journal (fixes the restart gap, paper only). DONE on branch desk-journal-and-history, with the settings-change log, History page, CSV export and the readiness panel (reports only).
2. Settings-change log and settings snapshot per trade.
3. History page and CSV export.
4. Readiness panel and server-side gate checks (still no order code).
5. Exchange layer: the common contract, a fake exchange for tests, then one adapter at a time (Kraken, Coinbase, Gemini first, any other exchange the same way), each marked unverified until its test suite passes.
6. Live order path behind all gates, tiny size cap first, in a separate reviewed change.

## 6. Exchanges: the Desk is exchange-agnostic
The Desk is not limited to any list of exchanges. Any exchange can be added by writing one small adapter; nothing else in the Desk changes.

**One interface, one adapter per exchange.** The Desk talks to a single "exchange" contract: read price, read balance, read fees and minimum sizes, place order, cancel order, read key permissions, report errors. The readiness gates in section 2 are identical for every exchange; the adapter only supplies the answers. The open-source `ccxt` library already speaks to over a hundred exchanges through one common interface (Kraken, Coinbase and Gemini among them), so most adapters would be thin wrappers around it, with a hand-written adapter only where an exchange is not covered.

**Order of work, not a limit.** First adapters, in order: Kraken, Coinbase, Gemini. Others follow the same recipe. (Robinhood is out of scope for now, by the owner's decision, 2026-11-15.)

**Supported means proven.** An exchange shows as "supported" only after its adapter passes the same standard test suite: the exchange's sandbox where one exists, otherwise a tiny real order placed by the owner. Until then it shows "unverified". No exchange is claimed from its documentation alone.

**Gate 3 per exchange.** "Trade on, withdrawals off" can only be verified where the exchange reports what a key may do. Where it cannot, the panel shows "cannot verify, confirm yourself" with the exact steps, and the gate stays red until the user ticks that they confirmed it.

**Notes found in public sources (2026-11-15); verify when building each adapter**
- Gemini: keys carry roles (Trader, Fund Manager, Auditor), and a new key gets the Trader role by default. Withdrawals sit under the separate Fund Manager role, so a Trader-only key is the right shape for the Desk. Gemini runs a full sandbox exchange with test funds at a separate address, and `ccxt` can switch to it with one setting.
- Kraken and Coinbase: how each reports key permissions is still to be confirmed.
- The earlier Coinbase use found in the owner's repos is public price data only, with no keyed trading.

## 7. Open questions for the owner
- Who holds the keys: always the user's own deployment, never ours?
- Minimum balance and the default first-live order size.
- Tax export format wanted, if any.
