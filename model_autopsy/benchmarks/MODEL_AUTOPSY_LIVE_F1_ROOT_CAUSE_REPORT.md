# LIVE DISCOVERY F1 = 0.0 — ROOT-CAUSE REPORT (READ-ONLY FORENSIC)

**Run:** `model_autopsy/benchmarks/live_runs/m22-live-01/` · **Project:** `eval_music`
**Method:** persisted artifacts + authoritative scorer only; no code/test/artifact
changes, no provider calls, no network, no spend. Pure-function scorer re-runs
were executed in-memory on copies; no artifact was modified (hashes untouched).
**Final classification: MIXED FAILURE** — primary: benchmark/scorer calibration
(unreachable evidence threshold); secondary: investigator never confirmed
(correctly, without verification). The model found the right mechanism; the
pipeline scored it 0.0.

---

## 1. Executive summary

The investigator generated a semantically correct, evidence-supported hypothesis
("Ranker underperforms on new-item slice due to cold-start feature sparsity…",
status `supported`, 5 refs) matching sealed truth ("cold-start collapse:
new-item slice P@K far below established items…"). Discovery still scored 0.0
through two stacked gates in `backend/eval/scorer.py`: (a) discovery reads only
`confirmed_findings` titles — empty here, because the honest resolution contract
withheld confirmation without verification; (b) the `eval_music` numbers gate
(`min_gap: 0.20` on the `gap` key) is **unreachable**: the deterministic fixture
produces gap 0.1695 in every recorded run (m16b/c, m17, m19, m22). Proof:
in-memory confirmation of the correct hypothesis still scores only 0.2
("unsupported … max slice gap=0.1695"); M19 hit exactly that ceiling. F1 = 0.0
is mathematically correct under the implementation and does NOT mean the model
found nothing — it means nothing was *confirmed*, and confirmation could never
have scored above 0.2 on this fixture.

## 2. Exact live-run reconstruction

Task (brief): "Are top results relevant for every catalog slice?" (sealed truth:
cold-start collapse, new-item P@K ≪ established under healthy pooled mean).
Turn 1: model proposed 3 hypotheses, ran ranking_slice_diagnostics,
classification_metrics, regression_metrics; linker linked. Summary invalid →
repair returned empty → rejected → fallback. Turn 2: ran slice_gap_significance
(gap 0.1695, p=0.0005 — gap is REAL) + repeat diagnostics; links recorded.
Turn 3: model silent → `total_inaction=TRUE`, empty-output fallback; prior gain
existed → evidence floor met → `completed`. Hypotheses final: uniformity
`rejected` (3 contradicts), cold-start `supported` (4 supports + significance),
base-rate-mix `investigating`. Resolution: `partially-resolved` — correct: one
supported-but-unverified + one open hypothesis, no verification probe run
(`independent_verification.performed: false`), so confirmation was rightly
withheld. Scorecard (`scorecard.json`): verdict `inconclusive`, "failure missed
entirely", discovery 0.0 / evidence 1.0 / reasoning 0.6 / calibration 1.0 /
efficiency 0.2 / reproducibility 1.0, overall 0.6. Spend $0.072925, 5 calls.

## 3. F1 scoring implementation trace (`backend/eval/scorer.py`)

`score(pid, report, truth)`: text = titles of `confirmed_findings` ONLY
(`_confirmed_text`; supported/rejected/investigating hypotheses invisible).
`named` = any family word in that text (`slice` family words include
"slice"/"rank"/"cold"). `supported` = `_evidence_supports`: for eval_music,
`any(n.get("gap",0) >= 0.20)` over ALL experiments' `numbers` (no tool filter).
Live numbers' `gap` values: `[0,0,0,0,0,0,0,0.1695]` → False. Decision table:
named+unsupported→0.2; unnamed+unsupported→0.0 ("failure missed entirely").
Live: confirmed empty → text "" → named False; supported False → 0.0. Answers
to §3: (1) a confirmed-finding title containing a family word + numbers ≥
threshold; (2) keyword-substring on confirmed titles + numeric band, NOT
semantic/hypothesis matching; (3) IDs irrelevant to discovery (titles only);
(4–5) supported-but-unconfirmed hypotheses are unscored by construction —
wording never even reaches the matcher; (6) duplicates N/A (titles joined);
(7) missing metadata doesn't exclude — but only confirmed titles count at all;
(8) correct pair (`eval_music` report vs sealed truth); (9) yes — empty
confirmed ⇒ named False ⇒ ≤0.0/0.4 paths only; (10) scored post-refinement on
the final eval report (fallback carries recorded state, so refinement IS
included — the supported hypothesis was present, just unconfirmed).

## 4. Ground-truth vs predicted comparison

Truth: "cold-start collapse: new-item slice P@K far below established items
under a healthy pooled mean" (`ground_truth_eval.json:50`). Model (supported):
"Ranker underperforms on new-item slice due to cold-start feature sparsity,
yielding lower top-K relevance for new catalog content." — same mechanism
(cold-start), same locus (new-item slice), same observable (top-K relevance
gap), corroborated by gap 0.1695/p=0.0005 + bias −0.177 + mae_by_group
new 0.327 > est 0.250. Title-word check passes ("slice","rank","cold"). The
0.0 is therefore NOT a semantic miss — it is a pipeline outcome (unconfirmed +
sub-threshold numbers).

## 5. Independent score reconstruction

Re-ran `SC.score('eval_music', persisted_eval_report, sealed_truth)` in-memory:
verdict `inconclusive`, "failure missed entirely", discovery **0.0 — reproduced
exactly**. TP/FP/FN framing: the scorer has no set-matching stage; the
effective outcome is TP=0 (no confirmed mechanism), FP=0, FN=1 → 0.0.
Counterfactual (in-memory only, NOT a new official score): inserting the
correct cold-start title into `confirmed_findings` → `unsupported`,
"mechanism named without supporting numbers (max slice gap=0.1695)",
discovery 0.2. M19 (`m19-music-01`, confirmed cold-start title) scored exactly
0.2 — the fixture's empirical ceiling. Nothing in the artifacts is missing;
reproduction is complete.

## 6. Evidence-linking analysis: discovery vs evidence discrepancy

No contradiction: the dimensions measure different things. `evidence = 1.0`
rewards *not fabricating* (inconclusive without confirmation); `discovery`
rewards *naming + numbering* a confirmed mechanism. Evidence supported a
hypothesis (cold-start, `supported`) that never entered the scored set because
discovery reads confirmed titles only. Linking operated correctly (right tools,
right relations, independent-repeat honesty on the third hypothesis). The
`partially-resolved` status was appropriate and the honest outcome — a
`confirmed` claim without verification would have been exactly the unsupported
confirmation the resolution contract exists to prevent.

## 7. M21/M22 context

Unconnected to the F1: M21's zero-action failure did not recur (8 actions ran);
the M22 nudge never fired (hypotheses existed from turn 1) — recovery
effectiveness stays live-unverified, a SEPARATE limitation. Evidence-floor
semantics worked as designed (completed on prior gain, not on resolution).
The scorer predates M22 and is untouched by it; M22 changed visibility, not
scoring. `useful_evidence=true` and discovery 0.0 coexisting is the P0
distinction functioning, not a contradiction.

## 8. Root-cause classification: MIXED FAILURE

Primary (D) benchmark calibration + (C) scorer design; secondary (A, bounded)
investigator non-confirmation. No (E): linking/adapter faithfully transmitted
state (spot-checked digests match actions).

## 9. Ranked findings

- **F1 [Critical · Benchmark] Unreachable `min_gap: 0.20`.** `scorer.py:37,99`.
  Artifact: every music run's `actions.json` (0.1695, incl. m16b/c, m17, m19,
  m22). Fixture (`generate.py:94`) plants new-item relevance 0.10 vs est 0.50 —
  a real, significant gap (p=0.0005) the threshold declares insufficient.
  Impact: eval_music discovery ceiling is 0.2, and 0.0 whenever the honest
  contract withholds confirmation. Confidence: proven.
