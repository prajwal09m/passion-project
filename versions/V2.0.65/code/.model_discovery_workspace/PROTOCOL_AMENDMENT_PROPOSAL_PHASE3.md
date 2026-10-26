# Protocol Amendment Proposal (Phase 3) — NOT ACTIVATED

Status: proposal only. Nothing here is active in the production generator.
Production values were read from source and are unchanged:
- `bias_governor.py`: `min_falsification_share = 0.35`, `max_replication_share = 0.50`,
  `replication_cap_min_portfolio` defaults to `1` when absent.
- `generator.py`: the falsification quota pressure applies when the falsification share is below the floor.

Approvals required before any activation: **owner approval** and an
**independent statistical review**. Neither has been obtained. An AI review or
an owner substitute is not an independent statistical review.

## 1. Problem (from the five-mode benchmark)

- Legacy: 18 emitted proposals, all redundant against measured history, stopped at cycle 7.
- Dedup only: stopped at cycle 1 with 0 proposals. The deadlock is real.
- Dedup + quota: 2 emitted, both replication-seed keys (not new models).
- Phase 3 expanded pool (simulated): all 12 "new" keys are replication-seed comparisons. All 8
  default-seed model atoms (4 arms × 2 estimators) are already measured.

Conclusion: the binding constraint is the **closed candidate universe**, not only the quota. Quota
amendments unlock replication work. They do not create new model hypotheses.

## 2. Proposed amendments

### A. Falsification floor — conditional relaxation (optional, owner decision)
- Change: the 0.35 floor applies only when at least one admissible falsification candidate exists.
  If none exists, the floor is waived for that cycle and the waiver is logged as
  `quota_waived_no_admissible_falsifier`.
- Problem solved: prevents a stall when no falsifier can be generated.
- Bias risk: over time, the system could drift toward confirmation if waivers recur. Mitigation:
  cap waivers per rolling window and surface waiver counts in the report.
- Safe failure: if waivers exceed the cap, the generator emits nothing and stops, which is the current behavior.
- Acceptance tests: waiver fires only with zero admissible falsifiers; waivers counted; cap enforced.

### B. Replication cap — minimum portfolio (optional, owner decision)
- Change: the 0.50 replication cap applies only once the portfolio contains at least N non-replication
  proposals (N is the owner's choice, for example 4).
- Problem solved: at cold start, a single replication can block the only available proposal.
- Bias risk: replication-heavy early portfolios. Mitigation: replications are tagged `replication`
  and never counted as novel evidence.
- Acceptance tests: cap is inactive below N and active above N; replications never increase novelty counts.

### C. Eligible classes
- Replications and seed changes are not eligible as novel-hypothesis proposals. They may still be used
  as stability controls. Keep the current classes unchanged; this is a clarification, not a relaxation.

### D. Feature and estimator universe (required for real expansion)
- The current four feature arms and two estimators make the universe closed. Expansion requires a
  new, separately reviewed feature definition set and an estimator allowlist change.
- Each feature must state its prediction-time availability, its leakage control, and the result
  that would contradict its hypothesis. None of these has been approved.
- Status: **not implemented in this phase**. The expanded pool currently contains no new feature or
  estimator. Predictive expansion remains blocked on this amendment.

### E. Evidence key
- Keys are compiled-configuration identities. Reversed comparisons (A vs B and B vs A) should map to
  one key with a reversed sign where mathematically applicable. This is a clarification and must be
  reviewed before adoption, because it changes what counts as "already measured."

## 3. Scientific justification and bias
- Relaxing floors can reduce falsification discipline. Each relaxation must be bounded and logged.
- Waivers and caps must be reported in every campaign report, not hidden in the generator.

## 4. Acceptance tests (for any future activation)
- Quota waivers fire only under the stated condition and are counted.
- No amendment changes frozen campaign configurations, promotion criteria, or launch gates.
- Campaign 4 records and the sealed holdout are untouched.

## 5. Owner / statistical sign-off
- Owner: [pending]
- Independent statistical reviewer: [pending]
