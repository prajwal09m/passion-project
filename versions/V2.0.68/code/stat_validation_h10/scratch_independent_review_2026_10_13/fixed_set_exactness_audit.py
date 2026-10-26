#!/usr/bin/env python3
"""SCRATCH - adversarial audit of Result 2 (fixed-set exactness), 2026-10-13.

Claim under audit (verbatim, D2_AI_INDEPENDENT_STATISTICAL_REVIEW.md
Section 4, Result 2, lines 136-146):

  "For any *fixed* set of M flip vectors and the identity, under the
   invariance null the vector (T_obs, T(s_1), ..., T(s_M)) has the same
   joint distribution as its shift by any group element, hence all M+1
   coordinates are exchangeable, hence the rank of T_obs is uniform on
   {0...M}, hence p_MC is exactly super-uniform conditionally on the flip
   set ... A production port with a pinned flip seed ... is therefore
   still exact under the null."

Parts:
  A. In-family counterexample, closed form + Monte-Carlo:
     W=4 weeks, F = {e, s1, s2} (identity + M=2 flip vectors), statistic
     T(x) = mean(x) (the linear week form certified by Result 3),
     x ~ N(0, I4) - a law invariant under the FULL product group (the
     report's null holds exactly).  p = (1 + #{b: T(s_b x) <= T(x)})/3.
     P(p <= 1/3) = 1/4 + arcsin(2/3)/(2*pi) = 0.36614 > 1/3.
  B. The claimed exchangeability fails directly: correlation matrix of
     (T(x), T(s1 x), T(s2 x)) is not invariant under swapping coordinates
     0 and 1, and the shifted set F*s1 != F (different set).
  C. Exhaustive enumeration over ALL 2^15 = 32768 fixed sets F containing
     the identity (subset of the 2^4 sign-flip group), null = uniform on
     {+-1}^4 (product-group invariant), T = mean.  For every F: check
     super-uniformity of p at every attainable threshold.  Result:
     violations occur only for non-closed (non-subgroup) sets; closed
     sets always pass (Theorem A).  Report max violation.
  D. Fresh-draw verification (Theorem B / Phipson-Smyth): rows drawn iid
     uniform per trial -> empirical size at threshold ~ nominal, i.e.
     validity holds MARGINALLY over the flip-set draw, not conditionally
     on a realized set.  Two geometries: (W=4, M=2, alpha=1/3) and
     (W=6, M=1000, alpha=0.05).

READ-ONLY wrt evidence; writes only into this directory.
Usage:  py -3 -X utf8 fixed_set_exactness_audit.py
"""
from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for cand in ("C:\\Python313\\python313.dll", "C:\\Python313\\python311.dll"):
    if Path(cand).exists():
        import ctypes
        sys.path_importer_cache.clear()
        ctypes.CDLL(cand)
        break
import numpy as np  # noqa: E402


# ----------------------------------------------------------------- helpers
def sgn(mask: int, W: int) -> np.ndarray:
    """Sign vector of the group element given as a bit mask (bit w set -> -1)."""
    return 1.0 - 2.0 * ((mask >> np.arange(W)) & 1)


def table_T(W: int) -> np.ndarray:
    """A[g][j] = T(g . x_j) for T = mean, g, j indexed by bit masks 0..2^W-1."""
    xs = np.array([sgn(j, W) for j in range(1 << W)])       # rows: x_j
    out = np.empty((1 << W, 1 << W))
    for g in range(1 << W):
        out[g] = (sgn(g, W) * xs).mean(axis=1)
    return out


def is_subgroup(F: list[int]) -> bool:
    s = set(F)
    return all((a ^ b) in s for a in F for b in F)          # XOR = composition


def p_of(A: np.ndarray, F: list[int], j: int) -> float:
    t_obs = A[0][j]
    cnt = sum(1 for g in F if A[g][j] <= t_obs + 1e-12)
    return cnt / len(F)


