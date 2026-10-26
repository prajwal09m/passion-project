# H-10 / D2 — PRODUCTION SIGN-FLIP PORT SPECIFICATION (binding requirements + acceptance tests)

**Date:** 2026-10-13. **Author:** the project's assigned AI reviewer
(Buffy/Codebuff). **Status:** PREPARED, NOT IMPLEMENTED. This is the
implementation specification and acceptance-test plan required by the D2
review (§10 item 5) and ADDENDUM A (remedy item 3 / A-8). The port itself is
gated: decision-sheet **gate 4 (port + equivalence tests) legitimately
cannot start before D2 closure**, and D2 is undecided
(`launch_gates.json: d2_decided.decided = false`). Everything below is
preparation only — no production sign-flip code exists in
`autonomous_agent/` non-test source (re-verified 2026-10-13), and this spec
adds none. When the owner records D2 (adopt) + C-3 ratification + the
protocol amendment, the port implements exactly this contract; the
acceptance tests below become the gate-4 test file.

## 0. Scope and non-goals

**In scope:** one module (proposed path
`autonomous_agent/proposal_layer/signflip.py`) that computes the one-sided
week-level sign-flip Monte-Carlo p-value for a single predeclared
degradation test, plus its wiring into the campaign-end multiplicity record
(`multiplicity.py` — already implemented and frozen for structure). Method
(b) only: week-level arm-label flips, lower tail, M = 1000, Holm step-down
over the four frozen families at α = 0.05, formal `REFUTED` issued only by
the campaign-end record.

**Out of scope / forbidden in the port:**

