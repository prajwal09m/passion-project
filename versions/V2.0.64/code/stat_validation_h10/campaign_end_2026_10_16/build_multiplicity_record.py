"""Campaign 4 — campaign-end multiplicity record (the mandatory finalization step).

Frozen design (plan §Multiplicity handling; config multiplicity_policy):
every per-cell / per-rung refutation test predeclared by the four frozen
families enters the campaign-end record; Holm step-down (alpha=0.05) over
the COMPLETE family assigns the only formal REFUTED labels that may ever
exist.  The approved p-value method is week_level_signflip_holm (owner's
recorded D2 decision, 2026-10-14).

Audit finding this script operationalizes (2026-10-16, verified against
every retained artifact):
  The executed v1.0.0 study pipeline emits pooled metrics only.  The
  v1.1.0 per-cell IUT evaluators (evaluate_regime_cells /
  evaluate_horizon_rungs / evaluate_purge_rungs) were never invoked by the
  production experiment path (only by tests), so NO per-member
  measurement -- no cell delta, no CI upper, no week-level g -- exists in
  any evaluation.json, ledger adjudication row, or memory file.
  Therefore no member has an unadjusted p-value and every predeclared
  member is UNAVAILABLE by construction.  The frozen C-2 Option A rule
  (missing_member_rule, owner-frozen in multiplicity_policy) then applies:
  unavailable members count toward m at p = 1.0, are labelled
  'unavailable', and can NEVER be formally REFUTED.  Counting strictens,
  never loosens, the remaining members' Holm thresholds -- vacuous here
  since every member is unavailable.  Scientific outcome, identical to
  the plan's fail-safe default ('if the pass can never run, every
  provisional signal defaults to INCONCLUSIVE'): ZERO formal refutations.

This script is deterministic, uses the frozen module API only (it
performs no statistics of its own), and append_record refuses to write a
second record for the same campaign, so re-running is a safe no-op check.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from autonomous_agent.proposal_layer import multiplicity as mult  # noqa: E402
from autonomous_agent.proposal_layer import signflip  # noqa: E402
from autonomous_agent import three_valued as tv  # noqa: E402

STATE = ROOT / "autonomous_agent" / "state"
LEDGER = STATE / "proposal_ledger.jsonl"
CONFIG = STATE / "campaign_config.json"
OUT = STATE / "campaign_end_multiplicity.jsonl"
C4 = "campaign-4-continuous-2026-10-14"


def main() -> int:
    # -- 1. frozen inputs: config pin, approved method, M and B ------------
    cfg_bytes = CONFIG.read_bytes()
    cfg = json.loads(cfg_bytes)
    assert cfg["campaign_id"] == C4, cfg["campaign_id"]
    pin = hashlib.sha256(cfg_bytes).hexdigest()
    sidecar = (STATE / "campaign_config.sha256").read_text("utf-8").strip()
    assert pin == sidecar, f"config pin {pin} != sidecar {sidecar}"
    mp = cfg["multiplicity_policy"]
    n_boot = int(mp["n_boot"])
    n_flips = int(mp["flip_draw"]["M"])
    assert n_boot == mult.MIN_N_BOOT, n_boot
    assert n_flips == mult.MIN_N_FLIPS, n_flips
    assert mp["missing_member_rule"] == "C-2_option_A"
    assert mp["missing_member_p"] == 1.0
    assert mp["campaign_end_record_required"] is True
    method = signflip.APPROVED_METHOD_NAME
    mult.require_approved_method(method)   # fail-closed gate

    # -- 2. derive the executed poolable set from the ledger ---------------
    rows = [json.loads(l) for l in LEDGER.read_text("utf-8").splitlines()
            if l.strip()]
    proposals, executed, adjudicated = {}, set(), {}
    for r in rows:
        if r.get("row_type") == "proposal":
            proposals[r["proposal_id"]] = r.get("proposal") or {}
        elif r.get("row_type") == "transition":
            d = r.get("detail") or {}
            if d.get("campaign_id") != C4:
                continue
            if r.get("to") == "EXECUTED":
                executed.add(r["proposal_id"])
            elif r.get("to") == "ADJUDICATED":
                adjudicated[r["proposal_id"]] = d
    # Every C4-executed proposal must have reached a terminal record
    # (interrupted executions are FAILED_EXECUTION and never adjudicated).
    families: dict[str, list[mult.FamilyMember]] = {}
    inventory = []
    for pid in sorted(executed):
        design = (proposals.get(pid, {}).get("design") or {})
        prims = [p.get("primitive_id") for p in design.get("primitives") or []]
        poolable = [p for p in prims
                    if p in mult.PRIMITIVE_TO_FAMILY]
        for prim in poolable:
            fam = mult.PRIMITIVE_TO_FAMILY[prim]
            ladder = tv.ladder_for(prim)
            assert ladder["family"] == fam
            exp = adjudicated.get(pid, {}).get("experiment_id")
            if exp is None:
                # interrupted before adjudication: members are unavailable
                # (never run at all); locate its experiment id from the
                # registry attempts.
                reg = json.loads(
                    (STATE / "experiment_registry.json").read_text("utf-8"))
                exp = next((a["experiment_id"] for a in reg["attempts"]
                            if pid.replace("prop-", "").replace("-1", "")
                            in a["experiment_id"]), None)
            assert exp, f"no experiment id for {pid}"
            for rung in ladder["rungs"]:
                families.setdefault(fam, []).append(mult.FamilyMember(
                    member_id=f"{exp}:{rung}", family=fam, primitive=prim,
                    experiment_id=exp, status=mult.STATUS_UNAVAILABLE,
                    note=("predeclared member; the executed v1.0.0 study "
                          "pipeline emitted pooled metrics only, so no "
                          "per-member delta/CI/week-level g exists in any "
                          "retained artifact (v1.1.0 per-cell evaluators "
                          "were never invoked in production); C-2 Option A: "
                          "counts toward m at p=1.0, never formally REFUTED")))
            inventory.append((fam, exp, prim))

    ledger_sha = hashlib.sha256(LEDGER.read_bytes()).hexdigest()
    print("config pin:", pin)
    print("ledger sha256:", ledger_sha)
    print("poolable experiments:",
          len({e for _, e, _ in inventory}),
          "| family sizes:",
          {f: len(v) for f, v in sorted(families.items())})
    for fam in sorted(families):
        bound = mult.FAMILIES[fam]["member_bound"]
        m = len(families[fam])
        mult.require_feasible(n_boot, m, n_flips)
        assert m <= bound, (fam, m, bound)

    # -- 3. compute via the frozen API and append once ---------------------
    if mult.read_records(OUT):
        print("record already exists at", OUT.relative_to(ROOT),
              "- append_record would refuse; not recomputing")
        return 0
    record = mult.campaign_end_record(
        campaign_id=C4, families=families, n_boot=n_boot,
        n_flips=n_flips, p_value_method=method, ledger_sha256=ledger_sha)
    mult.append_record(OUT, record)

    # -- 4. verify what was written ----------------------------------------
    written = mult.read_records(OUT)
    assert len(written) == 1 and written[0]["campaign_id"] == C4
    refuted = [m["member_id"] for fam in written[0]["families"].values()
               for m in fam["members"]
               if m["formal_status"] == mult.FORMAL_REFUTED]
    assert not refuted, f"unexpected formal refutations: {refuted}"
    total = sum(len(f["members"]) for f in written[0]["families"].values())
    statuses = {}
    for fam in written[0]["families"].values():
        for m in fam["members"]:
            statuses[m["formal_status"]] = statuses.get(
                m["formal_status"], 0) + 1
    print("APPENDED:", OUT.relative_to(ROOT))
    print("members:", total, "| formal statuses:", statuses)
    print("formal REFUTED count: 0 (fail-closed, C-2 Option A)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
