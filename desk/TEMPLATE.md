# Deploy and Host Nexus Grid Desk with Railway

Nexus Grid Desk is a paper operator desk for retail traders — status, market, engine, and controls in one Railway service. It has no live order execution path. It does not promise profitable trading.

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/nexus-grid-desk)

Published listing: https://railway.com/deploy/nexus-grid-desk

## About Hosting Nexus Grid Desk

Hosting this template runs one Railway service from the `desk/` folder of the public GitHub repo. Railway builds the Dockerfile, exposes public HTTP on port 8080, and health-checks `/api/health`. The paper loop runs in-process. The template mounts a persistent volume at `/data` for its SQLite paper journal. Railway hosting and volume storage are billable according to your Railway plan; paper trading itself needs no exchange or AI API keys.

## Common Use Cases

- Spin up a paper trading control surface without wiring a broker
- Share a one-click Railway desk with traders who bounce on multi-key signup
- Demo operator panels (status, market, core, logs, control, config, instance)
- Attach an optional research scorecard JSON for honest regime replay context
- Keep research/ML in a separate project; the template generates a unique control password for each deployment

## Dependencies for Nexus Grid Desk Hosting

- Public GitHub source: `cheffer0723/nexus-grid-dashboard-` (root directory `desk`)
- Python / FastAPI runtime built from the included Dockerfile
- Public Kraken market data for paper mode (no API keys)
- No Kraken credentials are needed or used for paper execution; adding them will not enable live orders

### Deployment Dependencies

- Railway public HTTP networking on the service
- Healthcheck path `/api/health`
- The included `/data` volume and `NEXUS_STATE_DB=/data/nexus-desk.sqlite3` preserve paper history across redeploys
- A per-deployment `NEXUS_CONTROL_PASSWORD` is generated; retrieve it from your service's Railway Variables tab before changing controls
- Paid Jev calls are disabled by default, even if you add a provider key
- Live demo reference: https://nexus.supersym.xyz

### Why Deploy Nexus Grid Desk on Railway?

Railway is a singular platform to deploy your infrastructure stack. Railway will host your infrastructure so you don't have to deal with configuration, while allowing you to vertically and horizontally scale it. By deploying Nexus Grid Desk on Railway, you are one step closer to supporting a complete full-stack application with minimal burden. Host your servers, databases, AI agents, and more on Railway.

## First-run coach

The desk opens a plain-language **New here?** guide for new traders:

1. You are on paper money  
2. Watch Observe / heartbeat  
3. What Gateway · Core · Sentinel · Vault · Observer mean  
4. Where to find your control password and paper history

## First deployment

1. Deploy the template on your Railway account. Wait until `/api/health` reports the paper engine running.
2. Open the service **Variables** tab in Railway and reveal/copy the generated `NEXUS_CONTROL_PASSWORD` into the Desk's **Protected controls** field when you want to change paper settings. Do not share it or put it in a public URL.
3. Visit **Instance** and **Logs** to check the heartbeat. The SQLite journal on `/data` records new paper cycles and simulated trade events. A new deployment cannot reconstruct pre-volume history.
4. Keep AI provider keys absent unless you explicitly want optional research comparisons. To enable paid Jev calls, add a provider key and set `NEXUS_JEV_CALLS_ENABLED=1`; the default attempted-call limit is three per UTC day. Provider charges may apply.

## Template variables

| Variable | Default | When to set |
|---|---|---|
| `NEXUS_PAPER_ONLY` | `1` | Keep `1` for the appetite test |
| `NEXUS_TRADE_SYMBOL` | `BTC/USD` | Optional |
| `NEXUS_LOOP_INTERVAL` | `120` | Optional |
| `NEXUS_SCALP_SL_PCT` | `0.0035` | Optional |
| `NEXUS_SCALP_TP_PCT` | `0.008` | Optional |
| `NEXUS_SCALP_POSITION_USD` | `25` | Optional |
| `NEXUS_CONTROL_PASSWORD` | generated unique secret | Required for all control writes and paid Jev calls; keep private |
| `NEXUS_STATE_DB` | `/data/nexus-desk.sqlite3` | Journal on the included `/data` volume |
| `NEXUS_JEV_CALLS_ENABLED` | `0` | Set to `1` only when you want paid Jev calls |
| `NEXUS_JEV_MAX_CALLS_PER_DAY` | `3` | Limit attempted calls per UTC day; requires persistent state DB |
| `KRAKEN_API_KEY` / `KRAKEN_API_SECRET` | empty | **Do not set.** No live execution path exists. |
| `NEXUS_SCORECARD_URL` | empty | Optional external scorecard JSON |
| `OPENROUTER_API_KEY` | empty | Optional Jev compare on Engine via OpenRouter (paper research only) |
| `TYPESAFE_API_KEY` | empty | Optional direct TypeSafe Jev key (if you have console access) |

It is a desk template, not a claim of edge. The bundled regime scorecard is an honest research replay: these fixed rules lagged buy-and-hold on the published window. Optional Jev is the same idea — compare only, never execution.
