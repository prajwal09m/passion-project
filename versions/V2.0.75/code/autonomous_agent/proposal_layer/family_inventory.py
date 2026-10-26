"""Campaign-family inventory reconstruction from the proposal ledger.

Read-only evidence module: rebuilds, for one campaign, which proposal classes
and primitive designs were actually adjudicated, which declared multiplicity
family(ies) they belong to, and which primitives fall under the frozen
``primitives_not_named_above`` pooling exclusion. This is the input an
auditor needs to see the family that *would* have entered a campaign-end
multiplicity record (H-6), without computing any correction:

* no p-values, no Holm thresholds, no adjusted decisions are computed here;
* no formal status is emitted — the provisional/refutation firewall
  (``multiplicity.assert_firewall_intact``) applies to any artifact produced
  from this inventory;
* the reconstruction is deliberately conservative about per-experiment
  member multipliers (``members_per_experiment`` is reported as declared, but
  the executed member count is *not* invented where the family collection
  ran at zero executions).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from autonomous_agent.proposal_layer.multiplicity import (  # noqa: E402
    assert_firewall_intact,
)

LEDGER_REL = "autonomous_agent/state/proposal_ledger.jsonl"
RECORD_REL = "autonomous_agent/state/campaign_end_multiplicity.jsonl"


def read_ledger_rows(path: Path | str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    text = Path(path).read_text(encoding="utf-8")
    for raw in text.splitlines():
        if raw.strip():
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError:
                continue  # ignore torn trailing write; ledger appends are line-atomic
    rows.sort(key=lambda row: str(row.get("at", "")))
    return rows


def _campaign_rows(rows: list[dict[str, Any]], campaign_id: str) -> tuple[
        dict[str, dict[str, Any]], dict[str, list[tuple[str, str, str, str | None]]]]:
    proposals: dict[str, dict[str, Any]] = {}
    transitions: dict[str, list[tuple[str, str, str, str | None]]] = defaultdict(list)
    for row in rows:
        if row.get("row_type") == "proposal":
            payload = row.get("proposal") or {}
            if str(payload.get("campaign_id")) == campaign_id:
                proposals[str(row.get("proposal_id"))] = payload
        elif row.get("row_type") == "transition":
            transitions[str(row.get("proposal_id"))].append((
                str(row.get("at", "")), str(row.get("from", "")),
                str(row.get("to", "")), row.get("reason_code")))
    return proposals, transitions


def _primitive_ids(payload: Mapping[str, Any]) -> list[str]:
    design = payload.get("design") or {}
    return [str(item.get("primitive_id"))
            for item in (design.get("primitives") or []) if item.get("primitive_id")]


def _declared_families(policy: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    families = (policy or {}).get("families") or {}
    return {str(name): dict(spec) for name, spec in families.items()}


def campaign_family_inventory(campaign: Mapping[str, Any],
                              ledger_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Reconstruct the executed family inventory for one frozen campaign."""
    campaign_id = str(campaign.get("campaign_id", ""))
    proposals, transitions = _campaign_rows(ledger_rows, campaign_id)
    policy = campaign.get("multiplicity_policy") or {}
    declared = _declared_families(policy)
    primitive_to_family: dict[str, list[str]] = defaultdict(list)
    for family, spec in declared.items():
        primitive_to_family[str(spec.get("primitive"))].append(family)

    members: list[dict[str, Any]] = []
    class_counts: Counter[str] = Counter()
    primitive_counts: Counter[str] = Counter()
    for proposal_id in sorted(proposals):
        payload = proposals[proposal_id]
        end_transitions = transitions.get(proposal_id) or []
        final_status = end_transitions[-1][2] if end_transitions else "PROPOSED"
        proposal_class = str(payload.get("proposal_class") or "")
        class_counts[proposal_class] += 1
        primitives = _primitive_ids(payload)
        for primitive in primitives:
            primitive_counts[primitive] += 1
        families_hit = sorted({family
                               for primitive in primitives
                               for family in primitive_to_family.get(primitive, [])})
        excluded = bool(primitives) and not families_hit
        members.append({
            "proposal_id": proposal_id,
            "proposal_class": proposal_class,
            "primitives": primitives,
            "declared_families": families_hit,
            "pooling_exclusion": excluded,
            "final_status": final_status,
        })

    executed_by_family: dict[str, list[str]] = defaultdict(list)
    for member in members:
        for family in member["declared_families"]:
            executed_by_family[family].append(member["proposal_id"])

    family_view = {}
    for family, spec in declared.items():
        executed = executed_by_family.get(family, [])
        family_view[family] = {
            "declared_primitive": spec.get("primitive"),
            "declared_member_bound": spec.get("member_bound"),
            "declared_members_per_experiment": spec.get("members_per_experiment"),
            "experiments_executed": len(executed),
            "proposal_ids": executed,
        }

    excluded_view = dict(Counter(m["primitives"][0] for m in members
                                 if m["pooling_exclusion"] and m["primitives"]))
    inventory = {
        "campaign_id": campaign_id,
        "declared_correction": policy.get("correction"),
        "declared_pooling": policy.get("pooling"),
        "declared_pooling_exclusions": policy.get("pooling_exclusions"),
        "campaign_end_record_required": policy.get("campaign_end_record_required"),
        "proposals_adjudicated": len(members),
        "proposal_classes": dict(class_counts),
        "primitive_execution_counts": dict(primitive_counts),
        "declared_families": family_view,
        "primitives_not_named_above": excluded_view,
        "members": members,
        "multiplicity_record_coverage": "unknown_caller",  # filled by CLI
        "record_row": None,
    }
    # firewall: the inventory must never carry (or be built over) formal labels
    assert_firewall_intact(inventory, context="campaign_family_inventory")
    return inventory


def check_record_coverage(inventory: dict[str, Any], records_path: Path | str) -> None:
    records_path = Path(records_path)
    covered = None
    if records_path.is_file():
        import autonomous_agent.proposal_layer.multiplicity as mp
        for row in mp.read_records(records_path):
            if str(row.get("campaign_id")) == inventory["campaign_id"]:
                covered = row
                break
    inventory["multiplicity_record_coverage"] = (
        "covered" if covered is not None else
        ("missing_record_pool" if inventory.get("declared_pooling") else "none_declared"))
    inventory["record_row"] = covered


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="autonomous_agent.proposal_layer.family_inventory",
        description="Reconstruct the executed multiplicity-family inventory "
                    "for one campaign (read-only evidence).")
    parser.add_argument("--root", default=".")
    parser.add_argument("--config", default="autonomous_agent/state/campaign_config.json")
    parser.add_argument("--ledger", default="autonomous_agent/state/proposal_ledger.jsonl")
    parser.add_argument("--records", default="autonomous_agent/state/campaign_end_multiplicity.jsonl")
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--out", default=None, help="write JSON here (stdout otherwise)")
    args = parser.parse_args(argv)
    root = Path(args.root)
    campaign = json.loads((root / args.config).read_text(encoding="utf-8"))
    if str(campaign.get("campaign_id")) != args.campaign:
        raise SystemExit(f"--campaign must match the live config "
                         f"({campaign.get('campaign_id')})")
    rows = read_ledger_rows(root / args.ledger)
    inventory = campaign_family_inventory(campaign, rows)
    check_record_coverage(inventory, root / args.records)
    payload = json.dumps(inventory, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        out = root / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8", newline="\n")
        print(f"written: {out.as_posix()}")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
