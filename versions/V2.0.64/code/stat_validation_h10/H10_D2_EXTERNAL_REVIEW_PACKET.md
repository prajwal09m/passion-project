# H-10 D2 — EXTERNAL STATISTICAL REVIEW PACKET

**STATUS: REVIEW NOT YET OBTAINED.** This packet is prepared material for an
independent reviewer. No external review has occurred; no reviewer has been
contacted, and no review result exists in this repository. Nothing in this
packet adopts, validates, or authorizes the proposed method. D2 is DEFERRED;
H-10 is UNRESOLVED; Campaign 4 is BLOCKED.

Prepared: 2026-10-11 (ET). Purpose: enable a qualified independent
statistician to assess method (b) — week-level sign-flip p-values with
Holm step-down — as Campaign 4's family-wise test. Owner standard: synthetic
evidence may falsify a candidate but can never establish real-data validity;
the exchangeability assumption in §5 cannot be proven by any local artifact
or diagnostic, and this packet does not claim otherwise.

---

## 1. The scientific claim and the proposed test

**Unit of analysis.** Paired out-of-fold (OOF) rows on the frozen 2023–2025
chronological folds; each predeclared experiment compares a candidate arm's
AUC to a reference arm's AUC on the same events. δ̂ = AUC(candidate) −
AUC(reference); the tested direction is H1: δ < 0.

**Intended claim if adopted.** "At campaign end, family-wise error rate of
formal REFUTED decisions across each predeclared Holm family is controlled
at α = 0.05, and each individual REFUTED decision corresponds to
statistically significant evidence that the candidate underperforms the
reference." Formal REFUTED status can arise *only* from the campaign-end
Holm-adjusted sign-flip decision (see §7); percentile-CI 0-exclusion is a
provisional signal only and never a formal decision.

**Exact statistic (method b).** With W weeks of paired OOF scores:

1. Compute the observed δ̂ on the real data.
2. For flip m = 1…M (M = 1,000): draw a sign vector s ∈ {−1, +1}^W with
   independent fair coins per week; within week w, swap (or not) the two
   arms' scores for all that week's events according to s_w; recompute the
   AUC difference δ_flip^(m). In the simulation code this is computed
   algebraically exactly via the closed form
   δ_flip = (s·g) / (2·n_pos·n_neg) for week-level contributions g,
   verified against brute-force AUC recomputation to max diff 1.5e-16.
