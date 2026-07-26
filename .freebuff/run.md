# DZAI — Demand Zone AI Terminal (preview run doc)

This worktree is a single workspace that contains both the Next.js webapp
(`demand-zone-webapp/`) and the Python ML pipeline (`Python/`, `outputs/`,
`Other/`, `data (v1)/`). The Preview tab renders the webapp. The Python
artifacts are only referenced as data sources; the webapp runs independently.

The webapp is self-contained: no `.env.local`, no external services, no
database, no API keys. All numbers in the UI are deterministic fixtures
sourced from the same Python pipeline outputs (and clearly labelled as such
in `src/data/signals.ts`, `src/data/metrics.ts`, `src/data/insight.ts`).

## 1. Reproduce the artifacts a fresh checkout needs

```
# From the worktree root (this directory):
cd demand-zone-webapp
npm install                          # installs Next 14, React 18,
                                    # lightweight-charts, motion,
                                    # animejs, lucide-react, clsx
```

No `.env.local` to copy — the app reads no secrets. No database to seed.
No CSV ingestion step — the candle data is generated deterministically in
`src/data/signals.ts` (`makeOHLC`, Mulberry32-seeded) and the ML numbers
are hard-coded from the real pipeline outputs in `src/data/metrics.ts`,
`src/data/features.ts`, and `src/data/insight.ts`.

## 2. Run the dev server

```
cd demand-zone-webapp
npx next dev -p 3000
```

Then open `http://localhost:3000/`.

- **Default port:** `3000` (Next.js convention).
- **Pick a free port** (e.g. `3007`, `3008`) if `3000` is already taken and
  pass it via `-p <port>`. The webapp binds to the chosen port with no
  config-file changes required.
- The server is the only long-running process for the preview.

### Routes

| Path          | Purpose                                                |
| ------------- | ------------------------------------------------------ |
| `/`           | Product showcase (KPIs + chart + signals + telemetry). |
| `/insight`    | Premium AI analysis (glassmorphism + confidence gauge). |
| `/analysis`   | Bloomberg-style chart-centric dashboard.               |
| `/performance`| ML research terminal (model compare + features).      |
| `/backtest`   | Equity curve + trade ledger + anime.js entrance sweep. |

### Keyboard shortcuts (registered in `AppShell`)

`⌘/Ctrl+1` Home · `⌘/Ctrl+2` Insight · `⌘/Ctrl+3` Analysis ·
`⌘/Ctrl+4` Model · `⌘/Ctrl+5` Backtest.

## 3. Verification (what the preview should show)

- All five routes return HTTP 200.
- The `/insight` page renders the full glassmorphism layout: header
  (ticker search, name, market status pill, timeframes, refresh), chart
  with demand/supply zones + EMAs + VWAP + entry/SL/TP lines, AI Signal
  card (94% confidence gauge, BUY pill, 6 probability rows, OHLC grid),
  Trade Setup card (12 fields + expected/risk summary), AI Reasoning
  with 8 checkmark rows, Feature Importance (10 gradient bars), 11
  Technical Indicator cards, 6 Risk gauges, 6 News & Sentiment articles,
  collapsible Model Information.
- The floating particles in the background are deterministic — same
  positions on every load, no hydration warning.
- The live clock in the top status bar renders `—` on the server and the
  first client render, then ticks every second post-mount.

## 4. Re-runs and cleanups

```
# Stop the dev server (any of):
pkill -f "next dev"                  # bash
taskkill //F //IM node.exe           # Windows (kills all node)

# Clear the build cache (only if the dev server gets confused):
cd demand-zone-webapp
rm -rf .next
```

## 5. Server log file (this worktree)

The dev server logs go to:

```
C:\Prajwal MIT\Passion\.freebuff\preview-thms0xrcdsd33u.log
```

Tail with:

```
tail -f "C:/Prajwal MIT/Passion/.freebuff/preview-thms0xrcdsd33u.log"
```
