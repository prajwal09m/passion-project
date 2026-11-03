# Hypothesis Discovery and Verification (Milestone 3, Parts 3 + 6)

## Card schema (every hypothesis)

`id, title, mechanism, evidence_motivating[], expected_observables[],
diagnostics[], support_criteria, refute_criteria, priority
(high/medium/low), status, history[]`. Validation rejects cards missing
title/mechanism/support/refute criteria. Storage: investigation
config `research.hypotheses[]` (deep-copied on write; no DB migration).

## Discovery (evidence-motivated, not a checklist)

`triage_hypotheses()` inspects the understanding doc (columns, task,
temporal hints, availability) and proposes only applicable cards: proxy
leak + subgroup concealment (classification), segment bias
(regression), stale-split drift (forecasting), instability
(clustering), slice collapse (ranking), plus a mandatory null
hypothesis ("no material issue") in every run. Each card states what
would support AND refute it before any experiment runs.

## Lifecycle

Statuses: proposed / investigating / supported / rejected /
inconclusive / blocked (missing info). Transitions validated
(`TRANSITIONS`); `supported`/`rejected` REQUIRE evidence references —
restatement alone can never confirm. `blocked` records what is missing
and which investigations are impossible with current evidence.

## Independent verification (`verification.py`)

Separate code path from the runner. Checklist per claim: sample size
(n>=30), methodology stated, evidence linked, no diagnostic
contamination, numbers reproducible, disproof criterion present. No
evidence -> `rejected`; any failed check -> `downgraded`; disagreements
preserved verbatim (`disagreement` field), never auto-resolved.

## Measured behavior (challenge suite, 9 scenarios)

8 supported findings upheld by review (leak x2, segment bias,
split/drift, slice gap, scaling mismatch, leak+subgroup pair); 0
overturned; clean/limited scenarios correctly produced zero
confirmations (null conclusion). Disagreement preservation covered in
`test_verification_preserves_disagreement`.

## Limitations

Deterministic rules only; LLM-proposed novel hypotheses and
human assessment of hypothesis quality are not yet validated (require
live inference / human review respectively).
