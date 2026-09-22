# Nexus Grid / Desk

Two products, two homes:

| Repo / folder | Role | Deploy |
|---|---|---|
| **`desk/` in this repo** | Trader operator dashboard + paper loop (Railway template / appetite test) | Railway |
| **`critical-mass-lab`** (separate private repo) | Research, algorithms, scorecards, later ML | Separate Railway project |

Buyers only touch the desk. Paper mode needs **no API keys**. Live needs one Kraken key pair in the same Railway variables panel.

- Desk runbook: [`desk/README.md`](desk/README.md)
- Marketplace framing: [`desk/TEMPLATE.md`](desk/TEMPLATE.md)

The older static GitHub Pages scorecard UI at the repo root remains available for demos; the shippable template is **`desk/`**.
