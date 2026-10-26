#!/usr/bin/env python3
"""Runner for the isolated H-10 statistical validation (SIM-1..SIM-5).

Usage (from the repository root):
    py -3 -X utf8 stat_validation_h10/run_sim.py <stage> [--trials N] [--campaigns N]

Stages: selftest | sim1 | sim2 | sim3 | sim4 | sim5 | all

This script is deliberately isolated: it imports only `simh10` (its sibling
module) and the frozen study backend read-only (inside simh10.selftest /
SIM-5 fixture equivalence).  It never touches the live research harness,
campaign records, the champion, the pinned configuration, or the sealed
holdout.  All outputs go to stat_validation_h10/results/.

Protocols are predeclared in
`autonomous_agent/MAIN AUDITS AND REFLECTIONS/HARNESS_V1_1_0_IMPLEMENTATION_PLAN_2026_10_09.md`
(SIM-1..SIM-5 section).  Default N values follow the plan (SIM-1: 1,000
trials/cell; SIM-2: 2,000 campaigns/config); the --trials/--campaigns
overrides are smoke-test aids only and are recorded in the output meta so
partial runs can never be mistaken for plan-compliant evidence.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import simh10  # noqa: E402

RESULTS = HERE / "results"
REPO_ROOT = HERE.parent
C4_DRAFT = (REPO_ROOT / "autonomous_agent" / "MAIN AUDITS AND REFLECTIONS"
            / "CAMPAIGN_4_CONFIG_DRAFT_2026_10_09.json")

# Plan-frozen sizes (plan: SIM-1 N=1,000 trials/cell; SIM-2 N=2,000 campaigns)
PLAN_SIM1_TRIALS = 1000
PLAN_SIM2_CAMPAIGNS = 2000

ALPHA_GRID = simh10.ALPHA_GRID          # (0.10, 0.05, 0.025, 0.01)
HIST_BINS = np.array([0.0, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05,
                      0.10, 0.25, 0.50, 0.75, 1.0])
METHODS = ("p_a", "p_b", "p_c")
METHOD_LABEL = {"p_a": "(a) sign proportion of paired bootstrap deltas",
                "p_b": "(b) week-level sign-flip / permutation",
                "p_c": "(c) normal-z on bootstrap SE"}

# SIM-1 cell grid (see plan SIM-1 (i)-(v); rho sweep cell rho=0.5 coincides
# with cell (i) and is run anyway for explicit coverage).
SIM1_CELLS = [
    dict(name="i_balanced_symmetric", W=60, sz=60, pi=0.30, rho=0.5,
         dtheta=0.0, skewed=False, plan_cell="i"),
    dict(name="ii_skewed_sizes_rates", W=60, sz=60, pi=0.30, rho=0.5,
         dtheta=0.0, skewed=True, plan_cell="ii"),
    dict(name="iii_rho0", W=60, sz=60, pi=0.30, rho=0.0, dtheta=0.0,
         skewed=False, plan_cell="iii"),
    dict(name="iii_rho50", W=60, sz=60, pi=0.30, rho=0.5, dtheta=0.0,
         skewed=False, plan_cell="iii"),
    dict(name="iii_rho90", W=60, sz=60, pi=0.30, rho=0.9, dtheta=0.0,
         skewed=False, plan_cell="iii"),
    # regime-cell-like small sample: n = 3,752 rows, E[positives] = 932
    dict(name="iv_regime_small_n", W=60, sz=None, sizes=[63] * 32 + [62] * 28,
         pi=932 / 3752, rho=0.5, dtheta=0.0, skewed=False, plan_cell="iv"),
    dict(name="v_power_delta_minus_001", W=60, sz=60, pi=0.30, rho=0.5,
         dtheta=-0.01, skewed=False, plan_cell="v", calibration=False),
]

SIM2_RHOS = (0.0, 0.3, 0.7)
SIM2_M_GRID = (1, 4, 12, 24, 36, 50, 90)
SIM2_B_GRID = (500, 1000, 2000)
SIM2_W, SIM2_SZ, SIM2_PI = 40, 20, 0.30
SIM2_MEMBERS = 90


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _simh10_sha() -> str:
    return hashlib.sha256((HERE / "simh10.py").read_bytes()).hexdigest()


def save_json(path: Path, obj: dict) -> None:
    obj = dict(obj)
    obj.setdefault("meta", {})
    obj["meta"].update({"written_utc": _now(), "simh10_sha256": _simh10_sha(),
                        "runner": str(Path(__file__).name)})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=False,
                               default=lambda o: o.item() if hasattr(o, "item")
                               else str(o)), encoding="utf-8")
    print(f"[saved] {path}", flush=True)


def theta_for_delta(theta_b: float, target_delta: float) -> float:
    """theta_A such that Phi(sqrt2*theta_A) - Phi(sqrt2*theta_b) = target."""
    target = simh10.norm_cdf(math.sqrt(2.0) * theta_b) + target_delta
    lo, hi = -2.0, 2.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if simh10.norm_cdf(math.sqrt(2.0) * mid) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def rate_summary(ks: dict[str, int], n: int, alpha: float) -> dict:
    """Per-alpha rejection summary with exact binomial CI + liberal test."""
    out = {}
    for key, k in ks.items():
        lo, hi = simh10.clopper_pearson(k, n, 0.95)
        out[key] = {
            "alpha": alpha, "k_reject": int(k), "n_trials": int(n),
            "rate": k / n, "cp95_lo": lo, "cp95_hi": hi,
            "p_liberal_one_sided": simh10.liberal_p(k, n, alpha),
        }
    return out


# --------------------------------------------------------------------------
# Stage: selftest
# --------------------------------------------------------------------------

def stage_selftest() -> dict:
    print("[selftest] running simh10.selftest() ...", flush=True)
    t0 = time.time()
    res = simh10.selftest()
    res["duration_s"] = round(time.time() - t0, 2)
    save_json(RESULTS / "selftest.json", res)
    for name, chk in res["checks"].items():
        flag = "PASS" if chk["ok"] else "FAIL"
        print(f"  [{flag}] {name}: {chk['detail']}", flush=True)
    print(f"[selftest] {'ALL CHECKS PASSED' if res['passed'] else 'FAILURES PRESENT'}"
          f" ({res['duration_s']}s)", flush=True)
    return res


# --------------------------------------------------------------------------
# Stage: SIM-4 (deterministic freeze-time feasibility)
# --------------------------------------------------------------------------

def stage_sim4() -> dict:
    print("[sim4] parsing C4 draft for family bounds ...", flush=True)
    if not C4_DRAFT.exists():
        res = {"error": f"config draft not found: {C4_DRAFT}"}
        save_json(RESULTS / "sim4.json", res)
        return res
    res = simh10.sim4_feasibility(C4_DRAFT)
    save_json(RESULTS / "sim4.json", res)
    for row in res["families"]:
        print(f"  family={row['family']:32s} m<={row['m_bound']:3d} "
              f"B_min={row['B_min_required']:5d} B1000_ok={row['B1000_ok']} "
              f"config_n_boot_ok={row['config_n_boot_ok']}", flush=True)
    print(f"  verdict @ B=1000: {res['verdict_B1000']} | unbound m=90 needs "
          f"B>={res['unbound_contingency']['B_min_required']}", flush=True)
    return res


# --------------------------------------------------------------------------
# Stage: SIM-1 (null calibration) + per-trial records for SIM-3
# --------------------------------------------------------------------------

def stage_sim1(trials: int) -> dict:
    print(f"[sim1] N={trials} trials/cell, B=M=1000, "
          f"{len(SIM1_CELLS)} cells", flush=True)
    if trials != PLAN_SIM1_TRIALS:
        print("  *** NON-PLAN N (smoke run) - not plan-compliant evidence ***",
              flush=True)
    summary_cells = {}
    for ci, cell in enumerate(SIM1_CELLS):
        seed = 1100 + ci
        rng = np.random.default_rng(seed)
        theta_b = 0.35
        theta_a = (theta_for_delta(theta_b, cell["dtheta"])
                   if cell.get("dtheta") else theta_b)
        t0 = time.time()
        pa = np.full(trials, np.nan)
        pb = np.full(trials, np.nan)
        pc = np.full(trials, np.nan)
        ci_hi = np.full(trials, np.nan)
        se = np.full(trials, np.nan)
        dh = np.full(trials, np.nan)
        nv = np.zeros(trials, dtype=np.int64)
        npos = np.zeros(trials, dtype=np.int64)
        for k in range(trials):
            stats = simh10.make_trial(
                cell["W"], cell["sz"] or 0, cell["pi"], cell["rho"],
                theta_a, theta_b, rng, skewed=cell["skewed"],
                sizes=cell.get("sizes"))
            r = simh10.run_methods(stats, B=1000, M=1000, rng=rng)
            pa[k], pb[k], pc[k] = r["p_a"], r["p_b"], r["p_c"]
            ci_hi[k], se[k], dh[k] = r["ci_hi"], r["se"], r["delta_hat"]
            nv[k], npos[k] = r["n_boot_valid"], stats.n_pos
            if (k + 1) % 250 == 0:
                el = time.time() - t0
                print(f"  cell {cell['name']}: {k + 1}/{trials} "
                      f"({el:.0f}s, {el / (k + 1):.3f}s/trial)", flush=True)
        dur = time.time() - t0
        # per-method summaries
        is_calib = cell.get("calibration", True)
        methods_out = {}
        for mkey, arr in (("p_a", pa), ("p_b", pb), ("p_c", pc)):
            per_alpha = {}
            for alpha in ALPHA_GRID:
                kcnt = int(np.count_nonzero(arr <= alpha))
                per_alpha[str(alpha)] = rate_summary(
                    {"all": kcnt}, trials, alpha)["all"]
            hist, _ = np.histogram(arr, bins=HIST_BINS)
            methods_out[mkey] = {
                "per_alpha": per_alpha,
                "histogram_counts": hist.tolist(),
                "histogram_bins": HIST_BINS.tolist(),
                "mean_p": float(np.nanmean(arr)),
                "min_p": float(np.nanmin(arr)),
            }
        cell_res = {
            "plan_cell": cell["plan_cell"],
            "calibration_cell": is_calib,
            "dgp": {k: v for k, v in cell.items() if k != "calibration"},
            "theta_A": theta_a, "theta_B": theta_b,
            "true_delta_auc": (simh10.norm_cdf(math.sqrt(2) * theta_a)
                               - simh10.norm_cdf(math.sqrt(2) * theta_b)),
            "B": 1000, "M": 1000, "N": trials, "seed": seed,
            "duration_s": round(dur, 1),
            "mean_n_positives": float(npos.mean()),
            "mean_n_boot_valid": float(nv.mean()),
            "methods": methods_out,
        }
        save_json(RESULTS / f"sim1_{cell['name']}.json", cell_res)
        np.savez_compressed(RESULTS / f"sim1_{cell['name']}.npz",
                            p_a=pa, p_b=pb, p_c=pc, ci_hi=ci_hi, se=se,
                            delta_hat=dh, n_boot_valid=nv, n_pos=npos)
        # console roll-up at alpha=0.05
        row = " | ".join(
            f"{m}: {methods_out[m]['per_alpha']['0.05']['rate']:.3f}"
            for m in METHODS)
        print(f"  cell {cell['name']} done ({dur:.0f}s) reject@0.05 -> {row}",
              flush=True)
        summary_cells[cell["name"]] = cell_res

    # Liberal tests with family-wise correction across cells x alphas x methods
    n_cal = sum(1 for c in SIM1_CELLS if c.get("calibration", True))
    n_tests = n_cal * len(ALPHA_GRID) * len(METHODS)
    bonf = 0.05 / n_tests
    verdicts = {}
    for mkey in METHODS:
        liberal_raw, liberal_bonf = [], []
        for name, cres in summary_cells.items():
            if not cres["calibration_cell"]:
                continue
            for alpha in ALPHA_GRID:
                pr = cres["methods"][mkey]["per_alpha"][str(alpha)][
                    "p_liberal_one_sided"]
                if pr < 0.05:
                    liberal_raw.append(f"{name}@{alpha}(p={pr:.2g})")
                if pr < bonf:
                    liberal_bonf.append(f"{name}@{alpha}(p={pr:.2g})")
        verdicts[mkey] = {
            "liberal_cells_raw_0.05": liberal_raw,
            "liberal_cells_bonferroni": liberal_bonf,
            "bonferroni_threshold": bonf,
            "n_calibration_cells": n_cal,
            "SIM1_pass_no_liberal_cell": len(liberal_bonf) == 0,
            "note": ("raw flags (p<0.05 uncorrected) listed for transparency; "
                     "plan pass criterion applied conservatively at the "
                     "Bonferroni-corrected level across calibration cells x "
                     "alphas x methods"),
        }
    summary = {
        "N": trials, "B": 1000, "M": 1000,
        "cells": {k: {"plan_cell": v["plan_cell"],
                      "true_delta_auc": v["true_delta_auc"],
                      "reject@0.05": {m: v["methods"][m]["per_alpha"]["0.05"]
                                      for m in METHODS}}
                  for k, v in summary_cells.items()},
        "verdicts": verdicts,
    }
    save_json(RESULTS / "sim1_summary.json", summary)
    for mkey in METHODS:
        v = verdicts[mkey]
        print(f"  [SIM-1 {mkey}] pass(no liberal cell, Bonf)="
              f"{v['SIM1_pass_no_liberal_cell']} raw_flags="
              f"{v['liberal_cells_raw_0.05']}", flush=True)
    return summary


# --------------------------------------------------------------------------
# Stage: SIM-2 (Holm FWER; pooled-member design)
# --------------------------------------------------------------------------

def _sim2_pvalues_for_member(st, rng, W):
    """Bootstrap/sign-flip p-values at B/M in {500,1000,2000} from nested
    draws (first 500/1000 of 2000 replicates) + CI uppers per B."""
    n = st.n_pos + st.n_neg
    K, wp, t = simh10.draw_week_multiplicities(st.week_sizes, n, 2000, rng)
    d = st.bootstrap_deltas(K, wp, t)
    d = d[np.isfinite(d)]
    S = rng.integers(0, 2, size=(2000, W)) * 2 - 1
    fl = st.sign_flip_deltas(S)
    dh = st.delta_hat
    pas, pbs, pcs, cihis = [], [], [], []
    for Bl in SIM2_B_GRID:
        db = d[:Bl] if d.size >= Bl else d
        fb = fl[:Bl]
        pas.append((int(np.count_nonzero(db >= 0)) + 1) / (db.size + 1))
        pbs.append((int(np.count_nonzero(fb <= dh)) + 1) / (fb.size + 1))
        se = float(np.std(db, ddof=1)) if db.size > 1 else 0.0
        z = dh / se if se > 0 else (math.inf if dh >= 0 else -math.inf)
        pcs.append(simh10.norm_cdf(z))
        cihis.append(float(np.quantile(db, 0.975)))
    return pas, pbs, pcs, cihis


def _fwer_table(parr, campaigns):
    """parr: (N, members, 3 B-grid); returns FWER rows per (m, B)."""
    rows = []
    for m in SIM2_M_GRID:
        for bi, Bl in enumerate(SIM2_B_GRID):
            rej_counts = np.array([
                simh10.holm_step_down(parr[c, :m, bi], 0.05).sum()
                for c in range(campaigns)])
            rej = rej_counts > 0
            k = int(rej.sum())
            rows.append({
                "m": m, "B": Bl, "k_fwer": k, "n_campaigns": campaigns,
                "fwer": k / campaigns,
                "cp95": list(simh10.clopper_pearson(k, campaigns, 0.95)),
                "p_liberal_one_sided": simh10.liberal_p(k, campaigns, 0.05),
                "mean_rejections_per_campaign": float(rej_counts.mean()),
                "floor_p": 1.0 / (Bl + 1),
                "any_rejection_attainable": (1.0 / (Bl + 1)) <= 0.05 / m,
            })
    return rows


def _rho_fwer_rows(pa, pb, pc, campaigns) -> list:
    """FWER table rows for one rho's p-value arrays."""
    rows = []
    for mkey, arr in (("p_a", pa), ("p_b", pb), ("p_c", pc)):
        for row in _fwer_table(arr, campaigns):
            row["method"] = mkey
            rows.append(row)
    return rows


