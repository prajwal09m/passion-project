# Milestone 11 Architecture

```
M9/M10 autonomous baseline (shared evidence record)
        |
lead.assign -> {data_scientist.brief, model_analyst.brief}
        |
designer.propose -> ledger.reserve -> engine.run -> linker.link
        |
skeptic.challenge -> resolve-by-experiment | preserve-unresolved
        |
judge.verdict (hypotheses + evidence only)
```

One shared `Ledger` (thread-safe, atomic reserve, hard cap) funds
every agent; parallel agents cannot overspend (tested with 4
threads × 5 reserves against cap 10: used exactly 10). Paid work
additionally needs a human authorization token (M12) — the ledger
alone never authorizes spend. All outputs durable via events.