- **F2 [High · Scorer] Discovery reads confirmed titles only.** `scorer.py:104`
  via `_confirmed_text`. Supported-but-unverified work is invisible; wording
  match is substring, not semantic. Impact: honest non-confirmation ⇒ 0.0 by
  construction. Confidence: proven. (Design intent — confirmation-gated
  scoring — but it conflates "didn't confirm" with "didn't discover".)
- **F3 [Medium · Investigator] No verification probe designed/run.**
  `eval_report.verification: []`, `independent_verification.performed: false`;
  skeptic-lite proposed probes but none executed. The supported cold-start
  hypothesis was confirmable in principle (permutation evidence existed).
  Impact: confirmation — and any score above 0.0 — was unreachable this run
  regardless of F1. Confidence: strongly supported.
- **F4 [Low · Scorer] Key-name fragility.** `ranking_slice_diagnostics` emits
  `max_slice_gap` (scorer ignores; reads `gap`); only `slice_gap_significance`
  feeds the gate. Impact: none this run (both 0.1695), latent trap. Plausible,
  unverified beyond code reading.

Direct answers: (1) Yes, 0.0 is valid under the implementation. (2) No — it
measures confirmation+threshold, not diagnostic accuracy; the mechanism WAS
discovered at hypothesis level. (3) Yes — the supported cold-start hypothesis.
(4) Yes — linking correct, relations and independence accounting sound.
(5) Yes — `partially-resolved` with no verification is exactly right.
(6) Combination: benchmark threshold first, scorer design second, investigator
confirmation gap third. (7) Fix first: recalibrate or justify `min_gap`
(F1) — it caps the fixture at 0.2/0.0 no matter what any investigator does.

