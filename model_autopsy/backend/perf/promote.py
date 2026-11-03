"""M15 Phase 1.4: promotion and rollback (offline).

A candidate replaces the baseline only with: valid experiment
record, reproducible training (params + seed + data hash),
no evaluation contamination (test period untouched until gate),
independent held-out delta with CI excluding zero harm,
acceptable calibration (Brier no worse +0.01), and no subgroup
AUC regression worse than -0.02 on adequate subgroups.
Otherwise the baseline is retained with reasons. The previous
model artifact is always kept for rollback.
"""
from __future__ import annotations


def gate(delta: dict, brier_base: float, brier_cand: float,
         sub_base: dict, sub_cand: dict) -> dict:
    reasons = []
    if delta.get("n", 0) < 100:
        reasons.append("held-out n too small")
    lo = (delta.get("delta_ci95") or [0, 0])[0]
    if not (delta.get("delta", 0) > 0 and lo > 0):
        reasons.append("held-out delta not reliably positive")
    if (brier_cand - brier_base) > 0.01:
        reasons.append("calibration regressed (Brier +%.4f)"
                       % (brier_cand - brier_base))
    for g, b in sub_base.items():
        c = (sub_cand.get(g) or {}).get("auc")
        if b.get("auc") is None or c is None:
            continue
        if c - b["auc"] < -0.02:
            reasons.append(f"subgroup {g} regressed "
                           f"({b['auc']} -> {c})")
    if reasons:
        return {"promote": False, "reasons": reasons,
                "action": "retain baseline; previous model kept"}
    return {"promote": True, "reasons": [],
            "action": "promote candidate; keep baseline for rollback"}
