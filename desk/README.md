# Nexus Desk (trader template)

One Railway service. One variables panel. Paper trading needs **no exchange keys**.

This is product direction **#2**: the operator desk buyers run. Research and scorecards stay in **Critical-Mass-Lab**.

## What buyers fill in

| When | Variables |
|---|---|
| Paper (default) | Nothing. Public Kraken market data only. |
| Lock control writes (optional) | `NEXUS_CONTROL_PASSWORD` |
| Live later (optional) | `KRAKEN_API_KEY`, `KRAKEN_API_SECRET`, then flip `NEXUS_PAPER_ONLY=0` and `NEXUS_DASHBOARD_ALLOW_LIVE_ARM=1` deliberately |
| Research card (optional) | `NEXUS_SCORECARD_URL` pointing at a Critical-Mass-Lab scorecard JSON |

No DigitalOcean panel. No second host for paper. No Replit URLs. No OpenAI keys for this template.

## Two repos

1. **This desk repo** (`desk/` here, or a renamed `nexus-desk` repo): UI + paper observer + control API → Railway.
2. **critical-mass-lab**: algorithms, scorecard jobs, future ML → separate Railway project, no buyer keys.

They share JSON only (`scorecard.json`, optional signal URLs). They do not share `.env`.

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

## Railway + GitHub Actions

1. Create a Railway project and empty service.
2. In GitHub repo settings → secrets:
   - `RAILWAY_TOKEN`
   - `RAILWAY_SERVICE_ID`
  (optional) `RAILWAY_PROJECT_ID`
3. Root directory / Dockerfile path: `desk/` (this folder).
4. Push to `main`. Workflow `.github/workflows/deploy-desk-railway.yml` builds and deploys.
5. Leave Kraken variables empty for paper.

Or in Railway UI: New → GitHub repo → root directory `desk` → deploy. Same Dockerfile.

## Moving off the droplet

Today `nexus.supersym.xyz` is still on DigitalOcean. Target state:

- DNS for `nexus.supersym.xyz` → Railway desk service
- Droplet retired once this service matches what you need
- Critical-Mass-Lab keeps research workers on its own Railway project

## Notes

- Bundled UI assets under `public/assets/` match the current Nexus operator shell.
- Paper loop is in-process (`desk/backend/paper_engine.py`) so one container is enough.
- Live arming stays refused until keys and flags are set on purpose.
- ML is later; do not block this template on it.