3. One-sided lower-tail p-value:
   **p_b = ( #{m : δ_flip^(m) ≤ δ̂} + 1 ) / (M + 1)** — the +1 makes the
   p-value valid under the discrete floor; smallest representable p is
   1/(M+1) = 1/1,001.

**Null actually tested (sharp null).** Within every week w, the joint
distribution of the two arms' scores over that week's events is invariant
to swapping the arm labels — i.e., week-level arm-label exchangeability.
Under this sharp null the sign vector is uniform on {±1}^W regardless of the
data, so p_b is super-uniform and Holm is valid. **Note for the reviewer:**
the sharp null ("no within-week arm difference for any event distribution")
is stronger than the scientific claim of interest (aggregate δ ≥ 0). The
reviewer is explicitly asked whether exactness against the sharp null
transfers adequately to the weak/aggregate null that motivates REFUTED
decisions, or whether an asymptotic-justification gap must be closed.

**Multiplicity.** Holm step-down at α = 0.05 across each predeclared family,
computed once at campaign end. Holm controls FWER under arbitrary
dependence among valid super-uniform marginals; the open question is
marginal validity on real data (§5), not the Holm step itself.

---

## 2. Evidence classification (read this first)

| Item | Kind | Where |
|---|---|---|
| SIM-1…SIM-5 numbers, self-test results | **Synthetic** (falsification battery, proxy frames) | §3 |
| Frozen backend bootstrap semantics; six-gate adapter; draft C4 config; governance flake | **Observed** (local code/artifacts, hash-verified) | §3, §8 |
| Week-level exchangeability on real data; sharp-null-to-weak-null transfer; transport of synthetic calibration to the ~61k-row real frame | **Assumptions — unestablished** | §5, §6 |
| Shared-training dependence; temporal/4-week-block dependence; real-data FWER | **Unresolved — not simulated anywhere** | §6 |

**Forbidden readings of this packet (stated to prevent misuse):** the
simulations do not prove FWER ≤ 0.05 on real data; no diagnostic can prove
exchangeability; "no failure found under the predeclared battery" is not
validation.

---

## 3. The simulation battery: SIM-1 … SIM-5

DGP (all sims): score model s_X = θ_X·(2y−1) + u_week + d_i + ε_Xi, unit
total variance, so population AUC_X = Φ(√2·θ_X) and true δ is known exactly.
Paired arms share events, market-week factor u_week (level ρ) and event
difficulty d_i. Bootstrap scheme = frozen backend exactly (W-SUN weeks,
4-week circular blocks, in-frame order, truncate at n, percentile CI).
Full detail: `H10_SIMULATION_EVIDENCE_REPORT.md` (§3, §6–§8).

### SIM-1 — null calibration (N = 1,000 trials/cell; B = M = 1,000)
Six calibration cells (balanced; skewed; ρ ∈ {0, 0.5, 0.9}; regime small-n;
frames ~3,600 rows) + one power side-check (δ = −0.01).
Acceptance (predeclared): no cell significantly above nominal α by one-sided
exact binomial, Bonferroni-corrected over 72 tests (6 cells × 4 α × 3
methods), threshold 6.9e-4.
Results at α = 0.05 (cell means): (a) 6.35%, **(b) 4.98%**, (c) 6.32%.
(a) and (c) show consistent mild anti-conservatism (~+1.3 pp, all six cells
same sign; 12/24 and 8/24 raw flags); (b) 1 raw flag of 24, well centered.
All three formally pass the corrected criterion. Power side-check:
rejection ~41–46% for all three (no candidate outpowers another at m = 1).

### SIM-2 — Holm FWER (N = 2,000 campaigns/config; 540,000 member trials)
Global-null families m ∈ {1, 4, 12, 24, 36, 50, 90} × ρ ∈ {0, 0.3, 0.7}
(shared weeks/labels across members) × B = M ∈ {500, 1000, 2000}; frames
W = 40 × 20 = 800 rows; one mixed configuration (11 strong H1s + one true
H0, m = 12). Sharded run proven bit-identical to sequential on a shared
small config.
Acceptance (predeclared): no significant excess FWER above 0.05 under the
predeclared test — **this is a failure-to-detect criterion, explicitly not a
proof of FWER ≤ 0.05.**
Results at α = 0.05, attainable cells: **(b) 0.032–0.057 in every cell of
every ρ** (CP upper ≤ 0.064; mildly conservative at large m); mixed config
P(true H0 rejected) = 0.0525 at 98.5% H1 power; worst single cell 113/2,000,
exact one-sided binomial p = 0.1014. (a) 0.066–0.271 and (c) 0.063–0.242 —
both FAIL decisively (mild SIM-1 liberality compounding through Holm).
Mechanical zeros confirmed for infeasible (m, B): floor blocks all
rejections — fail-closed behavior demonstrated.

### SIM-3 — CI-vs-p disagreement (FAILS FOR ALL THREE CANDIDATES)
Rate of (p ≤ 0.05) XOR (percentile CI upper < 0) at m = 1, predeclared
pass ≤ 1%. Measured 1.4–10.5% for all candidates in all cells, including the
best-behaved (b) (1.4–2.8% null cells, 8.7% near-null) and (a) (2.1–3.5%
null, 10.1% near-null). Reading: the disagreement is structural — a
percentile-bootstrap CI and any sampled p-value invert different functionals
near the null boundary. The plan's prescribed remedy is decision-rule
reconciliation before adoption (§4). **The SIM-3 failure is retained in the
record and is not erased by any interpretation.**

### SIM-4 — freeze-time granularity feasibility (deterministic, method-independent)
H-10b test B + 1 ≥ 20·m against the draft C4 config (DRAFT_ONLY input):
capped families m ≤ 24/36/36/12 all feasible at B = 1,000; the unbound
contingency (m = 90) is **not** feasible (needs B ≥ 1,799). The draft C4
config does not pin `n_boot` at all — the freeze must pin `n_boot ≥ 1000`
and cap any family at m ≤ 50 or raise B, else the freeze fails closed.

### SIM-5 — paired-implementation equivalence + unpaired divergence
Literal sequential replica reproduces frozen `block_bootstrap_delta`
**exactly** (max |ΔCI| = 0.0; δ and n_boot_valid equal); production fast
path identical on shared draws; self-test battery (9 checks vs sklearn /
brute force / backend, tolerances 1e-12…1e-9) all PASS after catching three
early drafting bugs (reported transparently). Unpaired control (N = 300):
rejection 0.063 → 0.003, CI width ×2.47, Fisher exact p = 3.1e-05 — the
required divergence guard. **PASS.**

### Fixed limitations of the battery (report §10)
Synthetic DGP only (falsification, not proof); proxy frames (800–3,600 rows
vs the real ~61k); power probed only lightly (two probes); RNG batching
differs from backend in production draws (scheme equality + shared-draw
equivalence proven); granularity floor is feasibility, not power; residual
fast-path bug risk nonzero — frozen backend remains the production semantics
authority.

---

## 4. The SIM-3 reconciliation question (precise form)

D1 was recorded with the REMEDIAL interpretation: the plan's ≤1% CI-vs-p
criterion was unattainable for every candidate (including the CI-aligned
one), so the remedy is *reconcile the decision rule with the gates*, with
the failure explicitly retained. **This interpretation does not itself
authorize any method.** It only prevents an unattainable criterion from
functioning as a disguised disqualification, and it makes the reconciliation
below a mandatory pre-adoption item:

> **Question for the reviewer:** Campaign 4 would report both (i) a
> percentile-bootstrap CI (ROBUST uncertainty criterion and provisional
> signal) and (ii) a Holm-adjusted sign-flip p-value (sole formal
> REFUTED-maker). They disagree at 1.4–10.5% near the null boundary by
> construction. Is it statistically defensible to (1) let the p-value/Holm
> outcome alone carry formal decisions, (2) keep the CI as a disclosed
> effect-size/provisional marker, and (3) document the structural
> disagreement — or is some additional reconciliation (e.g., a different CI
> construction, or a consistency flag) required before adoption?

Until D2 closes with an approved method and C-3 is separately ratified, no
adoption occurs regardless of the review's answer.

---

## 5. Real-data exchangeability assumption (the core open question)

**Assumption A (adopted only if the review supports it).** Under the
campaign-relevant null, the two arms' weekly OOF score vectors are
exchangeable within each week, so independent fair-coin arm-label flips per
week generate the exact randomization distribution.

Why this may fail on real data — **none of these mechanisms was simulated:**

1. **Shared-training dependence.** Both arms' OOF predictions come from
   models fitted on overlapping training windows (and, for model-class
   comparisons, on identical rows/labels). Pairing through shared *evaluation*
   events and shared difficulty/week factors (d_i, u_week) *is* modeled in
   the sims; the dependence induced through shared *estimation* (overlapping
   fits, correlated prediction errors arising from training reuse rather
   than from shared events) is **not**. The reviewer is asked whether this
   mechanism plausibly breaks within-week arm-label symmetry, and in which
   direction.
2. **Asymmetric arm construction.** The sharp null requires label symmetry;
   if one arm is systematically noisier, differently calibrated, or
   structurally advantaged within weeks in a way that is not pure location
   shift, flips are not draws from the true null distribution.
3. **Non-superposition of the tested null.** The claim of interest is about
   aggregate δ, not the sharp null (see §1 note). Exactness is proven only
   for the latter.
4. **Unverifiability.** No local artifact, and no diagnostic even if later
   authorized, can *establish* exchangeability on the real data; a
   diagnostic can only *falsify* it. This is why an external review — not a
   local test — is the owner's chosen closure route.

---

## 6. Dependence structures not represented by the simulations

1. **Temporal dependence across weeks.** The DGP shares factors *within*
   weeks (u_week independent across weeks). Real weekly delta contributions
   may be serially correlated (regime persistence, overlapping macro
   conditions). The flip treats weeks as independent exchangeable units;
   serial correlation in the weekly contribution sequence is the second
   unsimulated mechanism (after shared training). The reviewer is asked
   whether week-level flips remain defensible under plausible positive
   serial correlation, and whether a block-level flip (per 4-week block, the
   bootstrap's own block unit) should be considered instead.
2. **4-week circular bootstrap blocks vs week-level flips.** The CI side of
   the pipeline resamples 4-week circular blocks; the test flips individual
   weeks. The two functionals therefore have different dependence
   structures by design — part of why SIM-3 disagreement is structural
   (§4), and disclosed rather than hidden.
3. **Frame scale.** Sims used 800–3,600-row proxy frames; the real study has
   ~61k rows across more weeks. Larger frames generally help normal
   approximations and reduce discretization — stated as an argument, not
   evidence.

---

## 7. Proposed Holm families, multiplicity rules, and the C-2 convention

To be adopted **only** if D2 closes in favor of method (b) and C-3 is
ratified. Terms approved-in-principle by the (unsigned) decision record,
subject to final configuration review at freeze:

- **Families (draft C4 config, 2 cells × max_per_direction 12 per family):**
  regime_split_analysis (m ≤ 24), target_horizon_robustness (m ≤ 36),
  purge_sensitivity_probe (m ≤ 36), complexity_reduction_check (m ≤ 12).
- **Multiplicity rule:** Holm step-down, α = 0.05, computed once at campaign
  end across each family. No mid-campaign testing, no membership change
  after results exist, no silent truncation/omission, no M increase.
- **M = 1,000, m ≤ 50** (H-10b: M + 1 = 1,001 ≥ 20·m; infeasibility fails
  closed — freeze blocked, and such signals can never become formal
  refutations). `n_boot ≥ 1000` is separately required for the CI and must
  be pinned at freeze (absent from the draft — see SIM-4).
- **C-2 Option A (unavailable members — owner-selected convention, to be
  frozen in the C4 config before any family is frozen):** an unavailable /
  failed / missing predeclared member test counts toward family size m, is
  recorded with assigned p = 1.0 (always rendered as "unavailable", never
  as observed evidence), can never be formally REFUTED, does not change
  other members' thresholds, and its experiment-level signal defaults to
  INCONCLUSIVE under the provisional-to-formal firewall. Exclusion after
  results exist is impossible. **Reviewer question:** is this bookkeeping
  coherent with Holm validity (conservative by construction), or does the
  reviewer see a defect (e.g., in threshold recomputation or family
  definition) that must be fixed before adoption?

---

## 8. Open items and known discrepancies (full disclosure)

1. **Governance-suite test flake (observed, open).** The governance test
   suite fails 1 run in 10 with the failing test's identity **not
   captured**. It must be reproduced and dispositioned before implementation
   acceptance. It is not attributed to any statistical component; it is
   disclosed here because the reviewer asked for all known discrepancies.
2. **"Five gates" vs six.** The plan's ROBUST wording says five gates; the
   actual adapter implements **six** (`experiment_adapter.py:975`: unit,
   data_integrity, leakage, walk_forward, robustness, evaluation). Resolved
   to six in the decision record (D3).
3. **Draft C4 config does not pin n_boot** (SIM-4 finding) — freeze must
   fix this or fail closed.
4. **RNG batching** in the production fast path differs from the backend
   call pattern (batched vs per-block); scheme equality is exact and
   equivalence proven on shared draws (SIM-5); the sequential replica is
   bit-for-bit equal to the backend.
5. **Historical baseline never reproduced.** Baseline of record is
   BASELINE_RECONSTRUCTED_2026_10; the historical V1.0.1 baseline was never
   reproduced and no such claim is made. No profitability or live-trading
   claim exists anywhere in this work.
6. **Sealed holdout untouched** (SEALED, uses = 0); nothing in this packet
   authorizes its access.

---

## 9. Questions to the reviewer and decision criteria

**Questions:**
1. Does the proposed sign-flip test's null (§1, §5) match the intended
   scientific claim, including the sharp-null vs weak-null distinction?
2. Do shared-training dependence (overlapping OOF fits) and week-to-week
   dependence materially undermine marginal calibration, and would you
   recommend block-level flips or a different construction?
3. Do the simulations (SIM-1…SIM-5) adequately test the proposed use case?
   What cell, frame size, or mechanism is missing in a way that blocks
   adoption?
4. Is the SIM-3 reconciliation (§4) — formal decisions via Holm p-values,
   CI as disclosed provisional/summary functional — statistically
   defensible?
5. Are the Holm family definitions and the C-2 unavailable-member rule
   (§7) coherent and conservative as claimed?
6. What additional evidence, if any, is necessary before adoption?

**Adoption-support criteria (D2 → adopt):** the reviewer concludes the null
and exchangeability assumptions are defensible *for the claimed use with the
disclosed limitations*, the simulations are adequate for the decision, and
any additional evidence needed is bounded and prespecifiable.
**Rejection criteria:** the reviewer finds exchangeability untenable, the
shared-training/serial mechanisms materially invalidate calibration in a way
no bounded remediation fixes, or essential evidence is missing — then D2 =
REJECT or remains DEFERRED and H-10 stays UNRESOLVED, fail-closed. A
favorable review is evidence for the owner to weigh, **not** authorization:
adoption still requires the owner's explicit D2 decision and C-3 ratification
with signatures.

---

## 10. Material list, hashes, and reproducibility

All hashes verified 2026-10-11 (SHA-256):

| File | SHA-256 |
|---|---|
| `stat_validation_h10/H10_SIMULATION_EVIDENCE_REPORT.md` | `85c6ac4f21be0755671726fe1ceb0db37d645206e7183692b9ff545a8255a884` |
| `stat_validation_h10/simh10.py` (simulation core) | `4b7ebd5f3ffc5413247cdcedb099d493a71e3cfc01346a68c8440de9d59b51f3` |
| `stat_validation_h10/run_sim.py` (stage runner) | `96aa497cebb30ae38a381e361540dc68566f098b108eb26056777dcfecb3dcc1` |
| `…/HARNESS_V1_1_0_IMPLEMENTATION_PLAN_2026_10_09.md` (plan v3, protocol authority) | `094827b0e9a5f1c1b6d0ed13c32b9e22a6ff7c76568624228e8b2cb9f738eb4e` |
| `stat_validation_h10/H10_DECISION_SHEET_DRAFT.md` (audited sheet) | `5a62c9d08e642c7e4d4c3e56e34c74d737ddbe0298efc2dc340e148a73257159` |
| `stat_validation_h10/H10_DECISION_RECORD_AWAITING_SIGNATURE.md` (unsigned) | `b9db32335c93ccf5a06b764023f21b6595c2fa4a0a4dd7ccbec6f87d2e9f0a42` |
| `autonomous_agent/state/campaign_config.json` (frozen pin; matches `campaign_config.sha256`) | `1e0e30b8ecd99119e3c12214aacd512167c7fb6546e7b946f9dd65d5436fea5a` |
| `…/CAMPAIGN_4_CONFIG_DRAFT_2026_10_09.json` (DRAFT_ONLY, not frozen) | `307e98ab4b7207dac24bada4a438686fb859b28bec5e919e80219e249168cdcd` |
| `autonomous_agent/experiment_adapter.py` (six-gate reference) | `d80723d38183ac43e66f89566cacade141f6bfcf1463d6318414d3c3b6cc61aa` |
| `results/selftest.json` | `fb7fce987be73be5a3de08519de709665d1bc6a345ecdb8e2f097465ad5076da` |
| `results/sim1_summary.json` | `d203e04bcb5e3af331f6fea7b4e02192bd0c1a79d811f53c81ab208c6209bbc0` |
| `results/sim2_summary.json` | `e2b267e49a6df52731f77e1041a60b474ff524032cac76cb3b4123d313c07bbb` |
| `results/sim3.json` | `02b84d7d26fdae3403d91661623565a33a341aabdfd7778eba6dfea6ef59f848` |
| `results/sim4.json` | `e00f4b1e1fabc3cf1aa32cc7b8d038087ab24e1eb0ae8f8af3501e4564422c15` |
| `results/sim5.json` | `4bf8d364aba232d9b6c1eab70a7552b8ac86487c0c6f052c912926ee5a156bc2` |

(Also shipped on request: per-cell `results/sim1_*.json/.npz`,
`sim2_rho*_pvalues.npz` (~11 MB each, full member-trial p-values), shard
logs, `run_full.log`.)

**Protocol versions:** plan v3 (2026-10-09) is the protocol authority; sim
completed 2026-10-11 under it; recipe library v1.0.0; C4 config is the
2026-10-09 DRAFT (never frozen). Seeds (recorded per output `meta` with UTC
timestamps and the then-current `simh10.py` hash): SIM-1 cells 1100–1106;
SIM-2 ρ 2200–2202, mixed 2999; SIM-5 fixture 21/42, unpaired 5500; self-test
7/11/13/21.

**Reproduce (repo root):**
`py -3 -X utf8 stat_validation_h10/run_sim.py all`
(plan-compliant defaults). SIM-2 as actually run:
`sh stat_validation_h10/run_sharded_sim2.sh` (8 strided shards + merge;
smoke-proven bit-identical to the sequential `run_sim.py sim2` path).
Environment: Python 3.13.1, numpy 2.3.3, scipy 1.16.2, sklearn 1.9.0.
Reviewer may re-run any subset; runtime ~14 core-hours for SIM-2.

---

## 11. Ready-to-send review request (appendix)

> Subject: Independent statistical review request — permutation-based
> FWER-controlled testing procedure (with simulation code)
>
> I am seeking an independent expert review of a preregistered statistical
> decision procedure before it is adopted in an automated research harness.
> The material is a self-contained packet (~this document plus the evidence
> report and simulation code, hashes listed in §10). No data confidentiality
> obligations apply beyond not redistributing the materials; the code is
> reproducible on your side (§10).
>
> Scope: (1) whether a week-level arm-label sign-flip p-value with Holm
> step-down is valid for the claimed use, given the sharp-null/weak-null
> distinction and the unverifiable week-level exchangeability assumption;
> (2) whether shared-training dependence (overlapping OOF model fits) and
> serial week dependence materially undermine calibration; (3) whether the
> simulation battery adequately tests the use case; (4) whether the
> documented CI-vs-p disagreement reconciliation is defensible; (5) whether
> the Holm family definitions and missing-member (assigned p = 1) rule are
> coherent; (6) what additional evidence, if any, is required before
> adoption. A written assessment answering the six questions in §9, with
> reasoning and limitations, is the requested deliverable.
>
> This is a methods-and-code audit request, not an analysis job. Please
> state any conflict of interest, the review's scope boundaries, and your
> qualifications in your response.

**Routes identified (verified service pages, 2026-10-11; owner chooses — the
agent does not contact anyone, and no reviewer has been engaged):**

1. Kolabtree (freelance statistical reviewers; methods-and-code review
   briefs; platform estimates ~$30/hr, ~$400 average project, example
   analysis-verification $2,000 / ~3 weeks) —
   https://www.kolabtree.com/services/statistical-analysis
2. University of Georgia Statistical Consulting Center (accepts external
   clients; published rates 60–200 USD/hr by seniority/status, effective
   2020-07-01 — confirm; free initial hour) —
   https://www.stat.uga.edu/consulting-fees
3. Penn State Statistics Consulting Center (external industry/government
   clients; estimate on request) — https://scc.stat.psu.edu/
4. Registered Reports at a participating journal (formal peer review of the
   protocol before results; slower, journal-specific) —
   https://www.cos.io/initiatives/registered-reports
5. Cross Validated (free public Q&A for narrow questions only — explicitly
   **not** a substitute for this independent review) —
   https://stats.stackexchange.com/help/on-topic

An owner-designated qualified individual (e.g., a statistician known to the
owner) is equally acceptable; the requirement is genuine independence from
this project's authorship, a written assessment, and no fabricated or
imputed verdict.

---

## 12. What happens with the outcome (owner-only decisions; no pre-authorization)

- **If the review supports adoption:** the owner still must (1) decide D2 =
  adopt and (2) ratify C-3, each explicitly and by signature. Only then does
  the method become approved — then a separate implementation authorization
  is required before harness v1.1.0 work, then configuration-freeze
  approval, then separate explicit launch authorization. Every one of these
  is the owner's act; this packet authorizes none of them.
- **If the review finds material unresolved issues:** D2 stays DEFERRED and
  the reviewer's smallest necessary resolution path is recorded; H-10 stays
  UNRESOLVED, fail-closed.
- **If the review rejects the method:** the owner chooses the
  alternative-method path; nothing is silently substituted.
- **Independent work proceeds regardless:** D1, D3, D4, D5, C-1, C-2 and
  C-4 are recorded in the (still unsigned) decision record and do not depend
  on D2.

*End of packet. No method is adopted, no review has been obtained, and no
approval, signature, freeze, or launch is implied by this document.*
