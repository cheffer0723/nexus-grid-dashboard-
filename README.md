# Nexus Observability

A static dashboard template for traders who run a paper engine and want one place to see two things:

1. Whether a handful of regime rules actually held up on the same coins and dates.
2. What their own engine is doing right now: bias, paper trades, and where a rules signal and a model signal disagree.

Open `index.html` in a browser, or host the folder on any static site. Demo mode loads sample engine data and the checked-in scorecard. No account and no backend are required to look at it.

## Regime scorecard

The scorecard compares four fixed rules from the archived research engines. It does not search for a better setting on the coins it scores.

| Rule | What it does |
|---|---|
| Cerberus | Labels each day bull, bear, or sideways from the 20-day return, then takes the walk-forward bull-minus-bear odds long or short the next day. |
| Orthrus | Long the next day while price is above its 200-day average. |
| Hydra | Long the next day while the trailing 182-day return is positive. |
| Sisyphus | Long the next day after a close below the lower 20-day Bollinger band. |

The coin list, dates, and fee live in `scorecard-universe.json`. The current window is 1 Jan 2023 through 20 Sep 2026. The fee is 0.40% each time a position changes. Buy and hold on the same days has no fee. A hit is an in-market day where price moved the same way as the position.

Rebuild after you edit the universe file:

```bash
python3 scripts/build_regime_scorecard.py
```

The script uses Python 3.10 or newer, writes `scorecard.json`, and does not install packages. Check the math without downloading prices:

```bash
python3 scripts/test_regime_scorecard.py
```

Read the gap column as percentage points versus buy and hold. A rule can have a hit rate near 60% and still make less than simply holding the coin.

## Connect your engine

In the Backend API card, choose a mode and paste your API origin. The value stays in this browser.

| Mode | What it calls |
|---|---|
| Demo sample | `state.json` only |
| Your API, read-only | `GET {origin}/state` |
| Your API, with control | `GET {origin}/api/remote/state` and `POST {origin}/api/remote/commands` |
| This computer, control on | `GET http://127.0.0.1:8080/api/nexus/dashboard` and the local process routes |

Read-only state can be the packet shape in `state.json`, or a wrapper with `data` holding that packet. Control mode sends `{ "service", "action", "requested_by": "dashboard" }` and will attach header `x-nexus-remote-token` when you save a control token.

If the API call fails, the page keeps the sample packet and says so.

## Branding

`template.config.json` sets the title and subtitle. Demo mode is the default for a new browser.

## Local model helper

`scripts/temp-local-deep-learning-model.sh` starts a temporary Ollama container on `127.0.0.1` for short-lived experiments. It is separate from the scorecard.

```bash
scripts/temp-local-deep-learning-model.sh
```

Stop it with Ctrl+C. The container and temporary model cache are removed unless you pass `--keep-cache` or `--detach`.
