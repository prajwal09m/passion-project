#!/usr/bin/env python3
"""SCRATCH — independent adversarial review computations (2026-10-13).

Clearly identified scratch work supporting
stat_validation_h10/D2_AI_INDEPENDENT_STATISTICAL_REVIEW.md.
READ-ONLY with respect to all evidence; writes only inside this directory.

Usage:
  py -3 -X utf8 independent_checks.py fast     # audit + MC resolution + calibration
  py -3 -X utf8 independent_checks.py sym      # probe: exchangeable null (N=1000)
  py -3 -X utf8 independent_checks.py affine16 # probe: scale asymmetry, equal AUC
  py -3 -X utf8 independent_checks.py hetero   # probe: heteroskedastic, equal AUC (calibrated)
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STAT = HERE.parent
RES = STAT / "results"
ROOT = STAT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(STAT))

ALPHA = 0.05
M_FLIPS = 1000
WEEKS, SZ, PI = 24, 15, 0.18
N_ROWS = WEEKS * SZ
U_COEF, D_COEF = 0.5, 0.4
SEED0 = 20261013


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def manifest_hashes() -> dict[str, str]:
    lines = (STAT / "review_submission" / "BUNDLE_MANIFEST.txt").read_text("utf-8").splitlines()
    out = {}
    for i, l in enumerate(lines[:-1]):
        n, h = l.strip(), lines[i + 1].strip()
        if n and len(h) == 64 and all(c in "0123456789abcdef" for c in h):
            out[n] = sha(STAT / n)
    return out


# ---------------------------------------------------------------- fast parts
def naive_holm_rejects(pvals, alpha=0.05):
    """Textbook Holm rejection mask, written independently (slow path)."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: (pvals[i], i))
    rej = [False] * m
    for rank, i in enumerate(order):
        if pvals[i] <= alpha / (m - rank):
            rej[i] = True
        else:
            break
    return rej


def audit_pre_review() -> dict:
    """Independent slow-path re-derivations of material numbers."""
    out = {}
    # SIM-1: (b) rates straight from raw npz (fresh, minimal code)
    cells = ["i_balanced_symmetric", "ii_skewed_sizes_rates", "iii_rho0",
             "iii_rho50", "iii_rho90", "iv_regime_small_n"]
    rb = []
    for c in cells:
        z = np.load(RES / f"sim1_{c}.npz")
        rb.append(float(np.mean(z["p_b"] <= 0.05)))
    out["sim1_pb_mean_six_cells"] = round(float(np.mean(rb)), 4)
    out["sim1_pb_cell_i"] = round(rb[0], 4)
    out["sim1_pb_cell_iii50"] = round(rb[3], 4)
    out["sim1_claim"] = 0.0498
    # SIM-2: slow per-campaign Holm on two decision-relevant cells
    z23 = np.load(RES / "sim2_rho03_pvalues.npz")
    k4 = sum(bool(naive_holm_rejects(list(z23["pb"][c, :4, 1]), ALPHA).count(True))
             for c in range(2000))
    out["sim2_rho03_m4_b1000_pb_k"] = int(k4)
    out["sim2_claim_worst_cell_k"] = 113
    z00 = np.load(RES / "sim2_rho00_pvalues.npz")
    k24 = sum(bool(naive_holm_rejects(list(z00["pb"][c, :24, 1]), ALPHA).count(True))
              for c in range(2000))
    out["sim2_rho00_m24_b1000_pb_k"] = int(k24)
    out["sim2_rho00_m24_fwer"] = round(k24 / 2000, 4)
    # SIM-3: one cell, fresh XOR
    z1 = np.load(RES / "sim1_i_balanced_symmetric.npz")
    dis = int(np.count_nonzero((z1["p_b"] <= 0.05) ^ (z1["ci_hi"] < 0)))
    out["sim3_cell_i_pb_disagree"] = dis
    out["sim3_claim_cell_i_pb"] = 24
    # rounding explanations used by the pre-review
    out["rounding_113_over_2000"] = 113 / 2000
    out["pre_review_rounding_claim_check"] = {
        "113/2000 <= 0.057": 113 / 2000 <= 0.057,
        "131/2000 <= 0.066": 131 / 2000 <= 0.066,
    }
    return out


def mc_resolution() -> dict:
    """Exact P(reject) when the true (sharp-null) p sits at/near Holm thresholds."""
    from scipy.stats import binom
    out = {}
    for m in (1, 12, 24, 36, 50):
        t = ALPHA / m
        # reject iff (X+1)/(M+1) <= t  <=>  X <= t*(M+1) - 1
        kmax = int(math.floor(t * (M_FLIPS + 1) - 1.0 + 1e-12))
        row = {"first_holm_threshold": t, "max_rejecting_count": kmax}
        for label, p in (("p_true_half_t", t / 2), ("p_true_at_t", t),
                         ("p_true_2t", min(2 * t, 1.0))):
            row[label] = float(binom.cdf(kmax, M_FLIPS, p))
        row["attainable"] = (1.0 / (M_FLIPS + 1)) <= t
        out[f"m={m}"] = row
    return out


# ------------------------------------------------------------------- probes
def auc_pairwise(y, s):
    pos, neg = s[y == 1], s[y == 0]
    gt = pos[:, None] > neg[None, :]
    eq = pos[:, None] == neg[None, :]
    return float((gt + 0.5 * eq).mean())


