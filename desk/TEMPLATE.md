# Deploy and Host Nexus Grid Desk with Railway

Nexus Grid Desk is an operator desk for retail traders — status, market, engine, and controls in one Railway service. Start with no exchange keys (safe paper mode); add Kraken keys later only if you want live.

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/nexus-grid-desk)

Published listing: https://railway.com/deploy/nexus-grid-desk

## About Hosting Nexus Grid Desk

Hosting this template means running a single Railway service from the `desk/` folder of the public GitHub repo. Railway builds the Dockerfile, exposes public HTTP on port 8080, and health-checks `/api/health`. The paper loop runs in-process, so you do not need a second worker, database, or DigitalOcean droplet for the appetite-test deploy. Live arming stays gated behind explicit flags and credentials you choose later.

## Common Use Cases

- Spin up a paper trading control surface before wiring a broker
- Share a one-click Railway desk with traders who bounce on multi-key signup
- Demo operator panels (status, market, core, logs, control, config, instance)
- Attach an optional research scorecard JSON for honest regime replay context
- Keep research/ML in a separate project while the desk stays zero-secret by default

## Dependencies for Nexus Grid Desk Hosting

- Public GitHub source: `cheffer0723/nexus-grid-dashboard-` (root directory `desk`)
- Python / FastAPI runtime built from the included Dockerfile
- Public Kraken market data for paper mode (no API keys)
- Optional Kraken API key/secret only if you deliberately enable live

### Deployment Dependencies

- Railway public HTTP networking on the service
- Healthcheck path `/api/health`
- Optional variables documented below (all optional for paper)
- Live demo reference: https://nexus.supersym.xyz

### Why Deploy Nexus Grid Desk on Railway?

Railway is a singular platform to deploy your infrastructure stack. Railway will host your infrastructure so you don't have to deal with configuration, while allowing you to vertically and horizontally scale it. By deploying Nexus Grid Desk on Railway, you are one step closer to supporting a complete full-stack application with minimal burden. Host your servers, databases, AI agents, and more on Railway.

## First-run coach

The desk opens a plain-language **New here?** guide for new traders:

1. You are on paper money  
2. Watch Observe / heartbeat  
3. What Gateway · Core · Sentinel · Vault · Observer mean  
4. Optional live later — where to create Kraken API keys, minimum permissions, Railway variable names, and that Sentinel still gates live arming  

Kraken key links used in the coach:

- https://www.kraken.com/u/security/api  
- https://support.kraken.com/articles/360000919966-how-to-generate-an-api-key-pair  

## Variables (all optional for paper)

| Variable | Default | When to set |
|---|---|---|
| `NEXUS_PAPER_ONLY` | `1` | Keep `1` for the appetite test |
| `NEXUS_TRADE_SYMBOL` | `BTC/USD` | Optional |
| `NEXUS_LOOP_INTERVAL` | `120` | Optional |
| `NEXUS_SCALP_SL_PCT` | `0.0035` | Optional |
| `NEXUS_SCALP_TP_PCT` | `0.008` | Optional |
| `NEXUS_SCALP_POSITION_USD` | `25` | Optional |
| `NEXUS_CONTROL_PASSWORD` | empty | Only if you want to lock control writes |
| `KRAKEN_API_KEY` / `KRAKEN_API_SECRET` | empty | **Not needed for paper** |
| `NEXUS_DASHBOARD_ALLOW_LIVE_ARM` | `0` | Leave off for the template |
| `NEXUS_SCORECARD_URL` | empty | Optional external scorecard JSON |
| `TYPESAFE_API_KEY` | empty | Optional Jev compare on Engine (paper research only; never arms live) |

It is a desk template, not a claim of edge. The bundled regime scorecard is an honest research replay: these fixed rules lagged buy-and-hold on the published window. Optional Jev is the same idea — compare only, never execution.
