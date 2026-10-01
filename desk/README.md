# Nexus Desk (trader template)

One Railway service. One variables panel. Paper trading needs **no exchange keys**.

Marketplace / appetite-test overview: [`TEMPLATE.md`](TEMPLATE.md)

## What deployers fill in

| When | Variables |
|---|---|
| Paper (default) | Nothing. Public Kraken market data only. |
| Use control writes | Set `NEXUS_CONTROL_PASSWORD`; writes fail closed when absent |
| Keep a durable paper journal | Mount a Railway volume at `/data`; set `NEXUS_STATE_DB=/data/nexus-desk.sqlite3` |
| Allow paid Jev comparisons | Set a control password, persistent state DB, provider key, and `NEXUS_JEV_CALLS_ENABLED=1`; default cap is three attempted calls per UTC day |
| Live trading | Not implemented in this Desk; keys and flags do not enable order execution |
| Research card (optional) | `NEXUS_SCORECARD_URL` pointing at a scorecard JSON |

No DigitalOcean panel. No second host for paper. No Replit URLs. No OpenAI keys for this template.

## Railway template (appetite test)

Published: **[nexus-grid-desk](https://railway.com/deploy/nexus-grid-desk)**

- Service icon on `nexus-grid-webapp`: Python Devicon
- Root directory: `desk`
- Healthcheck: `/api/health`
- Paper default = zero secrets

Keep copy honest: paper desk / operator UI, not “guaranteed alpha.”

## Two repos

1. **This desk** (`desk/`): UI + paper observer + control API → Railway template. The published template points to `main`. The current demo deployment runs a commit from `main`, but its Railway deployment metadata names `cursor/nexus-desk-template-ee93`; verify the service's configured auto-deploy branch before relying on future pushes.
2. **critical-mass-lab**: algorithms, scorecard jobs, future ML → separate Railway project, no buyer keys. Its stopped market-data collector and Postgres are separate from the Desk.

They can share an explicitly supplied scorecard JSON. The Desk does not read the collector database, the old `NexusRuntime` engine, or local HADES/ONYX experiments.

The Desk's paper state uses process memory unless `NEXUS_STATE_DB` points to a persistent mounted volume. When configured, SQLite stores cycle snapshots, signal/setting provenance, and individual simulated trade entry/exit events. Read them through `GET /api/paper/events`; `?kind=trade` filters trades. The daily Jev budget is stored in the same file. A fresh volume cannot recover cycles or individual trades from earlier containers.

`GET /api/health` reports thread liveness, heartbeat age, and errors. A paused paper loop is reported as paused; a degraded loop returns HTTP 503. The website itself remains available for public reads during a pause.

## Local run

```bash
cd desk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --host 127.0.0.1 --port 8080
```

Open http://127.0.0.1:8080/

## GitHub Actions deploy (your own service)

1. GitHub secrets: `RAILWAY_TOKEN`, `RAILWAY_SERVICE_ID`
2. Push changes under `desk/`
3. Workflow `.github/workflows/deploy-desk-railway.yml` runs `railway up` from `desk/`

## Notes

- Bundled UI assets under `public/assets/` match the Nexus operator shell.
- Paper loop is in-process so one container is enough.
- Live arming always returns an error because this Desk has no order execution path.
- ML is later; do not block this template on it.
- Regime scorecard on the page is a research replay, not a live track record.
