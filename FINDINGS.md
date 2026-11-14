# Nexus Desk and Algorithm Findings Log

Plain English. One entry per discovery. Newest entries go at the bottom.
Each entry says who established it: **Checked** means Claude verified it from files or data in this session. **Owner's word** means Chris told us and it has not been verified. **Stored result** means a number from a file in a repo that Claude read but did not re-run.

Started: 2026-11-14.

---

## 1. The Desk has no live-order code
- **Status:** Checked.
- The Desk (NEXUS-CONTROL-DESK) only simulates trades. It reads public Kraken prices and writes a paper journal. Having Kraken keys or the live-arm flag set does not let it place real orders.
- Where: `desk/backend/paper_engine.py` and `config.py` in the nexus-grid-dashboard repo.

## 2. How the Desk decides to trade
- **Status:** Checked.
- Every 2 minutes it looks at 1-minute Bitcoin candles. It compares a fast average (9) with a slow average (21), plus a momentum gauge (RSI) that is almost always satisfied.
- Fast above slow: it buys $25 of BTC. Fast below slow: it closes an open buy. It never bets on a fall.
- Exits: loss of 0.35% or gain of 0.8%, checked only every 2 minutes. One position at a time. A price-average gauge (VWAP) is calculated but never used.

## 3. The Desk's first paper results
- **Status:** Checked (journal read through Chris's signed-in browser, about 01:02 UTC Nov 14).
- 7 closed trades, 1 win, 6 losses, net about -$0.10. Fees were not counted.

## 4. Backtest: the Desk's rule has no edge once fees are counted
- **Status:** Checked (our own test, public Kraken trades rebuilt into 1-minute candles).
- Data covered only about 1.5 days (BTC 73,329 to 72,198), so this is a small sample.
- Before fees the Desk's rule was about break-even (-$0.42 on 51 trades). With a 0.26% per-side fee it lost $7.05. The richer Scalper v2 was +$0.12 before fees and lost $15.61 after.
- A coin-flip control using the same exits landed in the same range. A round trip costs about 0.5% in fees against typical moves of about 0.1%.
- Open: 0.26% is the fee the old code assumed. Chris should check his actual Kraken fee tier. A longer re-run is optional.

## 5. The zip library holds about 25 distinct ideas, not 400
- **Status:** Checked (the catalog in `algorithm-lab/catalog/`).
- 168 files, 8 groups of duplicates, roughly 25 different ideas. Chris remembered a "400 algorithms" figure. We could not find it in chat history or repos. It may have come from a different count.

## 6. Scalper v2 is the richer parent of the Desk's rule
- **Status:** Checked (code read, and tested in item 4).
- It adds a confidence score, a 15-minute trend, VWAP, volume, and real shorts. Some of its feeds (order book, macro, COT) need extra data we do not have. After fees it did no better than the Desk (item 4).

## 7. Orthrus (200-day trend rule): tested over 20 years, reduces drawdown, does not add return
- **Status:** Stored result (file `data/backtests/engines.json`, generated 2026-06-23). Claude read the test code and found no peeking at future prices and fees charged on every position change. Claude did not re-run it, because the script downloads Yahoo Finance data.
- Rule: hold while price is above its 200-day average, cash below it.
- Worst drop, Orthrus vs just holding: S&P 500 -21% vs -55%. Nasdaq 100 -27% vs -53%. Small caps -28% vs -59%. Gold -34% vs -46%. Nvidia -55% vs -85%. **Bitcoin -71% vs -83%.** Long Treasuries -47% vs -48%.
- Final return, Orthrus vs holding: S&P 500 +454% vs +815%. Nasdaq 100 +1,033% vs +2,169%. Small caps +205% vs +523%. Bitcoin +15,023% vs +25,108%. Treasuries +2.5% vs +85%.
- Meaning: it works as a risk reducer on stock indexes and gives up a lot of return for that. It helps only modestly on Bitcoin and not at all on bonds.
- **Correction needed in the repo text:** the engines summary says the trend and momentum engines "roughly halved the worst drawdown on the stock and crypto markets." That is true for stock indexes but not for Bitcoin (-83% to -71%). Proposed new wording is in item 16.
- Caveats: most of the benefit comes from 2008 and 2022. Taxes on its ~60 trades are not counted. Daily data, so it is a different product from the Desk's 2-minute scalper.

## 8. Hydra (6-month momentum) and Sisyphus (oversold dips)
- **Status:** Stored result (same file as item 7).
- Hydra: mixed. It cut drawdowns (S&P 500 -23.5% vs -55.2%) and lagged on small caps. Best of the three on long Treasuries.
- Sisyphus: in the market only a sliver of the time. It lost money on Bitcoin (-66% while holding gained +19,275%) and on gold (-12.5%). It is niche and not for one-way markets.

## 9. HADES "cartel co-buy" idea
- **Status:** Stored result (HANDOFF and CARTEL_MIRROR in the hades repo).
- The signal fires when 2 or more of 74 tracked wallets buy the same new token within 180 seconds. Reported out-of-sample hit rates: about 30.8% (2 or more wallets) and 53.6% (3 or more), against a 16.7% base rate.
- The same handoff says the original engine's +104 SOL gain was paper only, and real money was 44 trades for -0.43 SOL.
- The handoff's own bar was at least 100 resolved live signals. We found no result for that forward test.
- The June CODEX_AUDIT flagged the outcome resolver (it uses current price change, not the real peak) and the ancestry worker.

## 10. Other Solana and arbitrage pieces
- **Status:** Checked (code read, not run).
- The Solana momentum scalp is the same logic as the Desk on SOL with stricter filters. Its confidence gate does nothing.
- CEX/DEX arbitrage (Kraken vs Raydium): its own math puts break-even at about 1.1%. It is shadow-only.
- Funding arbitrage: the live part is a TODO.
- The HADES Pump.fun token filter is a stub, so every token passes.

## 11. Third-party code and licences
- **Status:** Checked (credits found in the files).
- The Markov regime classifier is credited to Roan and refactored by Lewis Jackson. Check its licence before selling anything that contains it.
- The Almanak / Quant-python-DEFI zip is a large third-party framework. Do not ship it without checking its licence.

## 12. Secrets scan of the 9 zips
- **Status:** Checked.
- The only secret-looking hits were example and template files. No real keys were found.

## 13. Old servers that may still hold a Kraken key
- **Status:** Stored result (HANDOFF mentions them).
- An AWS EC2 box ("Nexus") whose .env holds a Kraken key and secret, and a Lightsail box ("hades-listener") that may still be billing. If either still exists, check the bill and rotate the key. Not yet verified.

## 14. Live Kraken trading plumbing worked months ago
- **Status:** Owner's word. Chris says real-money orders through the Kraken API were tested months ago. Not verified by Claude.

## 15. Why this was built and how it should be sold
- **Status:** Owner's words and decisions to date.
- Three months of building and extra features gave the feeling of an edge without one. The honest product direction we discussed is a research lab that scores every idea against a coin flip and against just holding, with fees shown, and no profit promises. Single purchase, same product for every buyer, runs on the buyer's own PC. Open: tester only, or full Desk with live trading.

## 16. Proposed wording for item 7 (NOT approved yet)
- Orthrus verdict: "The steady hand, tested over about 20 years including 2008, 2020 and 2022. It trails buy and hold on final return in every market, which is the price of sitting out dips. On the S&P 500, Nasdaq 100 and small caps it cut the worst drop by about half. On Bitcoin it helped less (worst drop -71% versus -83%). On long Treasuries it did almost nothing (-47% versus -48%). A risk reducer for stocks, not a profit engine."

---

## Open questions
- Which launch: tester only, or full Desk with live trading?
- Where is the long BTC minute history, and which parts can legally be sold? (Chris says it can be left out.)
- Chris's real Kraken fee tier.
- Do the old AWS and Lightsail servers still exist?
- Should the Hydra summary line be re-checked too? (QQQ and small caps were not halved by Hydra.)