def _mixed_rows(pa, pbs, pc, n_mix) -> list:
    """Holm power-sanity rows for the mixed (11 H1 + 1 H0) configuration."""
    mix_rows = []
    bi = SIM2_B_GRID.index(1000)
    for mkey, arr in (("p_a", pa), ("p_b", pbs), ("p_c", pc)):
        rej_any = np.array([simh10.holm_step_down(arr[c, :, bi], 0.05)
                            for c in range(n_mix)])
        null_rej = rej_any[:, 11]
        h1_rej = rej_any[:, :11].mean(axis=1)
        mix_rows.append({
            "method": mkey, "B": 1000, "n_campaigns": n_mix,
            "p_any_rejection": float(rej_any.any(axis=1).mean()),
            "p_true_H0_rejected": float(null_rej.mean()),
            "mean_fraction_H1_rejected": float(h1_rej.mean()),
            "true_delta_H1": (simh10.norm_cdf(math.sqrt(2) * 0.20)
                              - simh10.norm_cdf(math.sqrt(2) * 0.35)),
        })
    return mix_rows


def stage_sim2(campaigns: int, budget_s: float = 0.0, shards: int = 1,
               shard_index: int = 0) -> dict:
    """SIM-2 worker.  shards==1 runs the full grid sequentially.  With
    shards>1 this process computes only campaigns c where
    c % shards == shard_index, using the same per-campaign seeds, so the
    union of shards is bit-identical to a sequential run; the --merge
    action assembles shard partials and computes the FWER tables."""
    assert shards >= 1 and 0 <= shard_index < shards
    suffix = "" if shards == 1 else f"_s{shard_index}of{shards}"
    print(f"[sim2] N={campaigns} campaigns/config; rhos={SIM2_RHOS}; "
          f"m-grid={SIM2_M_GRID}; B-grid={SIM2_B_GRID}; members=90 pooled; "
          f"shards={shards} shard_index={shard_index}", flush=True)
    if campaigns != PLAN_SIM2_CAMPAIGNS:
        print("  *** NON-PLAN N (smoke run) - not plan-compliant evidence ***",
              flush=True)
    out = {"N_campaigns": campaigns, "W": SIM2_W, "sz": SIM2_SZ,
           "pi": SIM2_PI, "members_max": SIM2_MEMBERS,
           "pooled_design": ("each campaign generates a 90-member correlated "
                             "pool; config (m) uses the first m members "
                             "(exchangeable), config (B) uses nested prefixes "
                             "of one 2000-replicate draw - valid per-config, "
                             "cross-config estimates correlated"),
           "campaign_seeding": ("per-campaign default_rng([stage_seed, c]) - "
                                "deterministic and resume-safe; campaigns are "
                                "mutually independent"),
           "sharding": (f"{shards} strided shard(s); shard k owns c % "
                        f"{shards} == k; identical per-campaign seeds as a "
                        "sequential run; FWER tables computed by --merge"),
           "rhos": {}}
    for ri, rho in enumerate(SIM2_RHOS):
        seed = 2200 + ri
        tag = f"{rho:.1f}".replace(".", "")
        partial = RESULTS / f"sim2_rho{tag}_partial{suffix}.npz"
        pa = np.full((campaigns, SIM2_MEMBERS, len(SIM2_B_GRID)), np.nan,
                     dtype=np.float64)
        pb = np.full_like(pa, np.nan)
        pc = np.full_like(pa, np.nan)
        cih = np.full((campaigns, SIM2_MEMBERS, len(SIM2_B_GRID)), np.nan)
        if partial.exists():
            with np.load(partial) as z:
                pa[:] = z["pa"]
                pb[:] = z["pb"]
                pc[:] = z["pc"]
                cih[:] = z["cih"]
            print(f"  rho={rho}[shard {shard_index}]: partial resumed "
                  f"({int((~np.isnan(pa[:, 0, 0])).sum())} campaigns filled)",
                  flush=True)
        thetas = [(0.35, 0.35)] * SIM2_MEMBERS
        t0 = time.time()
        own = 0
        for c in range(shard_index, campaigns, shards):
            if not np.isnan(pa[c, 0, 0]):
                continue                      # already filled (resume)
            rng_c = np.random.default_rng([seed, c])
            members = simh10.make_correlated_members(
                SIM2_W, SIM2_SZ, SIM2_PI, rho, thetas, rng_c)
            for j, st in enumerate(members):
                pas, pbs_, pcs_, cihis = _sim2_pvalues_for_member(
                    st, rng_c, SIM2_W)
                pa[c, j], pb[c, j], pc[c, j] = pas, pbs_, pcs_
                cih[c, j] = cihis
            own += 1
            if own % 100 == 0:
                el = time.time() - t0
                print(f"  rho={rho}[shard {shard_index}]: {own} own campaigns "
                      f"({el:.0f}s, {el / own:.2f}s/campaign)", flush=True)
            if own % 50 == 0:
                np.savez_compressed(partial, pa=pa, pb=pb, pc=pc, cih=cih)
            if budget_s and (time.time() - t0) > budget_s:
                np.savez_compressed(partial, pa=pa, pb=pb, pc=pc, cih=cih)
                print(f"  rho={rho}[shard {shard_index}]: time budget hit "
                      f"after {own} own campaigns; partial saved - rerun to "
                      f"resume", flush=True)
                return out
        dur = time.time() - t0
        np.savez_compressed(partial, pa=pa, pb=pb, pc=pc, cih=cih)
        if shards == 1:
            rows = _rho_fwer_rows(pa, pb, pc, campaigns)
            out["rhos"][str(rho)] = {"seed": seed,
                                     "duration_s": round(dur, 1),
                                     "rows": rows}
            save_json(RESULTS / f"sim2_rho{tag}.json",
                      {"rho": rho, "N_campaigns": campaigns, "seed": seed,
                       "duration_s": round(dur, 1), "rows": rows})
            np.savez_compressed(RESULTS / f"sim2_rho{tag}_pvalues.npz",
                                pa=pa, pb=pb, pc=pc, cih=cih)
            partial.unlink()
            worst = max((r for r in rows if r["method"] == "p_a"),
                        key=lambda r: r["fwer"])
            print(f"  rho={rho} done ({dur:.0f}s); max FWER (p_a): "
                  f"{worst['fwer']:.4f} at m={worst['m']},B={worst['B']}",
                  flush=True)
        else:
            out["rhos"][str(rho)] = {"seed": seed,
                                     "shard_stride_seconds": round(dur, 1)}
            print(f"  rho={rho}[shard {shard_index}]: stride done "
                  f"({dur:.0f}s, {own} own campaigns)", flush=True)

    # Mixed configuration: one true H0 among strong H1s (plan SIM-2 final line)
    n_mix = campaigns
    thetas = [(0.20, 0.35)] * 11 + [(0.35, 0.35)]
    mix_partial = RESULTS / f"sim2_mixed_partial{suffix}.npz"
    pa = np.full((n_mix, 12, len(SIM2_B_GRID)), np.nan)
    pc = np.full_like(pa, np.nan)
    pbs = np.full_like(pa, np.nan)
    if mix_partial.exists():
        with np.load(mix_partial) as zm:
            pa[:] = zm["pa"]
            pbs[:] = zm["pbs"]
            pc[:] = zm["pc"]
        print(f"  mixed[shard {shard_index}]: partial resumed "
              f"({int((~np.isnan(pa[:, 0, 0])).sum())} campaigns filled)",
              flush=True)
    t0 = time.time()
    own = 0
    for c in range(shard_index, n_mix, shards):
        if not np.isnan(pa[c, 0, 0]):
            continue
        rng_c = np.random.default_rng([2999, c])
        members = simh10.make_correlated_members(
            SIM2_W, SIM2_SZ, SIM2_PI, 0.3, thetas, rng_c)
        for j, st in enumerate(members):
            pas_, pbs_, pcs_, _ = _sim2_pvalues_for_member(st, rng_c, SIM2_W)
            pa[c, j], pbs[c, j], pc[c, j] = pas_, pbs_, pcs_
        own += 1
        if own % 100 == 0:
            print(f"  mixed[shard {shard_index}]: {own} own campaigns "
                  f"({time.time() - t0:.0f}s)", flush=True)
        if own % 50 == 0:
            np.savez_compressed(mix_partial, pa=pa, pbs=pbs, pc=pc)
        if budget_s and (time.time() - t0) > budget_s:
            np.savez_compressed(mix_partial, pa=pa, pbs=pbs, pc=pc)
            print(f"  mixed[shard {shard_index}]: time budget hit after {own} "
                  f"own campaigns; partial saved - rerun to resume", flush=True)
            return out
    np.savez_compressed(mix_partial, pa=pa, pbs=pbs, pc=pc)
    if shards == 1:
        mix_partial.unlink()
        mix_rows = _mixed_rows(pa, pbs, pc, n_mix)
        out["mixed_config"] = {"rho": 0.3, "m": 12, "B": 1000,
                               "thetas": "11 x (0.20,0.35) strong H1 + "
                                         "1 x (0.35,0.35) true H0",
                               "rows": mix_rows,
                               "seed": 2999}
        save_json(RESULTS / "sim2_mixed.json", out["mixed_config"])
        save_json(RESULTS / "sim2_summary.json", out)
        for r in mix_rows:
            print(f"  mixed[{r['method']}]: P(any rej)={r['p_any_rejection']:.3f} "
                  f"P(H0 rej)={r['p_true_H0_rejected']:.3f} "
                  f"E[frac H1 rej]={r['mean_fraction_H1_rejected']:.3f}",
                  flush=True)
    else:
        print(f"  mixed[shard {shard_index}]: stride done "
              f"({time.time() - t0:.0f}s, {own} own campaigns)", flush=True)
    print(f"[sim2] shard {shard_index}/{shards} complete", flush=True)
    return out


