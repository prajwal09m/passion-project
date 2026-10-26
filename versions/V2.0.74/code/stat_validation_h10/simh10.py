"""Isolated statistical validation harness for Campaign 4 decision H-10.

Scope: SIM-1 (null calibration), SIM-2 (Holm family-wise error), SIM-3
(CI-vs-p disagreement), SIM-4 (freeze-time granularity feasibility), SIM-5
(paired-resampling consistency and equivalence with the frozen harness
bootstrap). This module is deliberately standalone: it imports nothing from
the live research harness except a read-only load of the frozen study
backend inside `selftest_fixture_comparison` (mirroring
`recipe_harness._load_frozen_study`, which documents that import as
read-only). All outputs are written under stat_validation_h10/results/.

Semantics mirrored from the frozen study backend
(`study_files/backend/demand_zone_study_v1.py::block_bootstrap_delta`,
read-only inspection of lines 803-828):

* weeks = ISO W-SUN periods of the row dates, sorted;
* moving-block bootstrap: repeatedly draw a start week uniformly, take
  `block_weeks` consecutive weeks (circular), append ALL rows of each week
  in frame order, until >= n rows; truncate the row list at exactly n rows
  (the final week may be partially included);
* per-replicate statistic delta* = AUC_arm1* - AUC_arm2* on the resampled
  rows (paired: the SAME row multiset drives both arms);
* percentile CI = np.quantile(deltas, [0.025, 0.975]).

Sign convention used throughout this module: delta = candidate - reference
(a refutation test has H1: delta < 0).

Fast path: an AUC on a week-multiset sample with per-row multiplicities m is
    AUC = sum_{i in pos, j in neg} m_i m_j I_ij / (n_pos_sample * n_neg_sample)
with I_ij = 1[s_i > s_j] + 0.5*1[s_i == s_j] (sklearn-compatible tie
handling; duplicated rows therefore contribute 0.5 against themselves across
classes only, which cannot happen, and identical-class duplicates do not
enter the numerator).  With m = k[week(i)] + e_i (k = full-week
multiplicities, e = extra partial-week copy) this is a quadratic form in k
plus linear corrections for the partial week, all precomputed per trial.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np

RESULTS_DIR = Path(__file__).resolve().parent / "results"
BLOCK_WEEKS = 4          # frozen backend default (block_weeks: int = 4)
ALPHA_GRID = (0.10, 0.05, 0.025, 0.01)

# --------------------------------------------------------------------------
# Basic statistics helpers
# --------------------------------------------------------------------------


def auc_pairwise(scores_pos: np.ndarray, scores_neg: np.ndarray) -> float:
    """AUC with sklearn-compatible 0.5 tie handling (pos vs neg arrays)."""
    gt = scores_pos[:, None] > scores_neg[None, :]
    eq = scores_pos[:, None] == scores_neg[None, :]
    return float((gt + 0.5 * eq).mean())


def norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def holm_step_down(pvals: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """Holm step-down; returns boolean rejection mask."""
    p = np.asarray(pvals, dtype=float)
    m = p.size
    order = np.argsort(p, kind="stable")
    reject = np.zeros(m, dtype=bool)
    for rank, idx in enumerate(order):
        if p[idx] <= alpha / (m - rank):
            reject[idx] = True
        else:
            break
    return reject


def clopper_pearson(k: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    from scipy.stats import beta
    lo = 0.0 if k == 0 else float(beta.ppf((1 - conf) / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - (1 - conf) / 2, k + 1, n - k))
    return lo, hi


def liberal_p(k: int, n: int, p0: float) -> float:
    """One-sided exact binomial p-value for H1: true rate > p0."""
    from scipy.stats import binom
    return float(binom.sf(k - 1, n, p0))


def two_sided_prop_test(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided Fisher exact test on two rejection counts."""
    from scipy.stats import fisher_exact
    table = [[k1, n1 - k1], [k2, n2 - k2]]
    return float(fisher_exact(table, alternative="two-sided").pvalue)


# --------------------------------------------------------------------------
# Trial statistics (fast quadratic-form aggregation)
# --------------------------------------------------------------------------


