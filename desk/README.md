# Nexus Desk (trader template)

One Railway service, one persistent volume, and a generated control password. Paper trading needs **no exchange keys**.

Marketplace / appetite-test overview: [`TEMPLATE.md`](TEMPLATE.md)

## What deployers fill in

| When | Variables |
|---|---|
| Paper (default) | Nothing. Public Kraken market data only; the published template includes a `/data` volume and generated password. |
| Use control writes | Reveal the generated `NEXUS_CONTROL_PASSWORD` in Railway Variables and enter it in the Desk. Writes fail closed when absent. |
| Keep a durable paper journal | The published template mounts `/data` and sets `NEXUS_STATE_DB=/data/nexus-desk.sqlite3`. For manual deployments, configure both yourself. |
| Allow paid Jev comparisons | Set a control password, persistent state DB, provider key, and `NEXUS_JEV_CALLS_ENABLED=1`; default cap is three attempted calls per UTC day |
| Live trading | Not implemented in this Desk; keys and flags do not enable order execution |
| Research card (optional) | `NEXUS_SCORECARD_URL` pointing at a scorecard JSON |

No DigitalOcean panel. No second host for paper. No Replit URLs. No OpenAI keys for this template.

## Railway template (appetite test)

Published: **[nexus-grid-desk](https://railway.com/deploy/nexus-grid-desk)**

- Service icon on `nexus-grid-webapp`: Python Devicon
- Root directory: `desk`
- Healthcheck: `/api/health`
- Paper default = no exchange/API keys; one generated control password

Keep copy honest: paper desk / operator UI, not “guaranteed alpha.”

## Two repos

1. **This desk** (`desk/`): UI + paper observer + control API → Railway template. The published template points to `main`. Confirm the demo's deployed revision separately; the template source and demo deployment are different release paths.
2. **critical-mass-lab**: algorithms, scorecard jobs, future ML → separate Railway project, no buyer keys. Its stopped market-data collector and Postgres are separate from the Desk.

They can share an explicitly supplied scorecard JSON. The Desk does not read the collector database, the old `NexusRuntime` engine, or local HADES/ONYX experiments.

The Desk's paper state uses process memory unless `NEXUS_STATE_DB` points to a persistent mounted volume. The published template configures both `/data` and the SQLite path. SQLite stores cycle snapshots, signal/setting provenance, and individual simulated trade entry/exit events. Read them through `GET /api/paper/events`; `?kind=trade` filters trades. The daily Jev budget is stored in the same file. A fresh volume cannot recover cycles or individual trades from earlier containers.

`GET /api/health` reports thread liveness, heartbeat age, and errors. A paused paper loop is reported as paused; a degraded loop returns HTTP 503. The website itself remains available for public reads during a pause.

## Local run

```bash
cd desk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8080
```

Open http://127.0.0.1:8080/

## Releases

Changes to `desk/` on `main` run the GitHub safety tests. The Railway demo should be connected to this repository's `main` branch for automatic deploys. Its actual deployment revision must still be checked after a merge. The workflow's manual `workflow_dispatch` deploy is a fallback and requires GitHub secrets `RAILWAY_TOKEN` and `RAILWAY_SERVICE_ID`; those secrets are not included in this public repository.

## Notes

- Bundled UI assets under `public/assets/` match the Nexus operator shell.
- Paper loop is in-process so one container is enough.
- Live arming always returns an error because this Desk has no order execution path.
- ML is later; do not block this template on it.
- Regime scorecard on the page is a research replay, not a live track record.