def stage_sim2_merge(campaigns: int, shards: int) -> dict:
    """Assemble shard partials, verify full campaign coverage, compute the
    FWER tables and mixed-config rows, save final SIM-2 artifacts."""
    print(f"[sim2-merge] assembling {shards} shards ...", flush=True)
    out = {"N_campaigns": campaigns, "W": SIM2_W, "sz": SIM2_SZ,
           "pi": SIM2_PI, "members_max": SIM2_MEMBERS,
           "pooled_design": ("each campaign generates a 90-member correlated "
                             "pool; config (m) uses the first m members "
                             "(exchangeable), config (B) uses nested prefixes "
                             "of one 2000-replicate draw - valid per-config, "
                             "cross-config estimates correlated"),
           "campaign_seeding": ("per-campaign default_rng([stage_seed, c]) - "
                                "deterministic and resume-safe; campaigns are "
                                "mutually independent"),
           "sharding": (f"merged from {shards} strided shards; union of "
                        "campaigns is bit-identical to a sequential run "
                        "(same per-campaign seeds)"),
           "rhos": {}}
    for ri, rho in enumerate(SIM2_RHOS):
        seed = 2200 + ri
        tag = f"{rho:.1f}".replace(".", "")
        pa = np.full((campaigns, SIM2_MEMBERS, len(SIM2_B_GRID)), np.nan)
        pb = np.full_like(pa, np.nan)
        pc = np.full_like(pa, np.nan)
        cih = np.full_like(pa, np.nan)
        for k in range(shards):
            f = RESULTS / f"sim2_rho{tag}_partial_s{k}of{shards}.npz"
            if not f.exists():
                msg = f"missing shard {k} partial for rho={rho}"
                print(f"[sim2-merge] ABORT: {msg}", flush=True)
                return {"error": msg}
            with np.load(f) as z:
                rows_k = np.isnan(pa[:, 0, 0]) & ~np.isnan(z["pa"][:, 0, 0])
                pa[rows_k] = z["pa"][rows_k]
                pb[rows_k] = z["pb"][rows_k]
                pc[rows_k] = z["pc"][rows_k]
                cih[rows_k] = z["cih"][rows_k]
        if np.isnan(pa).any() or np.isnan(cih).any():
            msg = f"incomplete campaign coverage for rho={rho} "
            msg += f"({int(np.isnan(pa[:, 0, 0]).sum())} missing)"
            print(f"[sim2-merge] ABORT: {msg}", flush=True)
            return {"error": msg}
        rows = _rho_fwer_rows(pa, pb, pc, campaigns)
        out["rhos"][str(rho)] = {"seed": seed, "rows": rows}
        save_json(RESULTS / f"sim2_rho{tag}.json",
                  {"rho": rho, "N_campaigns": campaigns, "seed": seed,
                   "merged_from_shards": shards, "rows": rows})
        np.savez_compressed(RESULTS / f"sim2_rho{tag}_pvalues.npz",
                            pa=pa, pb=pb, pc=pc, cih=cih)
        worst = max((r for r in rows if r["method"] == "p_a"),
                    key=lambda r: r["fwer"])
        print(f"  rho={rho} merged; max FWER (p_a): {worst['fwer']:.4f} at "
              f"m={worst['m']},B={worst['B']}", flush=True)
        for k in range(shards):
            (RESULTS / f"sim2_rho{tag}_partial_s{k}of{shards}.npz").unlink()
    # mixed
    n_mix = campaigns
    pa = np.full((n_mix, 12, len(SIM2_B_GRID)), np.nan)
    pc = np.full_like(pa, np.nan)
    pbs = np.full_like(pa, np.nan)
    for k in range(shards):
        f = RESULTS / f"sim2_mixed_partial_s{k}of{shards}.npz"
        if not f.exists():
            msg = f"missing mixed shard {k} partial"
            print(f"[sim2-merge] ABORT: {msg}", flush=True)
            return {"error": msg}
        with np.load(f) as z:
            rows_k = np.isnan(pa[:, 0, 0]) & ~np.isnan(z["pa"][:, 0, 0])
            pa[rows_k] = z["pa"][rows_k]
            pbs[rows_k] = z["pbs"][rows_k]
            pc[rows_k] = z["pc"][rows_k]
    if np.isnan(pa).any():
        msg = f"incomplete mixed coverage " \
              f"({int(np.isnan(pa[:, 0, 0]).sum())} missing)"
        print(f"[sim2-merge] ABORT: {msg}", flush=True)
        return {"error": msg}
    mix_rows = _mixed_rows(pa, pbs, pc, n_mix)
    out["mixed_config"] = {"rho": 0.3, "m": 12, "B": 1000,
                           "thetas": "11 x (0.20,0.35) strong H1 + "
                                     "1 x (0.35,0.35) true H0",
                           "rows": mix_rows, "seed": 2999,
                           "merged_from_shards": shards}
    save_json(RESULTS / "sim2_mixed.json", out["mixed_config"])
    save_json(RESULTS / "sim2_summary.json", out)
    for k in range(shards):
        (RESULTS / f"sim2_mixed_partial_s{k}of{shards}.npz").unlink()
    for r in mix_rows:
        print(f"  mixed[{r['method']}]: P(any rej)={r['p_any_rejection']:.3f} "
              f"P(H0 rej)={r['p_true_H0_rejected']:.3f} "
              f"E[frac H1 rej]={r['mean_fraction_H1_rejected']:.3f}",
              flush=True)
    print("[sim2-merge] COMPLETE", flush=True)
    return out