# ------------------------------------------------------- A. closed form + MC
def part_a_counterexample() -> dict:
    W = 4
    e, s1, s2 = 0, 0b0111, 0b1011        # flip sets {0,1,2} and {0,1,3}
    rho = 2.0 / 3.0                      # Corr(Y1, Y2), Y_b = sum_{i in F_b} x_i
    exact = 0.25 + math.asin(rho) / (2 * math.pi)

    # Monte-Carlo with the SAME geometry (fresh x each draw; F pinned)
    rng = np.random.default_rng(20261013)
    N = 2_000_000
    x = rng.normal(size=(N, W))
    T0 = x.mean(axis=1)
    T1 = (sgn(s1, W) * x).mean(axis=1)
    T2 = (sgn(s2, W) * x).mean(axis=1)
    cnt = (T1 <= T0 + 1e-12).astype(int) + (T2 <= T0 + 1e-12).astype(int)
    p = (1 + cnt) / 3.0
    size = float((p <= 1.0 / 3.0 + 1e-12).mean())
    se = math.sqrt(max(size * (1 - size), 1e-12) / N)

    # duplicate-row variant: F = {e, s, s}  ->  p in {2/3, 1}  (bounded below)
    # distinct-row near-duplicate: flip sets of size 4 sharing 3 coords gives
    # rho = sqrt(3/4) -> size = 0.25 + asin(sqrt(3/4))/(2 pi)
    rho2 = math.sqrt(3.0 / 4.0)
    dup_close = 0.25 + math.asin(rho2) / (2 * math.pi)

    # set-mapping:  F * s1 (right translate) vs F
    Fs1 = sorted({g ^ s1 for g in (e, s1, s2)})
    return {
        "null": "x ~ N(0, I4): invariant under the FULL product group (report's null holds)",
        "statistic": "T(x) = mean over 4 weeks (linear week form, Result-3 family)",
        "fixed_set_F": [e, s1, s2],
        "M_flip_vectors": 2,
        "set_mapping_F_times_s1": Fs1,
        "equals_F": Fs1 == [e, s1, s2],
        "closed_form_size_at_alpha_1_over_3": round(exact, 6),
        "mc_size_N2m": round(size, 6),
        "mc_se": round(se, 6),
        "mc_95ci": [round(size - 1.96 * se, 6), round(size + 1.96 * se, 6)],
        "exceeds_1_over_3": exact > 1.0 / 3.0,
        "near_duplicate_rows_size": round(dup_close, 6),
        "verdict": "conditional-on-set super-uniformity FALSE even in-family, null exact",
    }


# ------------------------------------------------- B. non-exchangeability
def part_b_exchangeability() -> dict:
    W = 4
    e, s1, s2 = 0, 0b0111, 0b1011
    # V = (T(x), T(s1 x), T(s2 x)); for x ~ N(0,I): Corr(T(gx), T(hx)) = mean(g . h)
    F = [e, s1, s2]
    M = np.array([[float((sgn(a, W) * sgn(b, W)).mean()) for b in F] for a in F])
    swapped = M[np.ix_([1, 0, 2], [1, 0, 2])]          # swap coordinates 0 and 1
    exchangeable = bool(np.allclose(M, swapped))
    marg = np.diag(M)
    return {
        "corr_matrix": [[round(v, 4) for v in row] for row in M],
        "all_marginals_identical": bool(np.allclose(marg, marg[0])),
        "corr_matrix_after_swapping_coords_0_1": [[round(v, 4) for v in row]
                                                  for row in swapped],
        "jointly_exchangeable": exchangeable,
        "shifted_set_F_times_s1": sorted({g ^ s1 for g in F}),
        "shift_maps_set_onto_itself": sorted({g ^ s1 for g in F}) == F,
        "note": ("identical marginals + null invariance do NOT give joint "
                 "exchangeability; the 'shift' maps F to a different set"),
    }


# ------------------------------- C. exhaustive enumeration of all fixed sets
def part_c_enumeration() -> dict:
    W = 4
    A = table_T(W)                                  # T(g . x_j)
    xs = list(range(1 << W))                        # null: uniform on all x
    non_id = list(range(1, 1 << W))
    n_groups = n_bad_groups = n_sets = n_bad_sets = 0
    worst = None
    group_sizes_seen = set()
    for r in range(0, len(non_id) + 1):
        for combo in itertools.combinations(non_id, r):
            F = [0] + list(combo)
            k = len(F)
            ps = [p_of(A, F, j) for j in xs]
            thresh = sorted(set(round(v, 12) for v in ps))
            for v in thresh:
                cdf = sum(1 for pv in ps if pv <= v + 1e-12) / len(xs)
                excess = cdf - v
                if excess > 1e-12:
                    rec = {"F_size": k, "alpha": v, "empirical_cdf": round(cdf, 6),
                           "excess": round(excess, 6), "F": F}
                    if is_subgroup(F):
                        n_bad_groups += 1
                        if worst is None or excess > worst.get("excess", 0):
                            worst = dict(rec, kind="SUBGROUP (theorem A violated!)")
                    else:
                        n_bad_sets += 1
                        if worst is None or excess > worst.get("excess", 0):
                            worst = dict(rec, kind="non-closed set")
            if is_subgroup(F):
                n_groups += 1
                group_sizes_seen.add(k)
            n_sets += 1
    # size-3 example explicitly
    A2 = A
    F_ex = [0, 0b0111, 0b1011]
    ps = [p_of(A2, F_ex, j) for j in xs]
    v = 1.0 / 3.0
    cdf = sum(1 for pv in ps if pv <= v + 1e-12) / len(xs)
    return {
        "null": "x uniform on {+-1}^4 (product-group invariant, ties present)",
        "statistic": "T = mean over weeks",
        "sets_checked": n_sets,
        "closed_sets_subgroups": n_groups,
        "closed_set_sizes_observed": sorted(group_sizes_seen),
        "violations_among_closed_sets": n_bad_groups,
        "threshold_violation_events_in_non_closed_sets": n_bad_sets,
        "worst_violation": worst,
        "explicit_size3_example_F": F_ex,
        "size3_example_p_dist": {str(round(vv, 6)): ps.count(vv)
                                 for vv in sorted(set(ps))},
        "size3_example_cdf_at_1_3": round(cdf, 6),
        "size3_example_exceeds": cdf > v + 1e-12,
        "interpretation": ("every fixed-set violation found is non-closed; "
                           "subgroup sets pass (Theorem A); production "
                           "M=1000 -> |F| = 1001 odd -> F can never be a "
                           "subgroup of a 2-group"),
    }


