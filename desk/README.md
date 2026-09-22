# Nexus Desk (trader template)

One Railway service. One variables panel. Paper trading needs **no exchange keys**.

Marketplace / appetite-test overview: [`TEMPLATE.md`](TEMPLATE.md)

## What deployers fill in

| When | Variables |
|---|---|
| Paper (default) | Nothing. Public Kraken market data only. |
| Lock control writes (optional) | `NEXUS_CONTROL_PASSWORD` |
| Live later (optional) | `KRAKEN_API_KEY`, `KRAKEN_API_SECRET`, then flip `NEXUS_PAPER_ONLY=0` and `NEXUS_DASHBOARD_ALLOW_LIVE_ARM=1` deliberately |
| Research card (optional) | `NEXUS_SCORECARD_URL` pointing at a scorecard JSON |

No DigitalOcean panel. No second host for paper. No Replit URLs. No OpenAI keys for this template.

## Publish as a Railway template (appetite test)

Draft already exists: **nexus-grid-desk** (`zK_1Id`).

- Deploy: https://railway.com/deploy/zK_1Id
- Service icon on `nexus-grid-webapp`: Python Devicon
- Root directory: `desk`
- Healthcheck: `/api/health`
- No required variables baked in (paper = zero secrets)

To finish marketplace listing: open **Templates → nexus-grid-desk**, paste the card image URL from [`TEMPLATE.md`](TEMPLATE.md) if the image field is empty, confirm the overview markdown, then **Publish**.

Keep copy honest: paper desk / operator UI, not “guaranteed alpha.”

## Two repos

1. **This desk** (`desk/`): UI + paper observer + control API → Railway template.
2. **critical-mass-lab**: algorithms, scorecard jobs, future ML → separate Railway project, no buyer keys.

They share JSON only. They do not share `.env`.

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
- Live arming stays refused until keys and flags are set on purpose.
- ML is later; do not block this template on it.
- Regime scorecard on the page is a research replay, not a live track record.