# --------------------------------------------------------------------------
# Stage: SIM-3 (CI-vs-p disagreement, derived from SIM-1/SIM-2 records)
# --------------------------------------------------------------------------

def stage_sim3() -> dict:
    print("[sim3] deriving CI-vs-p disagreement from SIM-1/SIM-2 records "
          "(alpha=0.05)", flush=True)
    res = {"alpha": 0.05, "criterion": "disagreement <= 1%",
           "from_sim1": {}, "from_sim2_m1": {}}
    thr = 0.01
    all_pass = True
    for cell in SIM1_CELLS:
        f = RESULTS / f"sim1_{cell['name']}.npz"
        if not f.exists():
            res["from_sim1"][cell["name"]] = {"error": "missing npz"}
            all_pass = False
            continue
        z = np.load(f)
        cell_out = {}
        for mkey in METHODS:
            p = z[mkey]
            ci_gate = z["ci_hi"] < 0.0
            p_gate = p <= 0.05
            dis = int(np.count_nonzero(p_gate != ci_gate))
            n = int(p.size)
            cell_out[mkey] = {
                "n_trials": n, "n_disagree": dis, "rate": dis / n,
                "ci_gate_rejects": int(ci_gate.sum()),
                "p_gate_rejects": int(p_gate.sum()),
                "pass_le_1pct": (dis / n) <= thr or not cell.get(
                    "calibration", True),
            }
            if cell.get("calibration", True) and (dis / n) > thr:
                all_pass = False
        res["from_sim1"][cell["name"]] = cell_out
    for rho in SIM2_RHOS:
        tag = f"{rho:.1f}".replace(".", "")
        f = RESULTS / f"sim2_rho{tag}_pvalues.npz"
        if not f.exists():
            res["from_sim2_m1"][str(rho)] = {"error": "missing npz"}
            continue
        z = np.load(f)
        key_map = {"p_a": "pa", "p_b": "pb", "p_c": "pc"}
        rho_out = {}
        for bi, Bl in enumerate(SIM2_B_GRID):
            ci_gate = z["cih"][:, 0, bi] < 0.0
            rho_out[str(Bl)] = {}
            for mkey in METHODS:
                p = z[key_map[mkey]][:, 0, bi]
                ok = np.isfinite(p) & np.isfinite(z["cih"][:, 0, bi])
                p_gate = p[ok] <= 0.05
                cg = ci_gate[ok]
                dis = int(np.count_nonzero(p_gate != cg))
                rho_out[str(Bl)][mkey] = {
                    "n": int(ok.sum()), "n_disagree": dis,
                    "rate": dis / max(1, int(ok.sum())),
                    "pass_le_1pct": (dis / max(1, int(ok.sum()))) <= thr,
                }
                # m=1 config: family-wise context absent, informational only
        res["from_sim2_m1"][str(rho)] = rho_out
    res["SIM3_pass"] = all_pass
    save_json(RESULTS / "sim3.json", res)
    for cell, out in res["from_sim1"].items():
        row = " | ".join(
            f"{m}: {out[m]['n_disagree']}/{out[m]['n_trials']}"
            f" ({out[m]['rate']:.4f})" for m in METHODS if m in out)
        print(f"  sim1 {cell}: {row}", flush=True)
    print(f"  [SIM-3] pass (<=1%) = {all_pass}", flush=True)
    return res