class TrialStats:
    """Precomputed pair-count structures for one simulated trial.

    Row layout: week-major frame order (all rows of week 0 first, ...),
    matching the frozen backend's `np.flatnonzero(weeks == week)` order for
    a week-major frame.
    """

    def __init__(self, y, sA, sB, week_id, W, week_sizes):
        self.y = np.asarray(y, dtype=np.int64)
        self.sA = np.asarray(sA, dtype=np.float64)
        self.sB = np.asarray(sB, dtype=np.float64)
        self.week_id = np.asarray(week_id, dtype=np.int64)
        self.W = int(W)
        self.week_sizes = np.asarray(week_sizes, dtype=np.int64)
        pos = self.y == 1
        self.pos_idx = np.flatnonzero(pos)
        self.neg_idx = np.flatnonzero(~pos)
        self.pw = self.week_id[self.pos_idx]          # pos week per row
        self.nw = self.week_id[self.neg_idx]          # neg week per row
        self.n_pos = int(self.pos_idx.size)
        self.n_neg = int(self.neg_idx.size)
        self.p_w = np.bincount(self.pw, minlength=self.W).astype(np.float64)
        self.q_w = np.bincount(self.nw, minlength=self.W).astype(np.float64)

        # Pair-comparison matrices (pos x neg) with 0.5 tie handling.
        # Same-arm matrices must compare pos and neg rows of the SAME arm.
        self.G_A = self._gmat(self.sA, self.sA)
        self.G_B = self._gmat(self.sB, self.sB)
        self.C_A = self._cmat(self.G_A)
        self.C_B = self._cmat(self.G_B)
        # Cross-arm matrices for the sign-flip method.
        self.G_AB = self._gmat(self.sA, self.sB)
        self.G_BA = self._gmat(self.sB, self.sA)
        self.C_AB = self._cmat(self.G_AB)
        self.C_BA = self._cmat(self.G_BA)
        # Full-sample AUCs and delta (float64 accumulation for exactness).
        self.auc_A = float(np.sum(self.G_A, dtype=np.float64) / self.G_A.size)
        self.auc_B = float(np.sum(self.G_B, dtype=np.float64) / self.G_B.size)
        self.delta_hat = self.auc_A - self.auc_B
        # Sign-flip linear form: delta_flip(s) = s . g / (2 n_pos n_neg).
        U = np.einsum("ij->i", self.C_A + self.C_AB - self.C_BA - self.C_B)
        V = np.einsum("ij->j", self.C_A - self.C_AB + self.C_BA - self.C_B)
        self.g = (U + V).astype(np.float64)
        self.pair_total = float(self.n_pos * self.n_neg)
        # Frame-order row lists per week (needed by corrections + reference).
        self._week_rows = [np.flatnonzero(self.week_id == w) for w in range(self.W)]
        # Partial-week correction tables (per arm), indexed [week', t, w].
        maxsz = int(self.week_sizes.max())
        self.corr = {}
        self.pextra = np.zeros((self.W, maxsz + 1), dtype=np.int64)
        self.qextra = np.zeros((self.W, maxsz + 1), dtype=np.int64)
        self._build_corrections()

    def _gmat(self, sp, sn=None):
        """(n_pos x n_neg) comparison matrix of score vector sp vs sn."""
        sn = self.sB if sn is None else sn
        p = sp[self.pos_idx]
        n = sn[self.neg_idx]
        out = (p[:, None] > n[None, :]).astype(np.float32)
        out += 0.5 * (p[:, None] == n[None, :]).astype(np.float32)
        return out

    def _cmat(self, G):
        idx = (self.pw[:, None] * self.W + self.nw[None, :]).ravel()
        return np.bincount(idx, weights=G.ravel().astype(np.float64),
                           minlength=self.W * self.W).reshape(self.W, self.W)

    def _build_corrections(self):
        """Correction tables for partial-week truncation.

        For partial week w' taking its first t rows (frame order):
          A[w', t, w] = sum_{i in pos, week w} sum_{j in neg cap first t} I_ij
          B[w', t, w] = sum_{i in pos cap first t} sum_{j in neg, week w} I_ij
          C[w', t]    = sum_{i in pos cap} sum_{j in neg cap} I_ij
        Then for multiplicities m = k + e (e on first t rows of w'):
          numer = k^T C_full k + A[w'].T k + B[w'].T k + C[w']  (per arm)
        """
        maxsz = int(self.week_sizes.max())
        shapes = (self.W, maxsz + 1, self.W)
        for arm in ("A", "B"):
            self.corr[arm] = {
                "A": np.zeros(shapes, dtype=np.float64),
                "B": np.zeros(shapes, dtype=np.float64),
                "C": np.zeros((self.W, maxsz + 1), dtype=np.float64),
            }
        G_by_arm = {"A": self.G_A, "B": self.G_B}
        # Global index arrays for pos/neg rows in frame order.
        pos_by_week = {w: self.pos_idx[self.pw == w] for w in range(self.W)}
        neg_by_week = {w: self.neg_idx[self.nw == w] for w in range(self.W)}
        pos_rank_in_week = np.zeros(self.n_pos, dtype=np.int64)
        neg_rank_in_week = np.zeros(self.n_neg, dtype=np.int64)
        for w in range(self.W):
            rows = self._week_rows[w]
            pmask = self.y[rows] == 1
            pos_rows = rows[pmask]
            neg_rows = rows[~pmask]
            # rank within week in frame order
            pos_gpos = np.searchsorted(self.pos_idx, pos_rows)
            neg_gpos = np.searchsorted(self.neg_idx, neg_rows)
            pos_rank_in_week[pos_gpos] = np.arange(pos_rows.size)
            neg_rank_in_week[neg_gpos] = np.arange(neg_rows.size)
            sz = rows.size
            self.pextra[w, :sz + 1] = np.concatenate(
                [[0], np.cumsum(self.y[rows])]).astype(np.int64)
            self.qextra[w, :sz + 1] = np.concatenate(
                [[0], np.cumsum(1 - self.y[rows])]).astype(np.int64)
            if sz == 0:
                continue
            # row positions of this week among pos/neg global arrays
            p_gpos = np.flatnonzero(self.pw == w)   # into self.pos_idx
            n_gpos = np.flatnonzero(self.nw == w)
            ts = np.arange(1, sz + 1)                # t values 1..sz
            pe = self.pextra[w, ts]                  # pos rows in first t
            qe = self.qextra[w, ts]                  # neg rows in first t
            pe_idx = np.minimum(np.maximum(pe - 1, 0), sz - 1)
            qe_idx = np.minimum(np.maximum(qe - 1, 0), sz - 1)
            # arm-independent ordering + index arrays, hoisted out of the
            # per-arm loop (identical for every comparison matrix)
            rows_ord = (p_gpos[np.argsort(pos_rank_in_week[p_gpos])]
                        if p_gpos.size else None)
            cols = (n_gpos[np.argsort(neg_rank_in_week[n_gpos])]
                    if n_gpos.size else None)
            idx_a = self.pw[:, None] * sz + np.arange(sz)[None, :]
            idx_b = np.arange(sz)[:, None] * self.W + self.nw[None, :]
            for arm, G in G_by_arm.items():
                corr = self.corr[arm]
                # A-coef: cumulative over neg rows of w' (frame order), then
                # aggregate over pos weeks.  Only neg rows inside the first
                # t rows of w' participate -> column index qe[t] (zeroed
                # where qe[t] == 0).  Vectorized over all t with a single
                # bincount over (pos-week, t) pairs.
                if cols is not None:
                    cum = np.cumsum(G[:, cols], axis=1)      # n_pos x sz
                    M2 = np.where(qe > 0, cum[:, qe_idx], 0.0)  # n_pos x sz
                    corr["A"][w, ts, :] = np.bincount(
                        idx_a.ravel(), weights=M2.ravel(),
                        minlength=self.W * sz).reshape(self.W, sz).T
                # B-coef: cumulative over pos rows of w', aggregate neg weeks.
                if rows_ord is not None:
                    cum2 = np.cumsum(G[rows_ord, :], axis=0)  # sz x n_neg
                    M3 = np.where((pe > 0)[:, None],
                                  cum2[pe_idx, :], 0.0)      # sz x n_neg
                    corr["B"][w, ts, :] = np.bincount(
                        idx_b.ravel(), weights=M3.ravel(),
                        minlength=self.W * sz).reshape(sz, self.W)
                # C: double-cumsum of the w' x w' submatrix, indexed by the
                # pos/neg counts inside the first t rows.
                if rows_ord is not None and cols is not None:
                    sub = G[np.ix_(rows_ord, cols)]
                    c2 = np.cumsum(np.cumsum(sub, axis=0), axis=1)
                    ok = (pe > 0) & (qe > 0)
                    corr["C"][w, ts] = np.where(ok, c2[pe_idx, qe_idx], 0.0)

    # -- bootstrap ---------------------------------------------------------

    def bootstrap_deltas(self, K, wp, t):
        """delta* for each replicate given multiplicity/ partial-week spec."""
        K = np.asarray(K, dtype=np.float64)
        den_full_p = K @ self.p_w
        den_full_q = K @ self.q_w
        pex = self.pextra[wp, t]
        qex = self.qextra[wp, t]
        den = (den_full_p + pex) * (den_full_q + qex)
        out = np.empty(K.shape[0], dtype=np.float64)
        for arm, C in (("A", self.C_A), ("B", self.C_B)):
            quad = np.einsum("bi,ij,bj->b", K, C, K, optimize=True)
            corr = self.corr[arm]
            Arow = corr["A"][wp, t, :]        # (B, W)
            Brow = corr["B"][wp, t, :]
            lin = np.einsum("bi,bi->b", K, Arow + Brow)
            cst = corr["C"][wp, t]
            numer = quad + lin + cst
            auc = numer / den
            if arm == "A":
                out = auc
            else:
                out = out - auc
        return out

    def sign_flip_deltas(self, S):
        """delta under week-level arm flips; S in {+1,-1}^{(M, W)}."""
        return (S @ self.g) / (2.0 * self.pair_total)


