# FINAL token-efficiency analysis (2026-10-31)

Research question: does Delta reduce actual provider-billed input tokens while maintaining equivalent-or-better quality?

## Meta campaign measurements (provider-reported usage, 24 billed requests)
| Pair | Cond | Input | Cached | Uncached | Output | Requests | Incomplete | Summary |
|---|---|---|---|---|---|---|---|---|
| p1 | full | 17,591 | 9,924 | 7,667 | 6,232 | 6 | 2 | INVALID |
| p1 | delta | 16,993 | 12,966 | 4,027 | 7,188 | 6 | 2 | valid |
| p2 | full | 17,964 | 13,478 | 4,486 | 6,835 | 6 | 3 | INVALID |
| p2 | delta | 24,425 | 20,006 | 4,419 | 7,122 | 6 | 1 | valid |

Campaign totals: input 76,973 (cached 56,374 / uncached 20,599), output 27,377, $0.15056 est.

## Distinctions honored
- Prompt length ≠ billed input: compared provider-reported tokens only.
- Cached vs uncached split: uncached (newly processed) is the fair efficiency metric; cached reflects session-order warming (last run warmest: 20,006), not condition.
- Groq ≠ Meta billing: Groq deltas (−1.7%, −4.4%) are infrastructure signals only.
- Premature stopping excluded as efficiency: fulls had MORE incomplete stops (5 vs 3); no run hit caps; request counts equal.
- Formatting ≠ quality: scored separately via frozen rubric (delta 10+12 vs full unscorable+5).

## Decision
- Uncached input: Delta lower in **both pairs (−47.5%, −1.5%)**.
- Quality: Delta valid 2/2, full valid 0/2; scored Delta ≥ Full in both pairs.
- **Delta retained.** No significance claimed (n=2). Total-input comparison (+36% p2) is a cache-warming artifact, reported as a limitation, not a saving.

## Bottleneck
Provider-side output truncation (8/24 incomplete) and reasoning-budget exhaustion dominate: larger full contexts produce longer trajectories that hit the frozen 2000-output / 1200-repair caps. Efficiency work should target output/reasoning budgets and truncation recovery, not just input shortening.
