# Milestone 9 Finalization — Stable Release (2026-11-01)

## 1. M7 compatibility issue: root cause

`test_m7_closed_loop.py::test_double_contradiction_rejects` failed after
the M8/M9 attribution upgrade. Mixed verdict — the test was half-right,
the linker was half-wrong:

**Genuine linker bug (fixed).** `linker._MATCH` has always treated
split-overlap evidence as bearing on leakage hypotheses
(`"split-hygiene": family match OR _is_leakage`), but the M9
`attribution.classify` graded the same pair `neutral`: its
`_broad_match` has no split-hygiene branch and its exact-match gate
(`primary == rule_family`) never fires because `_family_of` maps
"split overlap leakage …" to `leakage` while rules emit
`split-hygiene`. A clean-split measurement directly tests an overlap
claim, so `neutral` was wrong. Fix: `_MECHANISM_EQUIV =
({split-hygiene, leakage})` in `backend/causal/attribution.py` with
`same_mechanism()` — parity with the linker's own taxonomy, not a
test-specific hack. No other families merged.

**Obsolete test expectation (updated).** The old test paired
`forecast_diagnostics` (splits clean → split-hygiene contradicts)
with `data_quality_profile` (no nulls/dups → quality contradicts)
and expected both to reject a "split overlap leakage artifact"
hypothesis. The second link is scientifically invalid under M8/M9
semantics: a clean null/duplicate screen says nothing about split
overlap. It passed originally only because the generic English word
"artifact" in the hypothesis matched the quality word list —
precisely the topic-word over-attribution M8/M9 eliminated
(mentioning ≠ evidence). Clean nulls are now recorded visibly as
`relevant_to` but never move belief. The old `rejected` expectation
required two moving contradictions; only one genuinely exists.

## 2. Resolution

- `backend/causal/attribution.py`: mechanism-equivalence fix above.
- `tests/test_m7_closed_loop.py`:
  - `test_double_contradiction_rejects` rewritten: level-shift claim
    on the frozen `fixture_eval/investigator/stable_output.csv`
    (stationary target, 240 rows, chronological train/test) is
    contradicted by `temporal_changepoint_scan` (|shift| ≈ 0.23 < 1)
    AND `distribution_shift_profile` (|mean_shift| ≈ 0.11 negligible)
    — two tools, same mechanism, both genuinely contradicting.
    Asserts `rejected` + exactly 2 contradicting refs.
  - `test_genuine_split_contradiction_links` (new): clean splits
    move a split-overlap claim to `investigating` with exactly one
    contradicting ref — guards the attribution fix.
  - `test_topical_overlap_does_not_reject` (new): clean splits +
    clean nulls = `investigating` with 1 contradict + 1 visible
    `relevant_to` — pins the M8/M9 semantic against regression.
- New frozen fixture `stable_output.csv` + conflict-free generator
  `gen_stable_output.py` (wording scrubbed so the ground-truth
  separation audit stays clean — a first draft tripped it and was
  fixed before any suite ran green).

## 3. Regression results

136 passed, 0 failed (`test_m7_closed_loop`, `test_m7_challenge`,
`test_m8_linker/challenge/discovery/reporting/budget`,
`test_m9_attribution/invention/agenda/confounders/memory_profile/challenge`,
`test_m6_causal`, `test_research_lab`, `test_eval_independence`).

## 4. Eight-scenario M9 results (unchanged by the fix)

Every scenario runs 2–6 experiments with hypothesis transitions.
Means: invention 1.0, planning 1.0, attribution 1.0, discovery 0.938,
causal 0.75, confounder 0.625 (dev) / 0.9 causal on held-out.
Sub-1.0 means are honest grades (investigated-but-unconfirmed),
not defects; the scorer was deliberately not tuned.

## 5. Remaining limitations

- Cross-family evidence never moves belief (e.g. changepoint-drift
  support vs a persistent-error hypothesis grades `neutral`); only
  rules that explicitly encode the cross-family contradiction
  (residual_time_analysis) bridge families.
- Quality-family hypotheses have a single contradicting tool, so
  `rejected` via two distinct tools is unreachable for them.
- `_broad_match` still lacks drift/misspecification/input-dependence
  branches (topical relevance for those grades `neutral`, recorded
  for audit).

## 6. Release status

M9 FROZEN as the stable foundation for M10–M12. Changed semantics:
split-hygiene ↔ leakage are one mechanism for attribution.
Everything else — thresholds, indecision bands, non-moving
relationships, provenance requirements — preserved.

## 7. Post-freeze live finding (no frozen behavior changed)

The integrated live run showed model-worded hypotheses denying a
level change still collecting drift-supports. Fix: family-level
denial symmetry (`denies_family`, own negation set excluding
"artifact") — evidence for a denied mechanism contradicts.
Proven zero-impact: full suite 408 pass, M9 means and M10 grades
byte-identical to §4. Regression pinned in
`test_family_denial_flips_drift_support`.
