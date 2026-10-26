"""Tests for the read-only family inventory and the H-6 stop-time guard.

Synthetic coverage uses a small hand-built ledger; the era-pinned test reads
the real campaign-5 ledger (skipped when the local state is absent) so the
reconstruction cannot silently drift from the recorded campaign facts.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from autonomous_agent.proposal_layer.family_inventory import (
    campaign_family_inventory,
    check_record_coverage,
    read_ledger_rows,
)
from autonomous_agent.proposal_layer.multiplicity import campaign_end_gap_status

WORKSPACE = Path(__file__).resolve().parents[1]


def synthetic_campaign() -> dict:
    return {
        "campaign_id": "campaign-test-2026-10-25",
        "multiplicity_policy": {
            "correction": "holm_step_down",
            "pooling": "campaign_end_over_complete_family",
            "pooling_exclusions": ["campaign_1_2_3_4_tests", "primitives_not_named_above"],
            "campaign_end_record_required": True,
            "no_multiplicity_record_outcome": "INCONCLUSIVE",
            "families": {
                "purge": {"primitive": "purge_sensitivity_probe",
                          "member_bound": 36, "members_per_experiment": 3},
                "complexity": {"primitive": "complexity_reduction_check",
                               "member_bound": 12, "members_per_experiment": 1},
            },
        },
    }


def synthetic_rows() -> list[dict]:
    def proposal(pid: str, cls: str, campaign: str, primitives: list[str]) -> dict:
        slot = {"prop-1": 1, "prop-2": 2, "prop-3": 3, "prop-x": 4}[pid]
        return {"row_type": "proposal", "at": f"2026-10-25T00:0{slot}:00:00+00:00",
                "proposal_id": pid,
                "proposal": {"proposal_class": cls, "campaign_id": campaign,
                             "design": {"primitives": [{"primitive_id": p} for p in primitives]}}}

    def transition(pid: str, at: str, frm: str, to: str) -> dict:
        return {"row_type": "transition", "at": at, "proposal_id": pid,
                "from": frm, "to": to, "reason_code": None}

    return [
        proposal("prop-1", "falsification", "campaign-test-2026-10-25", ["purge_sensitivity_probe"]),
        transition("prop-1", "2026-10-25T02:00:00+00:00", "EXECUTED", "ADJUDICATED"),
        proposal("prop-2", "confirmatory", "campaign-test-2026-10-25", ["complexity_reduction_check"]),
        transition("prop-2", "2026-10-25T02:00:01+00:00", "ADJUDICATED", "PROMOTED"),
        proposal("prop-3", "falsification", "campaign-test-2026-10-25", ["minimum_effect_falsifier"]),
        transition("prop-3", "2026-10-25T02:00:02+00:00", "EXECUTED", "ADJUDICATED"),
        # another campaign whose rows must be entirely invisible here
        proposal("prop-x", "falsification", "campaign-other-2026", ["purge_sensitivity_probe"]),
    ]


def test_inventory_classifies_declared_and_excluded_members() -> None:
    inventory = campaign_family_inventory(synthetic_campaign(), synthetic_rows())
    assert inventory["proposals_adjudicated"] == 3  # foreign campaign invisible
    assert inventory["proposal_classes"] == {"falsification": 2, "confirmatory": 1}
    purge = inventory["declared_families"]["purge"]
    comp = inventory["declared_families"]["complexity"]
    assert purge["experiments_executed"] == 1
    assert purge["proposal_ids"] == ["prop-1"]
    assert comp["proposal_ids"] == ["prop-2"]
    assert inventory["primitives_not_named_above"] == {"minimum_effect_falsifier": 1}


def test_final_status_comes_from_the_last_transition() -> None:
    inventory = campaign_family_inventory(synthetic_campaign(), synthetic_rows())
    final = {m["proposal_id"]: m["final_status"] for m in inventory["members"]}
    assert final["prop-2"] == "PROMOTED"
    assert final["prop-1"] == "ADJUDICATED"
    # no formal labels exist anywhere in the inventory
    dumped = json.dumps(inventory)
    assert "REFUTED" not in dumped


def test_record_coverage_reports_missing_and_covered(tmp_path: Path) -> None:
    inventory = campaign_family_inventory(synthetic_campaign(), synthetic_rows())
    check_record_coverage(inventory, tmp_path / "none.jsonl")
    assert inventory["multiplicity_record_coverage"] == "missing_record_pool"
    record = {"record_type": "campaign_end_multiplicity",
              "campaign_id": "campaign-test-2026-10-25"}
    path = tmp_path / "records.jsonl"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    other = campaign_family_inventory(synthetic_campaign(), synthetic_rows())
    check_record_coverage(other, path)
    assert other["multiplicity_record_coverage"] == "covered"


def test_gap_status_declared_policy_missing_record(tmp_path: Path) -> None:
    campaign = synthetic_campaign()
    records = tmp_path / "campaign_end_multiplicity.jsonl"
    gap = campaign_end_gap_status(campaign, records)
    assert gap is not None
    assert gap["campaign_id"] == "campaign-test-2026-10-25"
    assert gap["outcome"] == "INCONCLUSIVE"
    assert "provisional" in gap["consequence"]
    # covered -> None
    records.write_text(json.dumps({
        "record_type": "campaign_end_multiplicity",
        "campaign_id": campaign["campaign_id"]}) + "\n", encoding="utf-8")
    assert campaign_end_gap_status(campaign, records) is None
    # policy not requiring a record -> None
    campaign["multiplicity_policy"]["campaign_end_record_required"] = False
    assert campaign_end_gap_status(campaign, tmp_path / "absent.jsonl") is None


def test_gap_status_c5_live_state_is_machine_evisible() -> None:
    """Era-pinned: the live C5 config declares INCONCLUSIVE for a missing
    record, and the real multiplicity journal has no campaign-5 row."""
    config_path = WORKSPACE / "autonomous_agent/state/campaign_config.json"
    records_path = WORKSPACE / "autonomous_agent/state/campaign_end_multiplicity.jsonl"
    if not config_path.is_file():
        pytest.skip("live campaign config unavailable in this checkout")
    campaign = json.loads(config_path.read_text(encoding="utf-8"))
    if not str(campaign.get("campaign_id", "")).startswith("campaign-5"):
        pytest.skip("live config is not campaign-5 in this checkout")
    gap = campaign_end_gap_status(campaign, records_path)
    assert gap is not None
    assert gap["outcome"] == "INCONCLUSIVE"


def test_era_pinned_c5_reconstruction_matches_recorded_facts() -> None:
    """The provisional/refutation firewall applies to any inventory artifact."""
    ledger = WORKSPACE / "autonomous_agent/state/proposal_ledger.jsonl"
    config = WORKSPACE / "autonomous_agent/state/campaign_config.json"
    if not ledger.is_file() or not config.is_file():
        pytest.skip("live ledger/config unavailable in this checkout")
    campaign = json.loads(config.read_text(encoding="utf-8"))
    if not str(campaign.get("campaign_id", "")).startswith("campaign-5"):
        pytest.skip("live config is not campaign-5 in this checkout")
    inventory = campaign_family_inventory(campaign, read_ledger_rows(ledger))
    assert inventory["proposals_adjudicated"] == 23
    assert inventory["proposal_classes"] == {
        "confirmatory": 10, "falsification": 7, "exploration": 3, "replication": 3}
    families = inventory["declared_families"]
    assert families["purge"]["experiments_executed"] == 1
    assert families["complexity"]["experiments_executed"] == 1
    assert families["error_analysis"]["experiments_executed"] == 0
    assert families["horizon"]["experiments_executed"] == 0
    assert families["regime"]["experiments_executed"] == 0
    assert inventory["primitives_not_named_above"] == {
        "minimum_effect_falsifier": 7, "year_stability_falsifier": 4,
        "complexity_premium_check": 4, "point_in_time_data_audit": 3,
        "seed_set_replication": 3}
    assert json.dumps(inventory).count("REFUTED") == 0