# --------------------------------------------------------------------------
# Moving-block week bootstrap draws (exact harness semantics, vectorized)
# --------------------------------------------------------------------------


def draw_week_multiplicities(week_sizes, n, B, rng, block_weeks=BLOCK_WEEKS):
    """Vectorized replica of the frozen backend's block-sampling loop.

    Returns K (B, W) full-week multiplicities and, for each replicate, the
    partially consumed week wp and its row cut t (first t rows of that week
    in frame order enter with one extra copy).  Statistical scheme is
    identical to the backend loop; RNG batching differs (documented in the
    report; the sequential loop is reproduced separately for SIM-5
    equivalence testing).
    """
    sizes = np.asarray(week_sizes, dtype=np.int64)
    W = sizes.size
    n = int(n)
    minsz = max(1, int(sizes.min()))
    max_pos = int(math.ceil(n / (block_weeks * minsz))) + 2
    starts = rng.integers(0, W, size=(B, max_pos))
    offs = np.arange(block_weeks)
    widx = (starts[:, :, None] + offs) % W               # (B, nb, bw)
    wsz = sizes[widx]                                     # (B, nb, bw)
    flat_w = widx.reshape(B, -1)
    flat_s = wsz.reshape(B, -1)
    csum = np.cumsum(flat_s, axis=1)
    cut_pos = (csum >= n).argmax(axis=1)                  # first week reaching n
    pos_idx = np.arange(flat_s.shape[1])
    full_mask = pos_idx[None, :] < cut_pos[:, None]
    # accumulate full-week counts via bincount (equivalent to, but much
    # faster than, np.add.at on (replicate, week) pairs)
    rows_idx = np.repeat(np.arange(B), flat_s.shape[1])
    pairs = (rows_idx * W + flat_w.ravel())[full_mask.ravel()]
    K = np.bincount(pairs, minlength=B * W).reshape(B, W).astype(np.int64)
    prev = np.where(cut_pos > 0, csum[np.arange(B), np.maximum(cut_pos - 1, 0)], 0)
    t = (n - prev).astype(np.int64)
    wp = flat_w[np.arange(B), cut_pos]
    return K, wp, t