## 10. Recommendations (no implementation)

- **P0 (score correctness):** Recalibrate `eval_music` `min_gap` to the
  fixture's deterministic output (0.1695, significant at p=0.0005) or document
  why 0.20 is required; verify by re-running the scorer in-memory over all
  archived music eval_reports (expect ≤ ceiling change only on music runs).
  Regression risk: changes one fixture's ceiling — re-freeze threshold with
  rationale; do NOT lower other mechanisms' bars. Evidence: F1 + §5.
- **P1 (diagnostic quality):** Make verification-probe design a first-class
  loop obligation (skeptic proposes → investigator executes or records why
  not); verify via `verification: []` becoming non-empty in the next offline
  eval. Risk: extra tool calls — bound under existing budgets.
- **P2 (evaluation):** (a) score supported-but-unverified mechanisms
  separately from confirmed ones (discovery vs confirmation sub-metrics) so
  honesty isn't scored identically to blindness; (b) normalize `max_slice_gap`
  → `gap` alias in scorer or tool; (c) report per-fixture ceilings in
  benchmark docs. Verify with frozen-truth regression suite; risk is metric
  churn — version the rubric (v3) rather than editing v2 in place.
- **P3 (optional):** semantic-similarity audit column (advisory only, never
  replacing deterministic score); UI chip for discovery-vs-evidence split.

## 11. Limitations / unverified

Whether 0.20 was a deliberate "must exceed noise by margin" choice or an
arbitrary round number (no rationale comment in scorer); whether the fixture
seed/gap was tuned after the threshold was set; single live run (n=1);
archived runs' manifests not re-hashed here (hashes in m22 manifest verified
present, not recomputed — read-only stance toward integrity).

## 12. Final assessment

**MIXED FAILURE** (benchmark-ground-truth calibration primary, scorer design
contributory, investigator confirmation-gap secondary). The truth the task
asked for: **Model Autopsy discovered the correct explanation and our
evaluation system failed to recognize what it discovered** — compounded by the
investigator stopping one step short of confirmation. The 0.0 is real
arithmetic on an unreachable ruler, not evidence of an empty investigation.
