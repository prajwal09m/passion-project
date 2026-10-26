#!/usr/bin/env python3
"""SCRATCH — D2 pre-review independent recomputation (2026-10-13).

Clearly identified scratch calculation supporting
stat_validation_h10/D2_AI_PRE_REVIEW.md. READ-ONLY with respect to all
evidence: this script only reads bundles/results/source and writes
recompute_results.json inside this scratch directory.

Sections:
  A  bundle + pinned-artifact SHA-256 verification
  B  SIM-1 recomputed from raw per-trial npz
  C  SIM-3 disagreement recomputed from raw npz vs submitted sim3.json
  D  SIM-2 FWER recomputed from raw member p-value npz (own Holm)
  E  SIM-4 feasibility arithmetic + production feasibility() cross-check
  F  SIM-5 submitted numbers extracted for comparison
  G  Holm: production vs simulation vs own textbook implementation
  H  granularity-floor / p-resolution arithmetic
  I  independent type-I mini-study (own DGP, own AUC, own flip code)
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STAT = HERE.parent                      # stat_validation_h10
import sys
sys.path.insert(0, str(STAT.parent))   # repo root (autonomous_agent)
sys.path.insert(0, str(STAT))          # submitted sim code (simh10)
RES = STAT / "results"
OUT = HERE / "recompute_results.json"
T0 = time.time()
out: dict[str, object] = {}

try:
    from scipy.stats import binom, beta as sp_beta, fisher_exact
    HAVE_SCIPY = True
except Exception:                                              # pragma: no cover
    HAVE_SCIPY = False


def cp_interval(k: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    if not HAVE_SCIPY:
        raise RuntimeError("scipy required")
    lo = 0.0 if k == 0 else float(sp_beta.ppf((1 - conf) / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(sp_beta.ppf(1 - (1 - conf) / 2, k + 1, n - k))
    return lo, hi


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------- A. hashes
def section_hashes() -> dict:
    text = (STAT / "review_submission" / "BUNDLE_MANIFEST.txt").read_text("utf-8")
    claimed: dict[str, str] = {}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if s and " " not in s and "/" in s or (s and not s.startswith(("(", "#"))
                                                  and nxt.startswith(tuple("0123456789abcdef"))):
                if len(nxt) == 64 and all(c in "0123456789abcdef" for c in nxt):
                    claimed[s] = nxt
    zip_path = STAT / "H10_D2_REVIEW_SUBMISSION.zip"
    zip_sha = sha256_file(zip_path)
    import zipfile
    zf = zipfile.ZipFile(zip_path)
    zip_names = {i.filename for i in zf.infolist()}
    per_file = {}
    for name, want in claimed.items():
        entry = {"claimed": want}
        # bundle-relative (zip entry) verification
        if name in zip_names:
            got_zip = hashlib.sha256(zf.read(name)).hexdigest()
            entry["zip_sha256"] = got_zip
            entry["zip_match"] = (got_zip == want)
        # repository copy verification
        local = STAT / name
        if local.is_file():
            got_local = sha256_file(local)
            entry["repo_sha256"] = got_local
            entry["repo_match"] = (got_local == want)
        per_file[name] = entry
    # pinned artifacts claimed inside the packet (§10)
    packet_claims = {
        "autonomous_agent/MAIN AUDITS AND REFLECTIONS/HARNESS_V1_1_0_IMPLEMENTATION_PLAN_2026_10_09.md":
            "094827b0e9a5f1c1b6d0ed13c32b9e22a6ff7c76568624228e8b2cb9f738eb4e",
        "stat_validation_h10/H10_DECISION_SHEET_DRAFT.md":
            "5a62c9d08e642c7e4d4c3e56e34c74d737ddbe0298efc2dc340e148a73257159",
        "stat_validation_h10/H10_DECISION_RECORD_AWAITING_SIGNATURE.md":
            "b9db32335c93ccf5a06b764023f21b6595c2fa4a0a4dd7ccbec6f87d2e9f0a42",
        "autonomous_agent/state/campaign_config.json":
            "1e0e30b8ecd99119e3c12214aacd512167c7fb6546e7b946f9dd65d5436fea5a",
        "autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_4_CONFIG_DRAFT_2026_10_09.json":
            "307e98ab4b7207dac24bada4a438686fb859b28bec5e919e80219e249168cdcd",
        "autonomous_agent/experiment_adapter.py":
            "d80723d38183ac43e66f89566cacade141f6bfcf1463d6318414d3c3b6cc61aa",
        "stat_validation_h10/H10_SIMULATION_EVIDENCE_REPORT.md":
            "85c6ac4f21be0755671726fe1ceb0db37d645206e7183692b9ff545a8255a884",
        "stat_validation_h10/simh10.py":
            "4b7ebd5f3ffc5413247cdcedb099d493a71e3cfc01346a68c8440de9d59b51f3",
        "stat_validation_h10/run_sim.py":
            "96aa497cebb30ae38a381e361540dc68566f098b108eb26056777dcfecb3dcc1",
    }
    pins = {}
    for rel, want in packet_claims.items():
        p = STAT.parent / rel
        got = sha256_file(p) if p.is_file() else None
        pins[rel] = {"claimed": want, "actual": got, "match": got == want}
    # campaign_config.sha256 sidecar consistency
    side = (STAT.parent / "autonomous_agent/state/campaign_config.sha256"
            ).read_text("utf-8").split()[0]
    return {
        "bundle_zip_sha256": zip_sha,
        "bundle_prefix_ok": zip_sha.startswith("ee345dab"),
        "bundle_full_expected": "ee345dab3a587b5183e3d80b7a45f2283047f6d1d972c6eff5fc3bb47b74bb03",
        "bundle_full_match": zip_sha == "ee345dab3a587b5183e3d80b7a45f2283047f6d1d972c6eff5fc3bb47b74bb03",
        "n_manifest_files": len(claimed),
        "manifest_files": per_file,
        "packet_pins": pins,
        "config_sidecar_matches_config": side == sha256_file(
            STAT.parent / "autonomous_agent/state/campaign_config.json"),
        "n_zip_entries": len(zip_names),
    }


# ------------------------------------------------------------- B. SIM-1
SIM1_CELLS = [
    ("i_balanced_symmetric", True), ("ii_skewed_sizes_rates", True),
    ("iii_rho0", True), ("iii_rho50", True), ("iii_rho90", True),
    ("iv_regime_small_n", True), ("v_power_delta_minus_001", False),
]
ALPHAS = (0.10, 0.05, 0.025, 0.01)
METHODS = ("p_a", "p_b", "p_c")


def section_sim1() -> dict:
    cells = {}
    for name, calibration in SIM1_CELLS:
        z = np.load(RES / f"sim1_{name}.npz")
        entry = {"calibration": calibration}
        for m in METHODS:
            p = z[m]
            entry[m] = {}
            for a in ALPHAS:
                k = int(np.count_nonzero(p <= a))
                rate = k / p.size
                rec = {"k": k, "n": int(p.size), "rate": rate}
                if HAVE_SCIPY and calibration:
                    rec["p_liberal"] = float(binom.sf(k - 1, p.size, a))
                entry[m][a] = rec
        cells[name] = entry
    cal = [n for n, c in SIM1_CELLS if c]
    means = {m: float(np.mean([cells[n][m][0.05]["rate"] for n in cal]))
             for m in METHODS}
    bonf = 0.05 / (6 * 4 * 3)
    flags = {}
    for m in METHODS:
        raw = [cells[n][m][a]["p_liberal"]
               for n in cal for a in ALPHAS if HAVE_SCIPY]
        flags[m] = {
            "raw_flags_p_lt_0.05": sum(1 for p in raw if p < 0.05),
            "bonferroni_flags_p_lt_6.94e-4": sum(1 for p in raw if p < bonf),
            "min_raw_p": float(min(raw)) if raw else None,
        }
    claims = {
        "means_claimed": {"p_a": 0.0635, "p_b": 0.0498, "p_c": 0.0632},
        "flags_claimed": {"p_a": "12/24", "p_b": "1/24", "p_c": "8/24"},
        "min_raw_p_claimed_p_a": 0.0023,
        "power_rates_claimed": {"p_a": 0.453, "p_b": 0.411, "p_c": 0.457},
    }
    checks = {
        "means_match_rounded": all(
            abs(means[m] - claims["means_claimed"][m]) < 0.0005 for m in METHODS),
        "flag_counts_match": all(
            f"{flags[m]['raw_flags_p_lt_0.05']}/24" == claims["flags_claimed"][m]
            for m in METHODS),
        "no_bonferroni_flags": all(
            flags[m]["bonferroni_flags_p_lt_6.94e-4"] == 0 for m in METHODS),
        "power_rates_match": all(
            abs(cells["v_power_delta_minus_001"][m][0.05]["rate"]
                - claims["power_rates_claimed"][m]) < 0.0005 for m in METHODS),
    }
    return {"cells": cells, "means_at_0.05": means, "flags": flags,
            "claims": claims, "checks": checks}


# ------------------------------------------------------------- C. SIM-3
def section_sim3() -> dict:
    submitted = json.loads((RES / "sim3.json").read_text("utf-8"))
    recomputed = {}
    for name, _cal in SIM1_CELLS:
        z = np.load(RES / f"sim1_{name}.npz")
        ci_rej = z["ci_hi"] < 0.0
        entry = {}
        for m in METHODS:
            p_rej = z[m] <= 0.05
            k = int(np.count_nonzero(p_rej ^ ci_rej))
            entry[m] = {"k_disagree": k, "n": int(p_rej.size),
                        "rate": k / p_rej.size,
                        "p_gate_rejects": int(p_rej.sum()),
                        "ci_gate_rejects": int(ci_rej.sum())}
        recomputed[name] = entry
    # cross-check against submitted sim3.json (from_sim1 block)
    diffs = []
    sub1 = submitted.get("from_sim1", {})
    for cell, em in recomputed.items():
        s = sub1.get(cell, {})
        for m in METHODS:
            got = em[m]["rate"]
            want = (s.get(m) or {}).get("rate")
            if want is None or abs(got - want) > 1e-12:
                diffs.append({"cell": cell, "method": m,
                              "recomputed": got, "submitted": want})
    rates_b = [recomputed[c]["p_b"]["rate"] for c, _ in SIM1_CELLS]
    return {
        "recomputed": recomputed,
        "submitted_crosscheck_diffs": diffs,
        "p_b_rate_range": [min(rates_b), max(rates_b)],
        "claim_p_b_range_1.4_to_10.5": [0.014, 0.105],
        "all_methods_over_1pct": all(
            recomputed[c][m]["rate"] > 0.01
            for c, _ in SIM1_CELLS for m in METHODS),
        "criterion": submitted.get("criterion"),
        "sim3_pass_submitted": submitted.get("SIM3_pass"),
    }


# ------------------------------------------------------------- D. SIM-2
M_GRID = (1, 4, 12, 24, 36, 50, 90)
B_GRID = (500, 1000, 2000)


def holm_reject_matrix(p: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """Own textbook step-down (vectorized): True where H0 is rejected.

    p: (N, m).  Returns bool (N, m) in input order.  Step-down: reject
    sorted ranks while p_(i) <= alpha/(m - i); stop at first failure.
    """
    n, m = p.shape
    order = np.argsort(p, axis=1, kind="stable")
    ps = np.take_along_axis(p, order, axis=1)
    thresh = alpha / (m - np.arange(m))
    ok = ps <= thresh
    step = np.logical_and.accumulate(ok, axis=1)
    rej_sorted = np.zeros_like(step)
    rej_sorted[:, :] = step
    rej = np.zeros_like(rej_sorted)
    np.put_along_axis(rej, order, rej_sorted, axis=1)
    return rej


def section_sim2() -> dict:
    import sys
    sys.path.insert(0, str(STAT))
    import simh10  # noqa: E402  (submitted simulation code, for cross-checks)
    rhos = {0.0: "sim2_rho00_pvalues.npz",
            0.3: "sim2_rho03_pvalues.npz",
            0.7: "sim2_rho07_pvalues.npz"}
    rows = []
    crosscheck = []
    for rho, fname in rhos.items():
        z = np.load(RES / fname)
        for mkey, arr in (("p_a", z["pa"]), ("p_b", z["pb"]), ("p_c", z["pc"])):
            n_camp = arr.shape[0]
            for m in M_GRID:
                for bi, B in enumerate(B_GRID):
                    sub = arr[:, :m, bi]
                    rej = holm_reject_matrix(sub, 0.05)
                    any_rej = rej.any(axis=1)
                    k = int(any_rej.sum())
                    attain = (1.0 / (B + 1)) <= 0.05 / m
                    row = {"rho": rho, "method": mkey, "m": m, "B": B,
                           "k_fwer": k, "n": n_camp, "fwer": k / n_camp,
                           "attainable": attain}
                    if HAVE_SCIPY:
                        row["cp95"] = list(cp_interval(k, n_camp))
                        row["p_liberal"] = float(binom.sf(k - 1, n_camp, 0.05))
                    rows.append(row)
                    # cross-check own Holm vs submitted simh10 Holm (subset)
                    if len(crosscheck) < 400 and (m, B) in ((4, 500), (24, 1000),
                                                            (36, 2000), (90, 1000)):
                        idx = len(crosscheck) % n_camp
                        theirs = simh10.holm_step_down(sub[idx], 0.05)
                        mine = rej[idx]
                        crosscheck.append(bool(np.array_equal(
                            theirs.astype(bool), mine)))
    def rng_for(method, attainable_only=True):
        vals = [r["fwer"] for r in rows
                if r["method"] == method and (r["attainable"] or not attainable_only)]
        return [min(vals), max(vals)] if vals else [None, None]
    b_rows = [r for r in rows if r["method"] == "p_b" and r["attainable"]]
    worst = max(b_rows, key=lambda r: r["fwer"])
    # c4-relevant cells at B=1000
    c4 = {m: [min(r["fwer"] for r in rows if r["method"] == meth and r["m"] == m
                   and r["B"] == 1000 and r["attainable"]),
              max(r["fwer"] for r in rows if r["method"] == meth and r["m"] == m
                  and r["B"] == 1000 and r["attainable"])]
          for m in (24, 36) for meth in ("p_a", "p_b", "p_c")}
    mixed = json.loads((RES / "sim2_mixed.json").read_text("utf-8"))
    mixed_rows = mixed.get("rows") or []
    mixed_b = [r for r in mixed_rows if r.get("method") == "p_b"]
    # floor-blocked cells: FWER must be exactly 0 for (a)/(b)
    floor_zero = all(r["fwer"] == 0.0 for r in rows
                     if r["method"] in ("p_a", "p_b") and not r["attainable"])
    claims = {
        "p_b_attainable_range": [0.032, 0.057],
        "p_a_attainable_range": [0.066, 0.271],
        "p_c_attainable_range": [0.063, 0.242],
        "worst_p_b": {"k": 113, "n": 2000, "p": 0.1014},
        "mixed_p_true_H0_p_b": 0.0525,
        "mixed_power_p_b": 0.985,
    }
    checks = {
        "holm_crosscheck_all_equal": all(crosscheck) and len(crosscheck) > 0,
        "p_b_range_matches": (abs(rng_for("p_b")[0] - 0.032) < 5e-4
                              and abs(rng_for("p_b")[1] - 0.057) < 5e-4),
        "p_a_min_matches_0.066": abs(rng_for("p_a")[0] - 0.066) < 5e-4,
        "p_c_min_matches_0.063": abs(rng_for("p_c")[0] - 0.063) < 5e-4,
        "worst_p_b_k_113": worst["k_fwer"] == 113,
        "worst_p_b_binom_p": (abs(worst.get("p_liberal", 0) - 0.1014) < 5e-4
                              if HAVE_SCIPY else None),
        "floor_blocked_zero_fwer": floor_zero,
        "mixed_present": bool(mixed_b),
    }
    return {"rows": rows, "checks": checks,
            "p_b_attainable_range": rng_for("p_b"),
            "p_a_attainable_range": rng_for("p_a"),
            "p_c_attainable_range": rng_for("p_c"),
            "worst_p_b_cell": worst,
            "c4_cells_at_B1000": c4,
            "mixed_p_b": mixed_b,
            "claims": claims,
            "n_holm_crosschecks": len(crosscheck)}


# ------------------------------------------------------------- E. SIM-4
def section_sim4() -> dict:
    sys_out = {}
    s4 = json.loads((RES / "sim4.json").read_text("utf-8"))
    need = {f["family"]: 20 * f["m_bound"] - 1 if "m_bound" in f else None
            for f in s4.get("families", [])} if isinstance(s4.get("families"), list) else {}
    # arithmetic from the protocol rule itself
    arithmetic = {m: 20 * m - 1 for m in (24, 36, 12, 50, 51, 90)}
    sys_out["sim4_submitted_families"] = s4.get("families")
    sys_out["sim4_verdict_B1000"] = s4.get("verdict_B1000")
    sys_out["n_boot_in_draft"] = s4.get("n_boot_in_draft")
    sys_out["b_min_arithmetic_20m_minus_1"] = arithmetic
    sys_out["feasible_at_1000"] = {m: (1000 + 1 >= 20 * m)
                                   for m in arithmetic}
    sys_out["m50_boundary"] = {
        "1/1001": 1 / 1001, "0.05/50": 0.05 / 50,
        "floor_attains_first_holm_threshold_m50": 1 / 1001 <= 0.05 / 50,
        "floor_attains_first_threshold_m51": 1 / 1001 <= 0.05 / 51,
    }
    # production feasibility() cross-check
    from autonomous_agent.proposal_layer import multiplicity as MP
    sys_out["production_feasibility"] = {
        "feasible(1000,24)": MP.feasibility(1000, 24),
        "feasible(1000,36)": MP.feasibility(1000, 36),
        "feasible(1000,50)": MP.feasibility(1000, 50),
        "feasible(1000,51)": MP.feasibility(1000, 51),
        "feasible(500,36)": MP.feasibility(500, 36),
        "feasible(999,50)": MP.feasibility(999, 50),
    }
    sys_out["fail_closed_gate_refusal"] = None
    try:
        MP.require_approved_method("sign_flip")
    except Exception as exc:
        sys_out["fail_closed_gate_refusal"] = type(exc).__name__
    sys_out["approved_methods"] = sorted(MP.APPROVED_P_VALUE_METHODS)
    return sys_out


# ------------------------------------------------------------- F. SIM-5
def section_sim5() -> dict:
    s5 = json.loads((RES / "sim5.json").read_text("utf-8"))
    part_a = s5.get("part_a_fixture", {})
    part_b = s5.get("part_b_unpaired_control", {})
    outp = {"part_a_keys": sorted(part_a), "part_b_keys": sorted(part_b),
            "SIM5_pass": s5.get("SIM5_pass"), "part_b": part_b}
    # recompute fisher p if counts available
    if HAVE_SCIPY and "rejection_counts" in json.dumps(s5):
        outp["note"] = "counts embedded; see part_b"
    return outp


# ------------------------------------------------------------- G. Holm
def naive_holm(pvals, alpha=0.05):
    """Textbook Holm, written independently (index-tie-broken sort)."""
    m = len(pvals)
    idx = sorted(range(m), key=lambda i: (pvals[i], i))
    adj = [0.0] * m
    running = 0.0
    reject = [False] * m
    stopped = False
    for rank, i in enumerate(idx):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = running
        if not stopped and pvals[i] <= alpha / (m - rank):
            reject[i] = True
        else:
            stopped = True
    return adj, reject


def section_holm() -> dict:
    import sys
    sys.path.insert(0, str(STAT))
    import simh10
    from autonomous_agent.proposal_layer import multiplicity as MP
    rng = np.random.default_rng(20261013)
    n_cases, mism_adj, mism_prod_sim, n_edge = 0, 0, 0, 0
    for _ in range(20000):
        m = int(rng.integers(1, 61))
        kind = rng.integers(0, 4)
        if kind == 0:
            p = rng.random(m).tolist()
        elif kind == 1:                       # heavy ties (incl. 0/1)
            p = rng.choice([0.0, 0.001, 0.01, 0.05, 0.1, 0.5, 1.0],
                           size=m).tolist()
        elif kind == 2:                       # exactly at threshold
            m2 = int(rng.integers(1, 61))
            a = 0.05 / m2
            p = np.round(rng.random(m2), 6).tolist()
            p[0] = a
            m = m2
        else:
            p = rng.choice([0.0, 0.5, 1.0], size=m).astype(float).tolist()
        n_cases += 1
        adj1, rej1 = naive_holm(p, 0.05)
        adj2, rej2 = MP.holm_step_down(p, 0.05)
        if any(abs(x - y) > 1e-15 for x, y in zip(adj1, adj2)) or rej1 != rej2:
            mism_adj += 1
            if mism_adj <= 3:
                print("  MISMATCH prod:", p, adj1, adj2, rej1, rej2)
        rej3 = simh10.holm_step_down(np.array(p), 0.05)
        if [bool(x) for x in rej3] != rej1:
            mism_prod_sim += 1
    # alpha = 0.05 edge: rejection boundary equality handled identically?
    boundary = naive_holm([0.05 / 3] * 3, 0.05)
    boundary2 = MP.holm_step_down([0.05 / 3] * 3, 0.05)
    return {
        "random_cases": n_cases,
        "mismatches_production_vs_textbook": mism_adj,
        "mismatches_production_vs_simh10_rejections": mism_prod_sim,
        "boundary_case_textbook": boundary,
        "boundary_case_production": list(map(list, boundary2)),
        "alpha_grid_checked": 0.05,
        "n_edge_cases": n_edge,
    }


# ------------------------------------------------------------- I. type-I
WEEKS, SZ = 24, 15
N_ROWS = WEEKS * SZ
THETA, A_SIGMA, U_W, D_W, K_SCALE = 0.5, 1.0, 0.5, 0.4, 1.6


def auc_pairwise(y: np.ndarray, s: np.ndarray) -> float:
    """Own AUC (0.5 tie handling) — validated against sklearn in-script."""
    pos, neg = s[y == 1], s[y == 0]
    gt = pos[:, None] > neg[None, :]
    eq = pos[:, None] == neg[None, :]
    return float((gt + 0.5 * eq).mean())


def make_frame(scenario: str, rng: np.random.Generator):
    y = (rng.random(N_ROWS) < 0.30).astype(np.int64)
    if scenario == "ar1":
        u = np.empty(WEEKS)
        u[0] = rng.normal()
        for w in range(1, WEEKS):
            u[w] = 0.7 * u[w - 1] + math.sqrt(1 - 0.49) * rng.normal()
    else:
        u = rng.normal(size=WEEKS)
    d = rng.normal(size=N_ROWS)
    uw = np.repeat(u, SZ)
    e_a = rng.normal(size=N_ROWS)
    e_b = rng.normal(size=N_ROWS)
    sig = THETA * (2 * y - 1) + U_W * uw + D_W * d + A_SIGMA * e_a
    if scenario == "scale":
        # equal population AUC (affine invariance), broken within-week
        # arm-label exchangeability (arm B rescaled by K_SCALE).
        sbs = K_SCALE * (THETA * (2 * y - 1) + U_W * uw + D_W * d
                         + A_SIGMA * e_b)
    else:
        sbs = THETA * (2 * y - 1) + U_W * uw + D_W * d + A_SIGMA * e_b
    week = np.repeat(np.arange(WEEKS), SZ)
    return y, sig, sbs, week


def sign_flip_p(y, s_a, s_b, week, rng, M=1000) -> float:
    d_hat = auc_pairwise(y, s_a) - auc_pairwise(y, s_b)
    pos = s_a[y == 1]
    neg = s_a[y == 0]
    y_pos, y_neg = y == 1, y == 0

    def auc_from(a2: np.ndarray) -> float:
        p_, n_ = a2[y_pos], a2[y_neg]
        gt = p_[:, None] > n_[None, :]
        eq = p_[:, None] == n_[None, :]
        return float((gt + 0.5 * eq).mean())

    swaps = rng.integers(0, 2, size=(M, WEEKS)).astype(bool)
    count_le = 0
    for mrow in swaps:
        mask = mrow[week]                       # (N_ROWS,) flip membership
        a2 = np.where(mask, s_b, s_a)           # arm A after week flips
        b2 = np.where(mask, s_a, s_b)
        if auc_from(a2) - auc_from(b2) <= d_hat:
            count_le += 1
    return (count_le + 1) / (M + 1)


def section_type1() -> dict:
    from sklearn.metrics import roc_auc_score as sk_auc
    rng = np.random.default_rng(20261013)
    # validate own AUC against sklearn
    y, sa, sb, wk = make_frame("sym", rng)
    assert abs(auc_pairwise(y, sa) - sk_auc(y, sa)) < 1e-12
    results = {}
    for scenario in ("sym", "ar1", "scale"):
        n_trials, n_rej = 300, 0
        ps = []
        t_start = time.time()
        for _ in range(n_trials):
            y, sa, sb, wk = make_frame(scenario, rng)
            p = sign_flip_p(y, sa, sb, wk, rng)
            ps.append(p)
            if p <= 0.05:
                n_rej += 1
        del ps
        rate = n_rej / n_trials
        lo, hi = (cp_interval(n_rej, n_trials) if HAVE_SCIPY else (None, None))
        results[scenario] = {
            "n_trials": n_trials, "M_flips": 1000,
            "rejections_at_0.05": n_rej, "rate": rate,
            "cp95": [lo, hi],
            "significantly_above_0.05": bool(
                HAVE_SCIPY and binom.sf(n_rej - 1, n_trials, 0.05) < 0.05),
            "seconds": round(time.time() - t_start, 1),
            "description": {
                "sym": "null, arms i.i.d.-symmetric within week "
                       "(exchangeability holds)",
                "ar1": "null, AR(1) week factor rho=0.7, arms symmetric "
                       "(serial correlation, exchangeability holds)",
                "scale": "population AUCs equal by affine invariance, arm B "
                         "rescaled x1.6 (exchangeability broken)",
            }[scenario],
        }
        print(f"  type-I [{scenario}] {n_rej}/{n_trials} = {rate:.3f} "
              f"CP95 [{lo:.3f},{hi:.3f}]" if HAVE_SCIPY else
              f"  type-I [{scenario}] {n_rej}/{n_trials}", flush=True)
    return results


# ------------------------------------------------------------------ main
def main() -> None:
    import sys
    print("A: hashes...", flush=True)
    out["A_hashes"] = section_hashes()
    print("B: sim1...", flush=True)
    out["B_sim1"] = section_sim1()
    print("C: sim3...", flush=True)
    out["C_sim3"] = section_sim3()
    print("D: sim2 (own Holm over raw p-values)...", flush=True)
    out["D_sim2"] = section_sim2()
    print("E: sim4/feasibility...", flush=True)
    out["E_sim4"] = section_sim4()
    print("F: sim5...", flush=True)
    out["F_sim5"] = section_sim5()
    print("G: holm cross-checks...", flush=True)
    out["G_holm"] = section_holm()
    print("I: independent type-I mini-study...", flush=True)
    out["I_type1"] = section_type1()
    out["runtime_seconds"] = round(time.time() - T0, 1)
    out["scipy_available"] = HAVE_SCIPY
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"[saved] {OUT}  ({out['runtime_seconds']}s)")
    # concise verdict lines
    print("\n--- CHECK SUMMARY ---")
    print("hashes bundle full match :", out["A_hashes"]["bundle_full_match"])
    print("all packet pins match    :",
          all(v["match"] for v in out["A_hashes"]["packet_pins"].values()))
    print("sim1 checks             :", out["B_sim1"]["checks"])
    print("sim3 diffs vs submitted :", len(out["C_sim3"]["submitted_crosscheck_diffs"]))
    print("sim2 checks             :", out["D_sim2"]["checks"])
    print("holm mismatches (prod)  :", out["G_holm"]["mismatches_production_vs_textbook"])
    print("holm mismatches (sim10):", out["G_holm"]["mismatches_production_vs_simh10_rejections"])


if __name__ == "__main__":
    main()