def sequential_draw_week_multiplicities(week_sizes, n, rng, block_weeks=BLOCK_WEEKS):
    """Literal sequential replica of the backend loop (one replicate).

    Mirrors demand_zone_study_v1.block_bootstrap_delta RNG consumption:
    one rng.integers(0, W) per block, weeks appended in block order,
    truncate the flattened row list at n.
    """
    sizes = np.asarray(week_sizes, dtype=np.int64)
    W = sizes.size
    occ: dict[int, int] = {}
    appended: list[int] = []
    total = 0
    while total < n:
        start = int(rng.integers(0, W))
        for offset in range(block_weeks):
            w = (start + offset) % W
            appended.append(w)
            total += int(sizes[w])
    K = np.zeros(W, dtype=np.int64)
    run = 0
    wp = -1
    t = 0
    for w in appended:
        sz = int(sizes[w])
        if run + sz <= n:
            K[w] += 1
            run += sz
        elif run < n:
            wp = w
            t = n - run
            run = n
        else:
            break
    return K, wp, t


# --------------------------------------------------------------------------
# DGPs
# --------------------------------------------------------------------------


def make_trial(W, events_per_week, pi, rho, theta_A, theta_B, rng,
               skewed=False, sizes=None):
    """One paired-score trial.

    y_i ~ Bernoulli(pi_w); scores
        sX_i = theta_X * (2 y_i - 1) + u_week + d_i + eps_Xi,
    with u_week ~ N(0, rho) (common market-week effect), d_i ~ N(0, (1-rho)/2)
    shared event difficulty, eps_Xi ~ N(0, (1-rho)/2) arm noise.
    Total score variance = 1, so population AUC_X = Phi(sqrt(2) theta_X) and
    true delta = Phi(sqrt(2) theta_A) - Phi(sqrt(2) theta_B).
    """
    if skewed:
        sizes = np.maximum(5, np.round(rng.lognormal(
            math.log(events_per_week), 0.5, size=W))).astype(np.int64)
        pi_w = np.clip(rng.normal(pi, 0.10, size=W), 0.03, 0.60)
    else:
        if sizes is None:
            sizes = np.full(W, events_per_week, dtype=np.int64)
        else:
            sizes = np.asarray(sizes, dtype=np.int64)
        pi_w = np.full(W, float(pi))
    n = int(sizes.sum())
    week_id = np.repeat(np.arange(W), sizes)
    u = math.sqrt(rho) * rng.standard_normal(W)
    y = (rng.random(n) < pi_w[week_id]).astype(np.int64)
    d = math.sqrt((1 - rho) / 2) * rng.standard_normal(n)
    eA = math.sqrt((1 - rho) / 2) * rng.standard_normal(n)
    eB = math.sqrt((1 - rho) / 2) * rng.standard_normal(n)
    t = 2 * y - 1
    base = u[week_id] + d
    sA = theta_A * t + base + eA
    sB = theta_B * t + base + eB
    return TrialStats(y, sA, sB, week_id, W, sizes)


