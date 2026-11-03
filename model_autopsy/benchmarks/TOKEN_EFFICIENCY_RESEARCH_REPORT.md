# Token-Efficient Autonomous Research (Milestone 3, Part 10)

Extension of the Full/Delta architecture: understanding summaries,
hypothesis-state summaries, experiment-result summaries, dedup of
repeated evidence, relevance-ranked retrieval, compact findings, and
on-demand access to full outputs by id (`rcontexts.py`).

## What was measured (offline traces, 2026-11-01)

Naive baseline = resending full understanding docs + full experiment
result payloads every reasoning round. Reference-summary alternative =
understanding brief + hypothesis states + per-experiment one-line
summaries with evidence ids.

- Naive resend-all: 26,680 chars over 13 experiments (9 scenarios).
- Reference summaries: 6,727 chars.
- Reduction: 74.8% in characters (proxy).

Per-scenario summaries run 640-910 chars; per-experiment marginal
cost is one summary line (~160 chars) regardless of artifact size.

## What is NOT claimed

Character size is a proxy, not billed tokens. No universal percentage
is claimed: the 74.8% is a 9-scenario offline characterization, and
live savings must be measured from provider usage (`usage.input/
output/cached_tokens`) when a billed run occurs. `measure()` records
`provider_billed_tokens: None` on offline traces and states the
optimization target explicitly: minimize tokens while holding
investigation quality and evidence coverage.

## Safeguards against information loss

Summaries never replace evidence: full outputs stay in durable records
(`research_runs/*/result.json`, action rows) addressable by id;
verification re-reads recorded numbers, not summaries; `dedup()` keys
on (tool, summary-prefix) so distinct results are never merged.
No paid API experiments were run in this milestone.
