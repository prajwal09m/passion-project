# MODEL_AUTOPSY V2 vs V3 — COMPARISON (Stage 7B, computed values)

All values computed in-memory from persisted `eval_report.json` files with
the frozen v2 scorer and the new v3 scorer. **No archived scorecard was
modified.** v2 outputs reproduced every archived scorecard exactly (see
`test_v3_reproduces_every_archived_music_scorecard`).

| run | V2 verdict | V2 disc | V3 verdict | V3 disc | V3 evi | V3 ver | V3 conf | V3 overall |
|---|---|---|---|---|---|---|---|---|
| m16b-music-01 | inconclusive | 0.0 | honest_partial | 0.4 | 0.0 | 0.0 | 0.7 | 0.39 |
| m16b-music-02 | inconclusive | 0.0 | unresolved | 0.0 | 0.0 | 0.0 | 0.4 | 0.21 |
| m16b-music-03 | inconclusive | 0.0 | unresolved | 0.0 | 0.0 | 0.0 | 0.4 | 0.21 |
| m16b-music-04 | inconclusive | 0.0 | unresolved | 0.0 | 0.0 | 0.0 | 0.4 | 0.22 |
| m16b-music-05 | inconclusive | 0.0 | unresolved | 0.0 | 0.0 | 0.0 | 0.4 | 0.21 |
| m16c-music-01 | inconclusive | 0.0 | unresolved | 0.0 | 0.0 | 0.0 | 0.4 | 0.22 |
| m16c-music-02 | inconclusive | 0.0 | unresolved | 0.0 | 0.0 | 0.0 | 0.4 | 0.22 |
| m16c-music-03 | inconclusive | 0.0 | unresolved | 0.0 | 0.0 | 0.0 | 0.4 | 0.22 |
| m16c-music-04 | inconclusive | 0.0 | unresolved | 0.0 | 0.0 | 0.0 | 0.4 | 0.21 |
| m16c-music-05 | inconclusive | 0.0 | unresolved | 0.0 | 0.0 | 0.0 | 0.4 | 0.21 |
| m17-music-01 | inconclusive | 0.0 | honest_partial | 0.4 | 0.0 | 0.0 | 0.7 | 0.39 |
| m18-music-01 | inconclusive | 0.0 | unresolved | 0.0 | 0.0 | 0.0 | 0.4 | 0.13 |
| m19-music-01 | unsupported | 0.2 | confirmed | 1.0 | 0.0 | 0.0 | 1.0 | 0.61 |
| m21-music-01 | inconclusive | 0.0 | unresolved | 0.0 | 0.0 | 0.0 | 0.4 | 0.23 |
| m22-live-01 | inconclusive | 0.0 | honest_partial | 0.7 | 1.0 | 0.0 | 0.7 | 0.66 |

## Reading the table (what changed and why)

- **v2 discovery is 0.0 everywhere except m19** (confirmed-title-only gate).
  v3 credits investigating-level matches (m16b-01, m17-01: 0.4) and
  supported matches (m22: 0.7) — the forensic core complaint, resolved.
- **m19 flips unsupported→confirmed** (1.0/1.0): under the recalibrated,
  documented v3 band (0.15 + p<0.05), its confirmed cold-start finding with
  gap 0.1695/p=0.0005 IS justified confirmation. This is calibration
  working, not inflation — v2's 0.2 was the unreachable-ruler artifact.
- **v3 verification is 0.0 on every archived run**: no archived report
  records an executed probe (m19 predates the verify machinery; m22's
  refusal was correctly not counted). Honest, per spec.
- **v3 evidence is 0.0 on pre-fallback shapes** (m16–m21 except m22): those
  records embed no moving refs, so linkage cannot be reconstructed —
  reported with explanatory notes, not penalized silently. m22 (full
  fallback detail): 1.0.
- **No dimension was invented for history**: unavailable stays visible as
  low-with-notes where records are thin, never backfilled.

## M22 row (the required regression)

Correct cold-start hypothesis → discovery credit (0.7); supporting evidence
→ evidence credit (1.0); unexecuted probe → no verification credit (0.0);
withheld confirmation → confirmation stays unconfirmed (0.7 honest partial);
overall 0.66 `honest_partial` — accurately communicates "found with
evidence, unverified, honestly partial" instead of v2's 0.6 `inconclusive`
("failure missed entirely").