def make_correlated_members(W, events_per_week, pi, rho_member, thetas,
                            rng):
    """m members sharing one event grid (labels/weeks) and a shared week
    factor g_w; member j week factor = sqrt(rho) g + sqrt(1-rho) h_j.
    thetas: list of (theta_A_j, theta_B_j)."""
    sizes = np.full(W, events_per_week, dtype=np.int64)
    n = int(sizes.sum())
    week_id = np.repeat(np.arange(W), sizes)
    y = (rng.random(n) < pi).astype(np.int64)
    g = rng.standard_normal(W)
    members = []
    for (thA, thB) in thetas:
        h = rng.standard_normal(W)
        u = math.sqrt(rho_member) * g + math.sqrt(1 - rho_member) * h
        d = math.sqrt((1 - rho_member) / 2) * rng.standard_normal(n)
        eA = math.sqrt((1 - rho_member) / 2) * rng.standard_normal(n)
        eB = math.sqrt((1 - rho_member) / 2) * rng.standard_normal(n)
        t = 2 * y - 1
        base = u[week_id] + d
        sA = thA * t + base + eA
        sB = thB * t + base + eB
        members.append(TrialStats(y, sA, sB, week_id, W, sizes))
    return members


# --------------------------------------------------------------------------
# Candidate p-value methods (one test each)
# --------------------------------------------------------------------------


def run_methods(stats: TrialStats, B, M, rng):
    """Returns dict with p_a, p_b, p_c, ci, se from one trial."""
    K, wp, t = draw_week_multiplicities(stats.week_sizes, stats.n_pos + stats.n_neg,
                                        B, rng)
    deltas = stats.bootstrap_deltas(K, wp, t)
    deltas = deltas[np.isfinite(deltas)]
    n_valid = deltas.size
    p_a = (int((deltas >= 0).sum()) + 1) / (n_valid + 1)
    ci_lo, ci_hi = np.quantile(deltas, [0.025, 0.975])
    se = float(np.std(deltas, ddof=1))
    z = stats.delta_hat / se if se > 0 else math.inf
    p_c = norm_cdf(z)
    S = rng.integers(0, 2, size=(M, stats.W)) * 2 - 1
    flips = stats.sign_flip_deltas(S)
    p_b = (int((flips <= stats.delta_hat).sum()) + 1) / (M + 1)
    return {
        "p_a": p_a, "p_b": p_b, "p_c": p_c,
        "ci_lo": float(ci_lo), "ci_hi": float(ci_hi), "se": se,
        "delta_hat": float(stats.delta_hat), "n_boot_valid": int(n_valid),
    }


def run_unpaired(stats: TrialStats, B, rng):
    """Unpaired control: independent week resamples for the two arms.

    Returns dict mirroring `run_methods` (p_a, ci, se) computed from the
    unpaired deltas, for the SIM-5 divergence check.
    """
    n = stats.n_pos + stats.n_neg
    K1, wp1, t1 = draw_week_multiplicities(stats.week_sizes, n, B, rng)
    K2, wp2, t2 = draw_week_multiplicities(stats.week_sizes, n, B, rng)

    def arm_auc(C, K, wp, t):
        quad = np.einsum("bi,ij,bj->b", K, C, K, optimize=True)
        corr_key = "A" if C is stats.C_A else "B"
        corr = stats.corr[corr_key]
        lin = np.einsum("bi,bi->b", K, corr["A"][wp, t, :] + corr["B"][wp, t, :])
        cst = corr["C"][wp, t]
        den = ((K @ stats.p_w + stats.pextra[wp, t])
               * (K @ stats.q_w + stats.qextra[wp, t]))
        return (quad + lin + cst) / den

    deltas = arm_auc(stats.C_A, K1, wp1, t1) - arm_auc(stats.C_B, K2, wp2, t2)
    deltas = deltas[np.isfinite(deltas)]
    ci_lo, ci_hi = np.quantile(deltas, [0.025, 0.975])
    return {"p_a": (int((deltas >= 0).sum()) + 1) / (deltas.size + 1),
            "ci_lo": float(ci_lo), "ci_hi": float(ci_hi),
            "se": float(np.std(deltas, ddof=1)),
            "n_valid": int(deltas.size),
            "ci_width": float(ci_hi - ci_lo)}