def make_frame(scenario: str, rng, theta_b: float = 0.0):
    y = (rng.random(N_ROWS) < PI).astype(np.int64)
    u = rng.normal(size=WEEKS)
    d = rng.normal(size=N_ROWS)
    uw = np.repeat(u, SZ)
    base_shared = U_COEF * uw + D_COEF * d
    eps = rng.normal(size=N_ROWS)
    if scenario == "hetero":
        theta_a, sig_pos_a, sig_neg_a = 0.8, 1.0, 1.0
        sig_pos_b, sig_neg_b = 1.5, 1.0
        sig_a = theta_a * (2 * y - 1) + base_shared + np.where(y == 1, sig_pos_a, sig_neg_a) * eps
        eps_b = rng.normal(size=N_ROWS)
        sig_b = theta_b * (2 * y - 1) + base_shared + np.where(y == 1, sig_pos_b, sig_neg_b) * eps_b
    else:
        theta = 0.55
        sig_a = theta * (2 * y - 1) + base_shared + eps
        eps_b = rng.normal(size=N_ROWS)
        latent_b = theta * (2 * y - 1) + base_shared + eps_b
        sig_b = 1.6 * latent_b if scenario == "affine16" else latent_b
    week = np.repeat(np.arange(WEEKS), SZ)
    return y, sig_a, sig_b, week


def sign_flip_p(y, s_a, s_b, week, rng):
    d_hat = auc_pairwise(y, s_a) - auc_pairwise(y, s_b)
    y_pos = y == 1

    def auc_from(a2):
        p_, n_ = a2[y_pos], a2[~y_pos]
        gt = p_[:, None] > n_[None, :]
        eq = p_[:, None] == n_[None, :]
        return float((gt + 0.5 * eq).mean())

    swaps = rng.integers(0, 2, size=(M_FLIPS, WEEKS)).astype(bool)
    cnt = 0
    for row in swaps:
        mask = row[week]
        a2 = np.where(mask, s_b, s_a)
        b2 = np.where(mask, s_a, s_b)
        if auc_from(a2) - auc_from(b2) <= d_hat:
            cnt += 1
    return (cnt + 1) / (M_FLIPS + 1), d_hat


def calibrate_hetero(seed=SEED0 + 999) -> float:
    """Binary-search theta_B so E[AUC_B - AUC_A] = 0 under the hetero DGP."""
    from scipy.stats import norm
    rng = np.random.default_rng(seed)
    lo, hi = 0.0, 2.0
    n_pilot = 400

    def mean_delta(tb):
        tot = 0.0
        for _ in range(n_pilot):
            y, sa, sb, wk = make_frame("hetero", rng, theta_b=tb)
            tot += auc_pairwise(y, sb) - auc_pairwise(y, sa)
        return tot / n_pilot

    for _ in range(18):
        mid = 0.5 * (lo + hi)
        if mean_delta(mid) > 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def run_probe(scenario: str, n_trials: int = 1000, theta_b: float = 0.0) -> dict:
    from scipy.stats import beta as sp_beta, binom
    rng = np.random.default_rng(SEED0 + {"sym": 1, "affine16": 2, "hetero": 3}[scenario])
    rej = 0
    deltas = []
    ps = []
    t0 = time.time()
    # AUC validity check vs sklearn
    from sklearn.metrics import roc_auc_score
    y0, sa0, sb0, wk0 = make_frame(scenario, rng, theta_b)
    assert abs(auc_pairwise(y0, sa0) - roc_auc_score(y0, sa0)) < 1e-12
    for _ in range(n_trials):
        y, sa, sb, wk = make_frame(scenario, rng, theta_b)
        p, d_hat = sign_flip_p(y, sa, sb, wk, rng)
        ps.append(p)
        deltas.append(d_hat)
        if p <= ALPHA:
            rej += 1
    k, n = rej, n_trials
    lo = 0.0 if k == 0 else float(sp_beta.ppf(0.025, k, n - k + 1))
    hi = 1.0 if k == n else float(sp_beta.ppf(0.975, k + 1, n - k))
    return {
        "scenario": scenario, "n_trials": n, "M_flips": M_FLIPS,
        "frame": f"W={WEEKS} weeks x {SZ} rows ({N_ROWS}), pi={PI}",
        "theta_b_calibrated": theta_b if scenario == "hetero" else None,
        "rejections_at_0.05": k, "rate": k / n,
        "cp95": [lo, hi],
        "p_liberal_one_sided": float(binom.sf(k - 1, n, ALPHA)),
        "significantly_above_0.05": bool(binom.sf(k - 1, n, ALPHA) < 0.05),
        "mean_delta_hat": float(np.mean(deltas)),
        "sd_delta_hat": float(np.std(deltas, ddof=1)),
        "p_quantiles": {q: float(np.quantile(ps, q)) for q in (0.01, 0.05, 0.25, 0.5)},
        "seed": SEED0 + {"sym": 1, "affine16": 2, "hetero": 3}[scenario],
        "seconds": round(time.time() - t0, 1),
    }


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "fast"
    if mode == "fast":
        out = {"hashes_before": manifest_hashes()}
        out["audit"] = audit_pre_review()
        out["mc_resolution"] = mc_resolution()
        tb = calibrate_hetero()
        out["hetero_theta_b_calibrated"] = tb
        out["hetero_calibration_note"] = (
            "theta_B binary-searched on 400-frame pilots per step so that "
            "E[AUC_B - AUC_A] = 0 under the shared-factor DGP (pi=0.18).")
        out["hashes_after"] = manifest_hashes()
        out["evidence_unchanged"] = out["hashes_before"] == out["hashes_after"]
        (HERE / "fast_results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps({k: out[k] for k in ("audit", "mc_resolution")},
                         indent=2))
        print("hetero theta_b:", tb)
        print("evidence unchanged:", out["evidence_unchanged"])
    else:
        theta_b = 0.0
        if mode == "hetero":
            theta_b = calibrate_hetero()
            print(f"[calibrated] theta_b = {theta_b:.5f}", flush=True)
        res = run_probe(mode, theta_b=theta_b)
        (HERE / f"probe_{mode}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