# --------------------------------------------------------------------------
# Stage: SIM-5 (paired equivalence vs frozen backend + unpaired control)
# --------------------------------------------------------------------------

def stage_sim5() -> dict:
    print("[sim5] (a) fixture equivalence: fast path + sequential replica vs "
          "frozen backend block_bootstrap_delta ...", flush=True)
    from sklearn.metrics import roc_auc_score
    res = {"part_a_fixture": {}, "part_b_unpaired_control": {}}

    # --- part (a): bit-for-bit fixture equivalence -----------------------
    W, sz, pi, rho = 30, 15, 0.28, 0.5
    theta_a, theta_b, n_boot, seed = 0.35, 0.33, 1000, 42
    rngf = np.random.default_rng(21)
    statf = simh10.make_trial(W, sz, pi, rho, theta_a, theta_b, rngf)
    backend = simh10._load_frozen_backend()
    import pandas as pd
    dates = pd.to_datetime("2023-01-01") + pd.to_timedelta(
        np.repeat(np.arange(W), sz) * 7, unit="D")
    frame = pd.DataFrame({"date": dates, "label": statf.y,
                          "cand": statf.sA, "ref": statf.sB})
    res_api = backend.block_bootstrap_delta(frame, "cand", "ref",
                                            n_boot=n_boot, seed=seed)
    # sequential replica (identical RNG consumption -> identical draws)
    seq_rng = np.random.default_rng(seed)
    deltas_seq = []
    for _ in range(n_boot):
        K, wp, t = simh10.sequential_draw_week_multiplicities(
            statf.week_sizes, statf.y.size, seq_rng)
        idx = []
        for w in range(W):
            if K[w]:
                idx.append(np.tile(statf._week_rows[w], int(K[w])))
        if wp >= 0 and t > 0:
            idx.append(statf._week_rows[wp][:t])
        sel = np.concatenate(idx)
        lab = statf.y[sel]
        if np.unique(lab).size < 2:
            continue
        deltas_seq.append(roc_auc_score(lab, statf.sA[sel])
                          - roc_auc_score(lab, statf.sB[sel]))
    deltas_seq = np.array(deltas_seq)
    ci_seq = np.quantile(deltas_seq, [0.025, 0.975])
    # fast path on the SAME sequential draws (quadratic-form identity)
    rng_same = np.random.default_rng(seed)
    Ks, wps, ts = [], [], []
    for _ in range(n_boot):
        K_, wp_, t_ = simh10.sequential_draw_week_multiplicities(
            statf.week_sizes, statf.y.size, rng_same)
        Ks.append(K_); wps.append(wp_); ts.append(t_)
    Ks = np.array(Ks, dtype=np.int64)
    wps = np.array(wps, dtype=np.int64)
    ts = np.array(ts, dtype=np.int64)
    fast_deltas = statf.bootstrap_deltas(Ks, wps, ts)
    base_mine = float(roc_auc_score(statf.y, statf.sA)
                      - roc_auc_score(statf.y, statf.sB))
    ci_fast = np.quantile(fast_deltas, [0.025, 0.975])
    res["part_a_fixture"] = {
        "fixture": {"W": W, "sz": sz, "pi": pi, "rho": rho,
                    "theta_A": theta_a, "theta_B": theta_b,
                    "n_boot": n_boot, "seed": seed,
                    "n_rows": int(statf.y.size)},
        "backend": {"delta_auc": res_api["delta_auc"],
                    "ci_95": list(res_api["ci_95"]),
                    "n_boot_valid": res_api["n_boot_valid"],
                    "block_weeks": res_api["block_weeks"]},
        "sequential_replica": {"delta_auc": base_mine,
                               "ci_95": ci_seq.tolist(),
                               "n_boot_valid": int(deltas_seq.size)},
        "fast_path_on_same_draws": {"ci_95": ci_fast.tolist()},
        "max_abs_diff_ci_seq_vs_backend": float(
            np.max(np.abs(ci_seq - np.array(res_api["ci_95"])))),
        "max_abs_diff_ci_fast_vs_seq": float(
            np.max(np.abs(ci_fast - ci_seq))),
        "abs_diff_delta_auc": abs(base_mine - res_api["delta_auc"]),
        "n_valid_match": int(deltas_seq.size) == res_api["n_boot_valid"],
        "bit_for_bit_pass": bool(
            np.max(np.abs(ci_seq - np.array(res_api["ci_95"]))) == 0.0
            and abs(base_mine - res_api["delta_auc"]) < 1e-12
            and int(deltas_seq.size) == res_api["n_boot_valid"]),
        "note": ("the production fast path uses batched RNG draws (same "
                 "statistical scheme, different RNG batching); bit-for-bit "
                 "equivalence is established for the sequential replica, and "
                 "the fast path is exact on identical draws "
                 "(max_abs_diff_ci_fast_vs_seq)"),
    }
    print(f"  backend ci={res_api['ci_95']} seq ci={ci_seq.tolist()} "
          f"max|diff|={res['part_a_fixture']['max_abs_diff_ci_seq_vs_backend']:.3e} "
          f"bit_for_bit={res['part_a_fixture']['bit_for_bit_pass']}", flush=True)

    # --- part (b): unpaired control --------------------------------------
    print("[sim5] (b) unpaired control: N=300 trials, cell-(i) DGP ...",
          flush=True)
    n_ctrl = 300
    rng = np.random.default_rng(5500)
    pr_p = np.zeros(n_ctrl, dtype=bool)
    pr_u = np.zeros(n_ctrl, dtype=bool)
    w_p = np.zeros(n_ctrl)
    w_u = np.zeros(n_ctrl)
    t0 = time.time()
    for k in range(n_ctrl):
        stats = simh10.make_trial(60, 60, 0.30, 0.5, 0.35, 0.35, rng)
        n = stats.n_pos + stats.n_neg
        K, wp, t = simh10.draw_week_multiplicities(stats.week_sizes, n, 1000,
                                                   rng)
        d = stats.bootstrap_deltas(K, wp, t)
        d = d[np.isfinite(d)]
        p_p = (int(np.count_nonzero(d >= 0)) + 1) / (d.size + 1)
        lo_p, hi_p = np.quantile(d, [0.025, 0.975])
        un = simh10.run_unpaired(stats, 1000, rng)
        pr_p[k] = p_p <= 0.05
        pr_u[k] = un["p_a"] <= 0.05
        w_p[k] = hi_p - lo_p
        w_u[k] = un["ci_width"]
        if (k + 1) % 100 == 0:
            print(f"  control: {k + 1}/{n_ctrl} ({time.time() - t0:.0f}s)",
                  flush=True)
    kp, ku = int(pr_p.sum()), int(pr_u.sum())
    fisher_p = simh10.two_sided_prop_test(kp, n_ctrl, ku, n_ctrl)
    res["part_b_unpaired_control"] = {
        "n_trials": n_ctrl, "B": 1000, "seed": 5500,
        "dgp": "cell-(i) balanced, rho=0.5, delta=0, W=60, sz=60, pi=0.30",
        "paired_reject_at_0.05": {"k": kp, "rate": kp / n_ctrl},
        "unpaired_reject_at_0.05": {"k": ku, "rate": ku / n_ctrl},
        "fisher_two_sided_p_on_rates": fisher_p,
        "mean_ci_width_paired": float(w_p.mean()),
        "mean_ci_width_unpaired": float(w_u.mean()),
        "width_ratio_unpaired_over_paired": float(w_u.mean() / w_p.mean()),
        "measurably_different": bool(
            (fisher_p < 0.01) or (w_u.mean() / w_p.mean() > 1.05)),
        "note": ("unpaired control resamples week blocks independently per "
                 "arm, destroying the paired-replicate structure the harness "
                 "CI gate relies on; expected to inflate CI width (variance "
                 "from both arms sampled independently)"),
    }
    print(f"  paired rej@0.05={kp / n_ctrl:.3f} unpaired={ku / n_ctrl:.3f} "
          f"(Fisher p={fisher_p:.3g}); width ratio="
          f"{res['part_b_unpaired_control']['width_ratio_unpaired_over_paired']:.3f}",
          flush=True)
    res["SIM5_pass"] = bool(res["part_a_fixture"]["bit_for_bit_pass"]
                            and res["part_b_unpaired_control"]["measurably_different"])
    print(f"  [SIM-5] pass = {res['SIM5_pass']}", flush=True)
    save_json(RESULTS / "sim5.json", res)
    return res


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=["selftest", "sim1", "sim2", "sim3",
                                      "sim4", "sim5", "all"])
    ap.add_argument("--trials", type=int, default=PLAN_SIM1_TRIALS,
                    help="SIM-1 trials/cell (default plan value 1000)")
    ap.add_argument("--campaigns", type=int, default=PLAN_SIM2_CAMPAIGNS,
                    help="SIM-2 campaigns/config (default plan value 2000)")
    ap.add_argument("--time-budget", type=float, default=0.0,
                    help="SIM-2: seconds per stage-chunk before saving a "
                         "partial checkpoint and exiting cleanly (0 = run "
                         "to completion)")
    ap.add_argument("--shards", type=int, default=1,
                    help="SIM-2: total number of strided worker shards")
    ap.add_argument("--shard-index", type=int, default=0,
                    help="SIM-2: this worker's shard index (0..shards-1)")
    ap.add_argument("--merge", action="store_true",
                    help="SIM-2: merge shard partials and compute FWER "
                         "tables instead of simulating")
    args = ap.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    stages = (["selftest", "sim4", "sim5", "sim1", "sim2", "sim3"]
              if args.stage == "all" else [args.stage])
    rc = 0
    for st in stages:
        print(f"==== stage: {st} ({_now()}) ====", flush=True)
        if st == "selftest":
            rc |= 0 if stage_selftest()["passed"] else 1
        elif st == "sim1":
            stage_sim1(args.trials)
        elif st == "sim2":
            if args.merge:
                res = stage_sim2_merge(args.campaigns, args.shards)
                if "error" in res:
                    print(f"[abort] merge failed: {res['error']}", flush=True)
                    rc |= 1
            else:
                stage_sim2(args.campaigns, budget_s=args.time_budget,
                           shards=args.shards, shard_index=args.shard_index)
        elif st == "sim3":
            stage_sim3()
        elif st == "sim4":
            stage_sim4()
        elif st == "sim5":
            stage_sim5()
        if rc:
            print("[abort] selftest failed; refusing to continue", flush=True)
            break
    print(f"==== done in {time.time() - t0:.0f}s (exit {rc}) ====", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