# --------------------------------------------------------------------------
# Slow reference implementations (independent code paths for validation)
# --------------------------------------------------------------------------


def reference_bootstrap_deltas(stats: TrialStats, B, rng, block_weeks=BLOCK_WEEKS):
    """Slow, literal backend-semantics deltas (own RNG draws)."""
    from sklearn.metrics import roc_auc_score
    y = stats.y
    n = y.size
    deltas = []
    for _ in range(B):
        K, wp, t = sequential_draw_week_multiplicities(
            stats.week_sizes, n, rng, block_weeks)
        idx = []
        for w in range(stats.W):
            if K[w]:
                idx.append(np.tile(stats._week_rows[w], int(K[w])))
        if wp >= 0 and t > 0:
            idx.append(stats._week_rows[wp][:t])
        sel = np.concatenate(idx) if idx else np.array([], dtype=int)
        if sel.size != n:
            raise RuntimeError("reference resample size mismatch")
        lab = y[sel]
        if np.unique(lab).size < 2:
            continue
        a = roc_auc_score(lab, stats.sA[sel])
        b = roc_auc_score(lab, stats.sB[sel])
        deltas.append(a - b)
    return np.array(deltas)


def reference_sign_flip_deltas(stats: TrialStats, S):
    """Slow brute-force AUC recomputation for flip vectors S (M, W)."""
    from sklearn.metrics import roc_auc_score
    y = stats.y
    out = []
    for s in S:
        useA = s[stats.week_id] > 0
        sA = np.where(useA, stats.sA, stats.sB)
        sB = np.where(useA, stats.sB, stats.sA)
        out.append(roc_auc_score(y, sA) - roc_auc_score(y, sB))
    return np.array(out)


# --------------------------------------------------------------------------
# SIM-4: freeze-time feasibility (deterministic)
# --------------------------------------------------------------------------