# ------------------------------------------------- D. fresh-draw verification
def part_d_fresh_draws() -> dict:
    rng = np.random.default_rng(20261013 + 7)

    # (i) W=4, M=2, alpha = 1/3   (same geometry as the counterexample)
    N = 400_000
    x = rng.normal(size=(N, 4))
    s1 = rng.integers(0, 2, size=(N, 4)) * 2 - 1
    s2 = rng.integers(0, 2, size=(N, 4)) * 2 - 1
    t0 = x.mean(axis=1)
    cnt = ((s1 * x).mean(axis=1) <= t0 + 1e-12).astype(int) + \
          ((s2 * x).mean(axis=1) <= t0 + 1e-12).astype(int)
    p = (1 + cnt) / 3.0
    sz = float((p <= 1.0 / 3.0 + 1e-12).mean())
    se = math.sqrt(sz * (1 - sz) / N)
    # exact fresh-draw value with orbit ties: V_0..V_M iid uniform over the
    # |O|=16 orbit T-values -> P(V_0 strictly smallest of 3)
    n_orbit = 16
    exact_fresh = sum(((n_orbit - r) / n_orbit) ** 2 for r in range(1,
                      n_orbit + 1)) / n_orbit

    # (ii) production-like: W=6, M=1000, alpha = 0.05 (fresh rows per trial)
    N2, M2, W2 = 4000, 1000, 6
    hits = 0
    ps = np.empty(N2, dtype=float)
    lo = 0
    while lo < N2:
        n = min(200, N2 - lo)
        xb = rng.normal(size=(n, W2))
        s = rng.integers(0, 2, size=(n, M2, W2)) * 2 - 1
        vb = (s * xb[:, None, :]).mean(axis=2)        # (n, M2)
        v0 = xb.mean(axis=1)
        c = (vb <= v0[:, None] + 1e-12).sum(axis=1)
        ps[lo:lo + n] = (1 + c) / (M2 + 1.0)
        lo += n
    hits = int((ps <= 0.05 + 1e-12).sum())
    sz2 = hits / N2
    se2 = math.sqrt(sz2 * (1 - sz2) / N2)
    target2 = 50.0 / 1001.0          # rank of V0 among 1001 iid continuous
    return {
        "case_i_W4_M2_alpha_1_3": {
            "N": N, "size": round(sz, 6), "se": round(se, 6),
            "exact_with_ties": round(exact_fresh, 7),
            "no_ties_target": 0.333333,
            "note": ("fresh iid uniform rows per trial: valid MARGINALLY "
                     "over the draw; exact size below 1/3 (orbit ties make "
                     "ties conservative)"),
        },
        "case_ii_W6_M1000_alpha_0_05": {
            "N": N2, "M": M2, "size": round(sz2, 6), "se": round(se2, 6),
            "theory_rank_bound": round(target2, 6),
            "note": "same formula as production p=(1+count)/(M+1); super-uniform",
        },
        "contrast": ("same p-formula: conditional on the BAD pinned set of "
                     "part A -> 0.366; fresh draw -> ~0.333. Validity is a "
                     "property of the draw, not of an arbitrary realized set."),
    }


def main() -> None:
    out = {
        "meta": {"what": "adversarial audit of D2 review Result 2 (fixed-set "
                         "sign-flip exactness)", "date": "2026-10-13",
                 "scratch": True},
        "A_counterexample": part_a_counterexample(),
        "B_non_exchangeability": part_b_exchangeability(),
        "C_exhaustive_enumeration": part_c_enumeration(),
        "D_fresh_draw_verification": part_d_fresh_draws(),
    }
    txt = json.dumps(out, indent=2)
    print(txt)
    (HERE / "fixed_set_exactness_audit_results.json").write_text(txt, encoding="utf-8")
    print(f"[saved] {HERE / 'fixed_set_exactness_audit_results.json'}", flush=True)


if __name__ == "__main__":
    main()
