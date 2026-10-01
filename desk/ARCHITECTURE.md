# Nexus Desk boundaries

The published template points to `cheffer0723/nexus-grid-dashboard-`, branch `main`, directory `desk/`. The active `nexus.supersym.xyz` deployment runs a commit from `main`, although its Railway deployment metadata names `cursor/nexus-desk-template-ee93`; the service's auto-deploy branch needs reconciliation before promotion. The older `cheffer0723/Nexus-grid-webapp` and `NexusRuntime` are different codebases. The Desk's in-process paper engine fetches public Kraken OHLC directly. It does not consume the `critical-mass-research` Postgres database or control the stopped `nexus-market-data-collector`.

## Data paths

- **Paper observations:** Kraken OHLC → EMA/RSI signal → long-only simulated position → Desk read APIs. The simulation checks prices once per cycle and excludes fees, spread, and slippage.
- **Paper journal:** Set `NEXUS_STATE_DB` to a SQLite file on a mounted persistent volume. The journal records each successful cycle with signal, execution summary, and effective paper settings, plus each simulated entry and exit. `GET /api/paper/events` is the read interface. Without a persistent volume, the Desk starts fresh on deployment.
- **Historical research:** `critical-mass-lab` produces a scorecard JSON. The Desk serves its bundled snapshot unless the operator sets `NEXUS_SCORECARD_URL`. The JSON should include `generated_at_utc`, `eval_start`, `eval_end`, and an `engines` array with `name`, `hit_rate_active`, and `excess_return` for the current card. The scorecard does not alter the paper signal.
- **Jev comparison:** A browser operator can request a separate paper-only model comparison. The route requires `NEXUS_CONTROL_PASSWORD`, `NEXUS_JEV_CALLS_ENABLED=1`, a provider key, and durable SQLite storage for its UTC-day call budget. The comparison does not alter paper positions or enable orders.
- **Other local research:** HADES, ONYX, Solana, historical BTC, and the older Nexus runtime have no automatic feed into this Desk. Their artifacts need provenance and a separately designed evaluation contract before integration.

## Operations

The controls and settings writes are disabled when `NEXUS_CONTROL_PASSWORD` is unset. Reads remain public. `GET /api/health` checks the paper thread, last successful cycle age, and latest failure; an operator pause is reported as paused. The Desk has no live order execution implementation, even if legacy live variables are set.

The current service is configured as one Railway replica. SQLite on a mounted volume assumes a single writer; do not scale this design to multiple replicas without replacing its storage and lease model. Existing in-memory paper history cannot be reconstructed from a fresh volume. Preserve a read-only snapshot of the old container before the first deployment that mounts persistent storage.