def sim4_feasibility(config_draft_path: Path) -> dict:
    cfg = json.loads(config_draft_path.read_text(encoding="utf-8"))
    limits = {"n_boot_grid": [100, 2000]}  # CONFIG_LIMITS in recipe_harness.py:53
    # Family member bounds under the draft's caps.
    cap = None
    for key in ("max_per_direction",):
        if key in cfg.get("proposal_generation", {}):
            cap = cfg["proposal_generation"][key]
        elif key in cfg:
            cap = cfg[key]
    if cap is None:
        # search nested
        def find(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    if k == "max_per_direction":
                        return v
                    got = find(v)
                    if got is not None:
                        return got
            return None
        cap = find(cfg)
    cells = {"regime_split_analysis": 2, "target_horizon_robustness": 3,
             "purge_sensitivity_probe": 3, "complexity_reduction_check": 1}
    families = {prim: cells[prim] * int(cap) for prim in cells}
    n_boot_cfg = None
    def find_boot(d):
        if isinstance(d, dict):
            for k, v in d.items():
                if k == "n_boot" and isinstance(v, int):
                    return v
                got = find_boot(v)
                if got is not None:
                    return got
        return None
    n_boot_cfg = find_boot(cfg)
    rows = []
    feasible_all = True
    for fam, m in families.items():
        b_min = 20 * m - 1
        ok_1000 = (1000 + 1) >= 20 * m
        ok_cfg = None if n_boot_cfg is None else (n_boot_cfg + 1) >= 20 * m
        feasible_all &= bool(ok_1000)
        rows.append({"family": fam, "m_bound": m,
                     "B_min_required": b_min, "B1000_ok": ok_1000,
                     "config_n_boot": n_boot_cfg, "config_n_boot_ok": ok_cfg})
    # Unbound contingency (no direction cap): m could reach 90 rungs total.
    unbound = {"m": 90, "B_min_required": 20 * 90 - 1, "B1000_ok": False,
               "note": "requires family cap in config or n_boot >= 1799"}
    return {
        "config_draft": str(config_draft_path),
        "max_per_direction": cap,
        "n_boot_in_draft": n_boot_cfg,
        "grid": limits,
        "families": rows,
        "unbound_contingency": unbound,
        "verdict_B1000": "FEASIBLE for all capped families"
        if feasible_all else "INFEASIBLE",
    }


# --------------------------------------------------------------------------
# Self-tests (fast paths vs independent references)
# --------------------------------------------------------------------------


def selftest() -> dict:
    from scipy.stats import norm
    out = {"passed": True, "checks": {}}

    def check(name, ok, detail):
        out["checks"][name] = {"ok": bool(ok), "detail": detail}
        if not ok:
            out["passed"] = False

    rng = np.random.default_rng(7)
    W, sz, pi = 24, 12, 0.3
    stats = make_trial(W, sz, pi, 0.5, 0.35, 0.35, rng)
    n = stats.y.size

    # (a) quadratic AUC vs sklearn on the full sample
    from sklearn.metrics import roc_auc_score
    auc_sk = roc_auc_score(stats.y, stats.sA)
    check("auc_quadratic_vs_sklearn", abs(auc_sk - stats.auc_A) < 1e-12,
          f"{auc_sk:.15f} vs {stats.auc_A:.15f}")

    # (b) fast bootstrap deltas vs slow reference on the SAME draws
    rng1 = np.random.default_rng(11)
    K, wp, t = draw_week_multiplicities(stats.week_sizes, n, 50, rng1)
    fast = stats.bootstrap_deltas(K, wp, t)
    rng2 = np.random.default_rng(11)
    # replay the same multiplicity draws through the slow path
    from sklearn.metrics import roc_auc_score as ras
    slow = []
    for b in range(50):
        idx = []
        for w in range(W):
            if K[b, w]:
                idx.append(np.tile(stats._week_rows[w], int(K[b, w])))
        if t[b] > 0:
            idx.append(stats._week_rows[wp[b]][:t[b]])
        sel = np.concatenate(idx)
        lab = stats.y[sel]
        slow.append(ras(lab, stats.sA[sel]) - ras(lab, stats.sB[sel]))
    slow = np.array(slow)
    check("fast_vs_slow_bootstrap", np.max(np.abs(fast - slow)) < 1e-9,
          f"max|diff| = {np.max(np.abs(fast - slow)):.3e}")

    # (c) sequential draws reproduce the vectorized scheme's sizes
    rng3 = np.random.default_rng(13)
    Ks, wps, ts = sequential_draw_week_multiplicities(stats.week_sizes, n, rng3)
    check("sequential_draw_sizes",
          int(Ks @ stats.week_sizes) + (ts if wps >= 0 else 0) == n,
          f"rows = {int(Ks @ stats.week_sizes) + (ts if wps >= 0 else 0)} vs {n}")

    # (d) sign-flip linear form vs brute-force AUC recomputation
    S = rng.integers(0, 2, size=(25, W)) * 2 - 1
    lin = stats.sign_flip_deltas(S)
    brute = reference_sign_flip_deltas(stats, S)
    check("signflip_linear_vs_brute", np.max(np.abs(lin - brute)) < 1e-9,
          f"max|diff| = {np.max(np.abs(lin - brute)):.3e}")

    # (e) sign-flip identity equals delta_hat
    check("signflip_identity", abs(stats.sign_flip_deltas(np.ones((1, W), int))[0]
                                   - stats.delta_hat) < 1e-12,
          f"{stats.sign_flip_deltas(np.ones((1, W), int))[0]:.12f} vs "
          f"{stats.delta_hat:.12f}")

    # (f) Holm fixture (hand-computed)
    p = np.array([0.001, 0.012, 0.03, 0.2])
    rej = holm_step_down(p, 0.05)
    # thresholds: .0125, .0167, .025, .05 -> reject first two only
    check("holm_fixture", rej.tolist() == [True, True, False, False],
          f"rejects = {rej.tolist()}")

    # (h) fast bootstrap deltas vs slow reference on a VARYING-WEEK-SIZE
    # fixture (covers the partial-week corrections with sz < maxsz)
    rngh = np.random.default_rng(17)
    sizes_h = np.array([7, 25, 12, 19, 9, 23, 14, 11, 21, 8, 26, 15, 10,
                        18, 13], dtype=np.int64)
    statsh = make_trial(15, 0, 0.3, 0.5, 0.35, 0.35, rngh, sizes=sizes_h)
    Kh, wph, th = draw_week_multiplicities(statsh.week_sizes,
                                           statsh.y.size, 100, rngh)
    fasth = statsh.bootstrap_deltas(Kh, wph, th)
    slowh = []
    from sklearn.metrics import roc_auc_score as rash
    for b in range(100):
        idx = []
        for w in range(15):
            if Kh[b, w]:
                idx.append(np.tile(statsh._week_rows[w], int(Kh[b, w])))
        if th[b] > 0:
            idx.append(statsh._week_rows[wph[b]][:th[b]])
        sel = np.concatenate(idx)
        lab = statsh.y[sel]
        slowh.append(rash(lab, statsh.sA[sel]) - rash(lab, statsh.sB[sel]))
    slowh = np.array(slowh)
    check("fast_vs_slow_bootstrap_varying_sizes",
          np.max(np.abs(fasth - slowh)) < 1e-9,
          f"max|diff| = {np.max(np.abs(fasth - slowh)):.3e}")

    # (i) vectorized multiplicity draw == literal old add.at accumulation
    # on identical RNG state (bincount refactor equivalence)
    rngi = np.random.default_rng(23)
    sizes_i = np.array([10, 14, 9, 12, 11, 13, 8, 15], dtype=np.int64)
    Ki, wpi, ti = draw_week_multiplicities(sizes_i, 100, 60, rngi)
    rngi2 = np.random.default_rng(23)
    starts = rngi2.integers(0, 8, size=(60, math.ceil(100 / (4 * 8)) + 2))
    offs = np.arange(4)
    widx2 = (starts[:, :, None] + offs) % 8
    wsz2 = sizes_i[widx2]
    fw2 = widx2.reshape(60, -1)
    fs2 = wsz2.reshape(60, -1)
    cs2 = np.cumsum(fs2, axis=1)
    cp2 = (cs2 >= 100).argmax(axis=1)
    pi2 = np.arange(fs2.shape[1])
    fm2 = pi2[None, :] < cp2[:, None]
    K2 = np.zeros((60, 8), dtype=np.int64)
    np.add.at(K2, (np.repeat(np.arange(60), fs2.shape[1]), fw2.ravel()),
              fm2.astype(np.int64).ravel())
    check("draw_bincount_vs_addat", np.array_equal(Ki, K2),
          f"K equal = {np.array_equal(Ki, K2)}")

    # (g) frozen-backend equivalence: our sequential path vs the real
    # block_bootstrap_delta on a fixture (same seed).
    try:
        backend = _load_frozen_backend()
        import pandas as pd
        rngf = np.random.default_rng(21)
        statf = make_trial(30, 15, 0.28, 0.5, 0.35, 0.33, rngf)
        dates = pd.to_datetime("2023-01-01") + pd.to_timedelta(
            np.repeat(np.arange(30), 15) * 7, unit="D")
        frame = pd.DataFrame({"date": dates, "label": statf.y,
                              "cand": statf.sA, "ref": statf.sB})
        res = backend.block_bootstrap_delta(frame, "cand", "ref",
                                            n_boot=200, seed=99)
        # our sequential replica with the same seed (same RNG consumption:
        # one integer draw per block) -> identical draws, delta = AUC_cand -
        # AUC_ref = stats A - stats B.
        seq_rng = np.random.default_rng(99)
        deltas = []
        from sklearn.metrics import roc_auc_score as ras2
        for _ in range(200):
            K, wp, t = sequential_draw_week_multiplicities(
                statf.week_sizes, statf.y.size, seq_rng)
            idx = []
            for w in range(30):
                if K[w]:
                    idx.append(np.tile(statf._week_rows[w], int(K[w])))
            if wp >= 0 and t > 0:
                idx.append(statf._week_rows[wp][:t])
            sel = np.concatenate(idx)
            lab = statf.y[sel]
            if np.unique(lab).size < 2:
                continue
            deltas.append(ras2(lab, statf.sA[sel]) - ras2(lab, statf.sB[sel]))
        deltas = np.array(deltas)
        ci_mine = np.quantile(deltas, [0.025, 0.975])
        base_mine = float(ras2(statf.y, statf.sA) - ras2(statf.y, statf.sB))
        check("frozen_backend_base_delta",
              abs(base_mine - res["delta_auc"]) < 1e-12,
              f"{base_mine:.12f} vs {res['delta_auc']:.12f}")
        check("frozen_backend_ci",
              max(abs(ci_mine[0] - res["ci_95"][0]),
                  abs(ci_mine[1] - res["ci_95"][1])) < 1e-9,
              f"{ci_mine.tolist()} vs {res['ci_95']}")
        check("frozen_backend_n_valid",
              int(deltas.size) == res["n_boot_valid"],
              f"{deltas.size} vs {res['n_boot_valid']}")
    except Exception as exc:  # noqa: BLE001 - report, do not swallow silently
        check("frozen_backend_equivalence", False, f"ERROR: {exc!r}")
    return out


def _load_frozen_backend():
    """Read-only import of the frozen study backend (harness does the same)."""
    import importlib.util
    import sys
    root = Path(__file__).resolve().parents[1]
    path = root / "study_files" / "backend" / "demand_zone_study_v1.py"
    spec = importlib.util.spec_from_file_location("frozen_study_v1_sim", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
