# Deploy and Host Nexus Grid Desk with Railway

Nexus Grid Desk is a paper trading operator desk you can deploy in one click. It ships an operator UI plus an in-process paper observer on public Kraken market data. No exchange keys are required to try it. Optional Kraken keys are only needed if you later arm live trading on purpose.

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

It is a desk template, not a claim of edge. The bundled regime scorecard is an honest research replay: these fixed rules lagged buy-and-hold on the published window.
