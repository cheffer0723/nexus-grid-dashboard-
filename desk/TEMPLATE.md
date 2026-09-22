# Nexus Grid Desk

**Paper trading operator desk you can deploy in one click.**  
No exchange keys required to try it. Optional Kraken keys only if you later arm live.

## Marketplace assets

- Icon (512×512): [`public/template-icon.png`](public/template-icon.png)
- Raw URL on this branch (paste into Railway template image field):

```text
https://raw.githubusercontent.com/cheffer0723/nexus-grid-dashboard-/cursor/nexus-desk-template-ee93/desk/public/template-icon.png
```

After merge to `main`, use:

```text
https://raw.githubusercontent.com/cheffer0723/nexus-grid-dashboard-/main/desk/public/template-icon.png
```

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/new)

> After you publish the template in Railway, replace the button URL with your template link from **Workspace → Templates**.

## What this is

A single Railway service that runs:

- Operator UI (status, market, core, logs, control, config, instance)
- In-process paper observer on public Kraken BTC/USD (and ETH ticker)
- Health check at `/api/health`
- Optional research scorecard panel (bundled replay JSON)

It is a **desk template**, not a claim of edge. The bundled regime scorecard is an honest research replay: these fixed rules lagged buy-and-hold on the published window.

## Appetite test positioning

Ship this to see who deploys a paper desk:

- Traders who want a control surface before wiring a broker
- Builders who want a Railway-native starting point
- People who will bounce if signup asks for four API keys up front

**Default deploy = zero secrets.** Live stays gated.

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

## Repo layout

This package lives in the `desk/` folder of [`nexus-grid-dashboard-`](https://github.com/cheffer0723/nexus-grid-dashboard-).

When creating the Railway template service:

- **Source:** that GitHub repo (public)
- **Root directory:** `desk`
- **Healthcheck:** `/api/health`
- **Public HTTP:** enabled (container port `8080`)

## Local

```bash
cd desk
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --host 127.0.0.1 --port 8080
```

## Related

- **Critical-Mass-Lab** — research, algorithms, scorecards, later ML (separate Railway project, no buyer keys).
- Live demo: `https://nexus.supersym.xyz`