- No change to `APPROVED_P_VALUE_METHODS` by the port itself. Adding the
  method name remains an owner act recorded in the H-10 decision record
  (multiplicity.py docstring invariant: "Adding a method name requires the
  recorded H-10 decision — an owner decision, never a code-only change").
  Until that record exists, `require_approved_method()` must continue to
  raise `PValueMethodUnresolved` for every name, and the acceptance tests
  assert exactly that (fail-closed preserved).
- No studentized permutation, no block-level flips, no weak-null claims.
  The named upgrade path (Chung–Romano-type studentized permutation) stays
  recorded in review §8 and requires its own protocol amendment; it is not
  implemented here.
- No change to bootstrap/CI machinery, gates, thresholds, budgets, or the
  firewall.

## 1. The statistic and the null (verbatim contract)

- Statistic: δ̂ = AUC(score_B) − AUC(score_A) on the OOF evaluation frame,
  aggregated over W market weeks; flip unit = whole week (both arms' scores
  swapped within the week, equivalent to flipping the week's signed
  contribution g_w).
- Linear form (review Result 3, algebraically exact):
  `δ_flip(s) = (s · g) / (2 · n_pos · n_neg)` for s ∈ {±1}^W, with
  n_pos/n_neg invariant to within-week arm swaps. The port MUST use this
  linear form and MUST pass acceptance test A-3 (max |diff| < 1e-9 vs
  brute-force AUC recomputation; identity at all-+1 exact).
- Null (the one the claim needs): product-group invariance — swapping the
  two arms' scores within any subset of weeks leaves the joint law
  invariant. Disclosed assumption; unestablishable by any local artifact
  (review §5). Every emitted artifact must carry the disclosure string
  `assumption: week-level arm-label exchangeability (unestablished)`.
- Alternative (H1): δ < 0 (candidate underperforms reference), one-sided
  lower tail.

## 2. The p-value (C-4 formula, verbatim)

```
p = (1 + #{b ∈ 1..M : δ_flip(s_b) ≤ δ̂}) / (M + 1)
```

- `≤` tie handling (conservative), the `+1` correction, and lower-tail
  direction are mandatory and match the protocol text
  (`simh10.py:452`) exactly.
- M = 1000 pinned in the campaign config's `multiplicity_policy.n_flips`
  (see §6). The port refuses to run if the effective M differs from the
  frozen config value (fail-closed on provenance).

## 3. C-1 — generation of flip rows (binding)

The port MUST generate the M flip rows as **i.i.d. uniform draws on the
full group {±1}^W**, matching the reference implementation semantics
(`simh10.py:450`, `run_sim.py:308`):

```python
rng = np.random.default_rng(seed)
S = rng.integers(0, 2, size=(M, W)) * 2 - 1
```

Hard requirements:

1. **Uniformity and independence.** Every row i.i.d.; no symmetry
   enforcement, no antithetic pairing, no "balancing", no de-duplication,
   no rejection of "unusual" rows. Any curation invalidates Result 2′-B
   (Addendum A §5) and is a spec violation.
2. **No outcome-conditioned redraw.** The rows (or the seed that
   deterministically generates them) MUST be fixed and recorded **before**
   any δ̂, any p-value, and any outcome-inspecting step is computed. The
   generation call site must be upstream of data access in the execution
   order, and the emitted record must carry
   `flip_draw_stage: "before_outcome_evaluation"`.
3. **Group coverage.** W is taken from the actual frame (W = 157 weeks in
   the real frame); rows are full-length W-vectors. If a test is ever run
   on a subset of weeks, the subset is declared in the predeclared test
   spec, not chosen post hoc.

## 4. C-2 — seed and realization record (binding; the hard-corrected part)

ADDENDUM A retracted conditional-on-fixed-set exactness (Result 2). The
operative guarantee is **procedure-level** (Result 2′-B): valid *marginal
over the draw of the flip set, independent of the data*. The port MUST
therefore satisfy, in this order:

1. **Data-independent draw.** The seed must be drawn by the documented
   randomization — e.g. `secrets.randbits(64)` or the campaign
   seed-derivation (`default_rng([stage_seed, c])` style) — and MUST NOT be
   derived from any data, any outcome, any candidate score, or any
   inspect-then-decide step.
2. **Recorded before evaluation.** The seed (or the full generated matrix,
   whichever is canonical) is persisted to the experiment record
   *before* outcome evaluation. The record carries:
   - `flip_seed`: the integer seed,
   - `flip_rng`: the exact generator + bit-generator names and numpy
     version (`numpy.random.default_rng` / `PCG64` / version string),
   - `flip_M`, `flip_W`,
   - `flip_rows_sha256`: sha256 of the generated `(M, W)` int8 matrix bytes
     (regeneration check, not the canonical object),
   - `flip_draw_stage: "before_outcome_evaluation"`.
3. **A constant seed is NOT automatically a valid draw.** This is the
   explicit distinction the remediation requires. A hard-coded constant
   seed (like the bootstrap's pinned `seeds[0] = 42`) produces a
   *deterministic transformation set that never varies*. Two cases:
   - **Case A (acceptable, recorded procedure):** the constant is one
     *recorded realization* of the documented data-independent draw — the
     seed was generated by the randomization once, its provenance and
     timestamp precede all outcome evaluation, and the record presents the
     rows as "one realized draw of procedure P". Procedure-level validity
     then holds exactly as for a fresh draw (the guarantee never depended on
     re-randomization per test).
   - **Case B (invalid as a guarantee, must be documented, not resolved):**
     the seed is a compile-time constant with no recorded draw event — the
     set then never varies and *nothing in the record establishes that it
     was drawn independently of the data*. The port MUST NOT claim
     procedure-level validity in this case; it MUST fail closed with
     `FlipProvenanceMissing` unless an explicit, owner-signed note records
     the Case-A provenance. **The port spec does not declare Case B
     resolved; it documents it as unsupported.** (For Campaign 4 the
     predeclared procedure is Case A: draw once from the documented RNG at
     freeze time, record, and never redraw.)
4. **No set-conditional claims anywhere.** No emitted string may assert
   validity "conditional on the flip set", "given the flip set", "exact for
   this set", or equivalent (ADDENDUM A C-5). The reader-facing note in the
   multiplicity record already carries the corrected MC-resolution text;
   the port's artifacts append
   `validity_scope: "procedure_level_marginal_over_flip_draw"`.
5. **Never re-drawn, never re-used after inspection.** One draw per frozen
   test definition. If a test is re-run (crash restart), the SAME recorded
   seed/rows MUST be reused (determinism), never re-drawn; a re-draw after
   any inspection is a spec violation and must raise.

## 5. Required API (proposed, minimal)

```python
class FlipProvenanceMissing(Exception): ...

@dataclass(frozen=True)
class FlipDraw:
    seed: int; rng_name: str; bitgen: str; numpy_version: str
    M: int; W: int; rows_sha256: str
    stage: str  # must equal "before_outcome_evaluation"

def draw_flips(W: int, M: int, seed: int) -> tuple[np.ndarray, FlipDraw]
    # returns (S in {±1}^{(M,W)} int8, provenance). Pure; no data access.

def signflip_p_value(delta_hat: float, g: np.ndarray,
                     draw: FlipDraw, S: np.ndarray) -> float
    # (1 + #{s·g/(2 n+ n-) <= delta_hat}) / (M + 1); raises if the passed
    # draw/S fail the provenance checks (stage, M match, rows hash match).

def linear_deltas(g: np.ndarray, S: np.ndarray, n_pos: int, n_neg: int)
    # (S @ g) / (2 * n_pos * n_neg); the Result-3 linear form.
```

Fail-closed behaviors (each an acceptance test):

- `signflip_p_value` raises `FlipProvenanceMissing` when `draw.stage !=`
  `"before_outcome_evaluation"`, when `draw.M != S.shape[0]`, or when
  `rows_sha256` mismatches the actual matrix bytes.
- The campaign-end path (`multiplicity.campaign_end_record`) continues to
  raise `PValueMethodUnresolved` until the owner records the method name;
  the port does not bypass it, and no test monkeypatches the allowlist
  outside a clearly-labeled synthetic fixture context.
- Granularity: with the frozen M = 1000 and family bounds 24/36/36/12,
  `feasibility()` (now M-aware, see §6) must report feasible; the port
  refuses any family where `M + 1 < 20·m` (raises
  `GranularityInfeasible`), mirroring the H-10b rule on the p-value side.

## 6. M in the multiplicity record and feasibility check (review §6 gap — fixed this session)

The review's freeze-test gap: "D4 defines feasibility on **M**, but
`feasibility()` and the campaign-end record key on `n_boot`; M appears
nowhere in production. A reduced M would silently make formal refutations
unattainable while the freeze test passes (conservative, but wrongly
labeled feasible)."

Remediated 2026-10-13 in `autonomous_agent/proposal_layer/multiplicity.py`
(mutable, unpinned — structural change, no method adopted):

- `feasibility(n_boot, family_size, n_flips)` now takes the sign-flip count
  and enforces **both** `n_boot + 1 ≥ 20·m` (bootstrap/CI granularity) and
  `n_flips + 1 ≥ 20·m` (p-value resolution), plus the D4 caps.
- `assemble_record` / `campaign_end_record` require `n_flips` and record it
  per family in the `feasibility` block
  (`{"n_boot":…, "n_flips":…, "rules":[…], "feasible":…}`), so a recorded
  feasibility can never disagree with the actual p-value resolution.
- `MIN_N_FLIPS = 1000` (H-10b floor for method (b)); D4's `M = 1000` at
  `m ≤ 50` verified exact at its boundary (1/1001 = 0.000999 ≤ 0.001;
  fails at m = 51 — review §6 table).
- Existing two-argument call sites default `n_flips=None`, which yields
  `feasible=False` with an explicit "n_flips missing" reason (fail-closed,
  never silently feasible on the n_boot side alone).

## 7. Acceptance tests (the gate-4 test file, to be added with the port)

All tests below are *specified now*; they either (a) run today against the
reference implementation where one exists, or (b) are marked as requiring
the port module. The suite must pass with the port absent (skip, not
fail — absence is the current correct state) and must fail-closed on every
provenance violation once present.

| # | test | asserts | runs today? |
|---|---|---|---|
| A-1 | formula + ties | p == (1+#{≤})/(M+1) on hand-computed fixtures incl. exact ties at δ̂ | yes (reference) |
| A-2 | lower tail direction | negative δ̂ with δ_flip mass above it → small p; sign flip of data → p → 1−p+O(1/M) | yes (reference) |
| A-3 | linear form exactness | max\\|linear − brute-force AUC\\| < 1e-9; all-+1 identity == δ̂ | yes (self-test rerun 2026-10-13) |
| A-4 | uniform generation | rows ∈ {±1}^W; row marginals ≈ 0.5 at M=1000 (two-sided binomial, loose bound); rows change with seed | yes |
| A-5 | i.i.d. (no curation) | no duplicate-row rejection, no balancing: generated matrix fed through unchanged; count of rows == M exactly | yes |
| A-6 | provenance recorded pre-evaluation | FlipDraw.stage == "before_outcome_evaluation"; rows_sha256 verifies; numpy/bitgen strings present | yes (reference semantics) |
| A-7 | fail-closed provenance | FlipProvenanceMissing on stage mismatch / M mismatch / hash mismatch | yes (reference semantics) |
| A-8 | seed reuse determinism | same seed → identical S, identical p; re-draw attempt after inspection raises | yes |
| A-9 | M handling incl. M=1000 | p resolution == 1/(M+1); M=1000 accepted; M+1 < 20·m → GranularityInfeasible | yes |
| A-10 | multiplicity integration | campaign_end_record carries n_flips per family; feasibility reflects M; Holm unchanged | yes |
| A-11 | method gate intact | require_approved_method raises for all names while H-10 open; allowlist empty | yes |
| A-12 | equivalence fixtures | port output == reference output bit-for-bit on frozen fixtures (deterministic g, S from pinned seeds) | **no — requires port** |
| A-13 | no set-conditional claims | grep-level assertion: no emitted artifact string matches conditional-on-set validity patterns | yes |

Fixtures for A-12: three frozen cases (identity-flip exactness; a pinned
20-row synthetic g with seeds 20261013/14; a tie-heavy case with δ̂ exactly
equal to a flip delta), stored as JSON next to the test file with their
generation script and hashes.

## 8. What the port does NOT change

- Week-level exchangeability remains the disclosed assumption (C-3) — the
  port's artifacts carry the disclosure; nothing in code can establish it.
- SIM calibrations, the MC-resolution table (combinatorics), and Result 5
  (Holm under arbitrary dependence) are untouched.
- The sealed holdout, all pins, all approval fields, and Campaign 3's
  frozen config remain untouched by this spec.

## 9. Prerequisites before any line of §5 is written

1. Owner signs the D2 protocol amendment
   (`H10_D2_PROTOCOL_AMENDMENT_PROPOSED_2026_10_13.md`) and records
   `d2_decided` with the accepted limitations verbatim.
2. Owner ratifies C-3 (`H10_C3_RATIFICATION_PROPOSED_2026_10_13.md`) and
   records `c3_ratified`.
3. Decision-sheet gate 4 is the act that authorizes implementation; the
   tests in §7 are its acceptance criteria.
4. Only then: implement §5, run §7 (A-12 last), record results next to the
   flake-evidence file per the established pattern.
