# MODEL_AUTOPSY EVALUATION V3 — INDEPENDENT AUDIT (Stage 8, read-only)

Review posture: inspect as though written by someone else. Verified against
source, tests, and artifacts — not against the implementation report's claims.

## 1. Checks (16 required)

1. **V2 unchanged: PASS.** `scorer.py:37` still `min_gap: 0.20`; weights
   identical; `test_v2_weights_and_bands_untouched` + exact reproduction of
   all 4 archived music scorecards (m16b/m17/m19/m22) in the suite.
2. **V3 independently selectable/identifiable: PASS.** Separate module
   `scorer_v3.py`; every output carries `rubric_version: "v3"`;
   `score_v3(pid, report, truth)` importable without touching v2 paths.
3. **Historical reports preserved: PASS.** No writes to `live_runs/*` this
   project (only reads + in-memory scoring); m22 scorecard still
   `inconclusive/0.0/0.6` with no rubric tag (v2-legacy). v2-vs-v3 table
   computed, not stored over archives.
4. **Ground truth not silently changed: PASS.** `ground_truth_eval.json`
   content matches forensic record (cold-start mechanism text intact);
   fixture generator and CSV untouched; no v3 fixture created (correct —
   fixture was sound).
5. **Discovery includes supported-but-unverified: PASS.** M22 v3 discovery
   0.7 via supported hypothesis (overlap 0.67); dedupe prefers ref-rich
   records (bug found by tests, fixed at cause, re-verified).
6. **Confirmation still requires the resolution contract: PASS.**
   Confirmation 1.0 only with confirmed findings + passing numbers gate +
   no contradicts; M22 stays 0.7 (unconfirmed); unsupported confirmation
   tested to 0.0.
7. **Evidence scoring provenance-based: PASS.** Moving refs from `ran`
   actions only (same rule as `has_useful_evidence`); linkage fraction
   measured, repeats noted-not-counted; no tool-call counting.
8. **Verification requires execution: PASS.** Planned-only caps at 0.2;
   executed-with-result required for 1.0; all archived runs score 0.0
   honestly; independence enforced by existing `maybe_verify` (duplicate
   probe refused, spend released — tested).
9. **Missing metrics handled honestly: PASS.** Absent gap ≠ 0 (gate
   requires presence); missing usage → `None` + "cost unknown" note;
   missing truth → `overall: None` + `insufficient_data`; unavailable dims
   listed, never backfilled.
10. **No alias double-count: PASS.** Single canonical read path
    (`canonical_gap`); conflict prefers explicit `gap` + flag; 8
    normalization tests incl. invalid/None/mutation cases.
11. **Threshold rationale documented: PASS.** `rubric_v3.py` gives the
    4-point method (test-suite floor 0.15, margin, noise distance, null
    exemption); 0.20 origin investigated (`m4_scoring_methodology.md` band
    table, no rationale — stated as unverified, not assumed).
12. **Dashboard matches backend: PASS.** `Eval.tsx` renders stored
    scorecard fields directly (no transformation): dimensions, notes,
    unavailable, rubric label, verification trail, discovery≠confirmation
    explainer. tsc 0, build 0.
13. **Historical compatibility: PASS.** v2 scorecards render via unchanged
    generic renderer (new fields optional); v2 dims never shown as v3.
14. **No external provider calls: PASS.** All new tests offline (fixture
    CSV + temp DB); full suite ran with no credentials; no live driver
    invocation this project.
15. **No spending: PASS.** No provider usage entries created; governor
    untouched; spend-related tests use local budget accounting only.
16. **Demand Zone AI untouched: PASS.** Zero diffs on all Demand Zone
    paths (verified via git status).

## 2. Findings

- **No Critical or High issues.** The implementation matches the design;
  tests pin the guarantees; frozen artifacts verified intact.
- **Medium (accepted, documented): v3 not yet wired into the live
  pipeline.** `driver.py:279` / `resume.py:281` still call v2 `SC.score`.
  Correct for this offline project (no live runs authorized → zero
  behavioral effect), but the v2→v3 cutover for future live runs is an
  explicit undecided step. Recommendation: cut over only with a versioned
  pipeline flag recording which rubric scored each future run.
- **Medium (accepted, documented): thin-record archives score low on v3
  evidence (0.0 with notes).** Faithful to "measure the record, not the
  run" — but cross-era comparisons need the COMPARISON report's caveats.
- **Low:** efficiency inherits v2's count-based decay (M22: 0.2 for 8
  experiments); cost-awareness only surfaces in notes until usage blocks
  are standardized in reports.
- **Low:** `_normalization` flags piggyback inside `numbers` dicts;
  v2 scorer ignores unknown keys (verified by exact-reproduction tests),
  but a future strict-schema consumer should allowlist.

## 3. Verdict

**PASS with the two documented Mediums above (both accepted limitations,
neither integrity violations).** All 10 success criteria from §13 are met:
v2 reproducible; v3 separates the four achievements; threshold defensible;
M22 credited without fabricated verification; gap alias resolved; bounded
verification with explicit non-runs; dashboard accurate; history intact;
694/694 tests + tsc + build + scans green; audit finds no critical issues.
