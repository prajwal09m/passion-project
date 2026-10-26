# -*- coding: utf-8 -*-
"""The declared error_clustering_analysis primitive (Campaign 5 wiring).

Campaign 5 froze an ``error_analysis`` multiplicity family
(``error_clustering_analysis``; 2 members per experiment; member bound 20)
in ``state/campaign_config.json`` and its owner packets authorized
``add_primitives`` — but no declaration, ladder, or family binding for the
primitive existed anywhere in code, so the family could never contribute a
single member and the generator could never propose in it.

These tests pin exactly what was added and what deliberately was NOT:

1. the code's ``multiplicity.FAMILIES`` table is dict-equal to the frozen
   C5 config's ``multiplicity_policy.families`` (all five families,
   campaign-end authority consistent with the era-pinned config bytes);
2. the frozen ladder exists with its two rungs / family binding, and the
   ``three_valued.FAMILY_MEMBER_BOUNDS`` mirror carries ``error_analysis``;
3. the primitive declaration exists as ACTIVATED under the owner's A3
   countersign (FROZEN record): executable=True at harness 1.3.0, exactly
   one predeclared axis param plus the frozen matched pair, no invented
   acceptance margin, and the predeclaration-required contract;
4. the compiler's v1.3.0 renderer renders the frozen matched pair for
   exactly the five predeclared axes (one experiment per axis, no filler)
   and refuses anything else fail-closed; the generator grid is exactly
   the five axes;
5. the H-10b feasibility arithmetic holds for the family (B + 1 >= 20*m).
The boundaries that must stay intact for the rest of the library:
6. the reviewed library version string is "1.3.0" (moved under A3; the
   frozen config's 1.2.0 epoch stays untouched as history);
7. every previously executable primitive and the five activated v1.1.0
   ladder-family agreements are unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest  # noqa: F401

WORKSPACE = Path(__file__).resolve().parents[1]

import sys  # NOQA: E402
sys.path.insert(0, str(WORKSPACE))  # NOQA: E402

from autonomous_agent import three_valued as tv  # NOQA: E402
from autonomous_agent.proposal_layer import multiplicity as mult  # NOQA: E402
from autonomous_agent.proposal_layer import primitives as prims  # NOQA: E402
from autonomous_agent.proposal_layer import schema  # NOQA: E402
from autonomous_agent.proposal_layer.compiler import (  # NOQA: E402
    CompileError,
    preview_spec,
)

C5_CONFIG = WORKSPACE / "autonomous_agent" / "state" / "campaign_config.json"
# 2026-10-25 lineage re-pin (predeclared ordering: A2 freeze -> A3 activation
# commit -> lineage re-pin — see the record's implementation_lineage note):
# the era pin now binds the FROZEN, signed-and-repinned record bytes. Any
# byte change to the record fails loudly here.
C5_ERC_RECORD = (WORKSPACE / "autonomous_agent" / "MAIN AUDITS AND REFLECTIONS" /
                 "C5_ERROR_CLUSTER_PREDECLARATION_2026_10_25.json")
C5_ERC_FILE_SHA = "42a527f476b1564c"  # verified byte digest prefix of the frozen record
C5_ERC_CANONICAL_PIN = (
    "dca3e744e850d6aa")  # verified prefix of the canonical (minus 'pin') hash

PRIMITIVE_ID = "error_clustering_analysis"


def _c5_multiplicity_families() -> dict:
    config = json.loads(C5_CONFIG.read_text(encoding="utf-8"))
    return config["multiplicity_policy"]["families"]


class TestPredeclarationRecordIsEraPinned:
    """The proposed error-cluster definitions cannot drift before sign-off."""

    def _record(self) -> dict:
        return json.loads(C5_ERC_RECORD.read_text(encoding="utf-8"))

    def test_record_is_frozen_with_owner_countersign(self) -> None:
        record = self._record()
        assert record["_status"] == "FROZEN_2026_10_25"
        # countersign signed by owner
        assert record["countersign_block"]["authorized_by"] == "PMED"

    def test_declared_axes_and_generator_grid_match_the_record(self) -> None:
        import autonomous_agent.proposal_layer.generator as gen_mod
        axes = [d["experiment_axis"]
                for d in self._record()["cluster_definitions"]]
        primitive = prims.get(PRIMITIVE_ID)
        spec = primitive.params["error_cluster_axis"]
        assert spec.kind == "enum" and tuple(spec.values) == tuple(axes)
        # the generator grid is exactly the five axes, one dict each, in the
        # record's declared order (deterministic, no filler variants)
        grid = gen_mod._param_grid(primitive)
        assert [g["error_cluster_axis"] for g in grid] == axes
        assert all(set(g) == {"error_cluster_axis"} for g in grid)

    def test_record_canonical_pin_reproduces(self) -> None:
        import hashlib
        from autonomous_agent.proposal_layer.schema import canonical_json
        record = self._record()
        pin = record["pin"]
        recomputed = hashlib.sha256(
            canonical_json({k: v for k, v in record.items() if k != "pin"})
            .encode("utf-8")).hexdigest()
        assert recomputed == pin
        assert pin.startswith(C5_ERC_CANONICAL_PIN)

    def test_record_file_digest_matches_the_era_pin(self) -> None:
        import hashlib
        digest = hashlib.sha256(C5_ERC_RECORD.read_bytes()).hexdigest()
        assert digest.startswith(C5_ERC_FILE_SHA)

    def test_record_definitions_match_the_frozen_structure(self) -> None:
        record = self._record()
        assert record["evaluation_rules"]["matched_pair"] == (
            "arm_a == arm_b == C; estimator_a = LogisticRegression; "
            "estimator_b = LightGBM; identical folds, seeds, and frame "
            "for both pipelines")
        axes = [exp["experiment_axis"] for exp in record["cluster_definitions"]]
        assert axes == ["vix_regime", "first_retest", "volume_confirmation",
                        "departure_magnitude", "departure_candle_direction"]
        for exp in record["cluster_definitions"]:
            rungs = exp["rungs"]
            assert [r["rung"] for r in rungs] == [
                "error_cluster_1", "error_cluster_2"]
        # budget arithmetic in the record matches the frozen capacity
        req = record["campaign_target"]["requested_budget"]
        assert req["max_error_clustering_experiments"] * 2 == req["members_total"]
        assert req["members_total"] <= record["multiplicity"]["member_bound"]
        assert req["max_error_clustering_experiments"] <= 10

    def test_record_feasibility_arithmetic_holds(self) -> None:
        record = self._record()
        chi = record["evaluation_rules"]["member_statistic"]["ci"]
        mult = record["multiplicity"]
        m = record["campaign_target"]["requested_budget"]["members_total"]
        assert chi["n_boot"] + 1 >= 20 * m
        assert mult["campaign_end_procedure"]["feasibility_check"][
            "planned_members_m"] == m

    def test_record_derivation_policy_declares_the_firewall(self) -> None:
        policy = self._record()["derivation_policy"]
        assert "outcome" in policy["outcome_free_rule"]
        assert "intrinsic" in policy["intrinsic_threshold_rule"]
        assert "Both sides" in policy["no_favorable_side_rule"]

    def test_record_approval_items_are_explicit(self) -> None:
        cov = self._record()["coverage_analysis"]
        assert len(cov["requires_explicit_owner_approval"]) == 4
        assert cov["requires_explicit_owner_approval"][2].startswith(
            "A3: activation of the execution path")
        # not-required list may reference the holdout POLICY only as "no change
        # to ..."; and nothing there may promise access or resumption
        for item in cov["not_required"]:
            if "holdout" in item.lower():
                assert item.startswith(
                    "no change to duplicate policy, outcome-blindness policy")
        assert not any(item.lower().startswith("resume")
                       for item in cov["not_required"])
        assert cov["requires_explicit_owner_approval"][1].startswith(
            "A2: this predeclaration record itself")


class TestCodeMatchesTheFrozenConfig:
    def test_families_table_is_dict_equal_to_the_frozen_config(self) -> None:
        # The frozen campaign config declares five families; before 2026-10-25
        # the code's table only had four. This is now closed, and any future
        # drift between the code table and the frozen-era table fails loudly.
        assert mult.FAMILIES == _c5_multiplicity_families()

    def test_error_analysis_family_member_counts_are_the_declared_ones(self) -> None:
        declared = _c5_multiplicity_families()["error_analysis"]
        assert declared == {"primitive": PRIMITIVE_ID,
                            "members_per_experiment": 2, "member_bound": 20}
        assert mult.FAMILIES["error_analysis"] == declared
        assert mult.PRIMITIVE_TO_FAMILY[PRIMITIVE_ID] == "error_analysis"

    def test_library_version_string_is_1_3_0(self) -> None:
        # The frozen-era config pins primitive_library_version = "1.2.0",
        # but the owner's A3 authorization approves the harness 1.3.0 changes,
        # which include the error_cluster collector and executor. The library
        # version moves to 1.3.0 to reflect this reviewed change.
        assert schema.PRIMITIVE_LIBRARY_VERSION == "1.3.0"


class TestFrozenLadderAndBounds:
    def test_ladder_is_enumerated_and_frozen(self) -> None:
        ladder = tv.ladder_for(PRIMITIVE_ID)
        assert ladder["kind"] == "error_cluster"
        assert ladder["rungs"] == ["error_cluster_1", "error_cluster_2"]
        assert ladder["unit"] == "cluster"
        assert ladder["members_per_experiment"] == 2
        assert ladder["family"] == "error_analysis"

    def test_family_bounds_mirror_carries_error_analysis(self) -> None:
        assert tv.FAMILY_MEMBER_BOUNDS["error_analysis"] == 20
        assert tv.FAMILY_MEMBER_BOUNDS["error_analysis"] == \
            _c5_multiplicity_families()["error_analysis"]["member_bound"]

    def test_ladder_members_match_the_family_declaration(self) -> None:
        ladder = tv.ladder_for(PRIMITIVE_ID)
        declared = mult.FAMILIES["error_analysis"]
        assert ladder["members_per_experiment"] == \
            declared["members_per_experiment"]


class TestPrimitiveDeclaration:
    def test_declaration_exists_with_declared_contract(self) -> None:
        primitive = prims.get(PRIMITIVE_ID)
        assert primitive is not None
        assert primitive.executable is True  # Changed to True per A3 authorization
        assert primitive.harness_min_version == "1.3.0"
        assert primitive.direction == "error_analysis"
        assert primitive.falsification_capable is False
        assert primitive.accepts_arm is False
        # Exactly one predeclared-axis param; the matched pair and the
        # n_boot floor live in the frozen extra (never a generator knob).
        assert set(primitive.params) == {"error_cluster_axis"}
        assert primitive.params["error_cluster_axis"].kind == "enum"
        pair = primitive.extra["matched_pair"]
        assert pair["arm_a"] == pair["arm_b"] == "C"
        assert pair["estimator_a"] == "LogisticRegression"
        assert pair["estimator_b"] == "LightGBM"
        assert pair["seeds"] == [42, 43, 44] and pair["n_boot"] == 2000

    def test_no_acceptance_margin_is_invented(self) -> None:
        # A dormant primitive must not fabricate a pass/fail boundary that
        # the owner never predeclared (H-1).
        assert prims.get(PRIMITIVE_ID).extra["acceptance_margin"] is None

    def test_predeclaration_required_contract_is_recorded(self) -> None:
        extra = prims.get(PRIMITIVE_ID).extra["predeclaration_required"]
        assert "owner-predeclared" in extra
        assert "fail-closed" in extra
        # The substantive firewall claim: no cluster rule may be invented
        # from outcomes at runtime.
        assert "no cluster rule may be derived from outcomes" in extra

    def test_extra_ladder_and_family_cannot_drift(self) -> None:
        extra = prims.get(PRIMITIVE_ID).extra
        assert extra["frozen_ladder"] == tv.ladder_for(PRIMITIVE_ID)
        assert extra["multiplicity"]["family"] == "error_analysis"
        assert extra["multiplicity"]["members_per_experiment"] == \
            tv.ladder_for(PRIMITIVE_ID)["members_per_experiment"]

    def test_h10b_feasibility_holds_for_the_new_family(self) -> None:
        # B + 1 >= 20 * m for the family's MemberSpec (2 members, bound 20)
        # with the frozen matched pair's n_boot (B = 2000, B + 1 = 2001).
        primitive = prims.get(PRIMITIVE_ID)
        n_boot = primitive.extra["matched_pair"]["n_boot"]
        declared = mult.FAMILIES["error_analysis"]
        m = declared["members_per_experiment"]
        assert n_boot >= mult.MIN_N_BOOT
        assert n_boot + 1 >= 20 * m
        assert declared["member_bound"] <= mult.MAX_FAMILY_SIZE_M


class TestFirewallAndGeneratorExclusion:
    def test_compiler_renders_the_frozen_matched_pair(self) -> None:
        # After A3 authorization the compiler has a v1.3.0 renderer: it
        # copies the frozen matched pair and the one predeclared axis into a
        # config that passes the closed harness contract, for every axis.
        from autonomous_agent.proposal_layer.compiler import _render_config
        from autonomous_agent.recipe_harness import (
            validate_experiment_config)
        primitive = prims.get(PRIMITIVE_ID)
        payload = {"research_question_id": "hyp-erc-range-test",
                   "hypothesis": "Range-test hypothesis text.",
                   "baseline_id": "b"}
        for axis in primitive.params["error_cluster_axis"].values:
            config = _render_config(payload, primitive,
                                    {"error_cluster_axis": axis})
            assert validate_experiment_config(config) == []
            assert config["harness_version"] == "1.3.0"
            assert config["error_cluster_axis"] == axis
            assert config["arm_a"] == config["arm_b"] == "C"
            assert (config["estimator_a"], config["estimator_b"]) == \
                ("LogisticRegression", "LightGBM")
            assert config["n_boot"] == 2000
            assert config["seeds"] == [42, 43, 44]
            assert config["folds"] == [2023, 2024, 2025]

    def test_compiler_refuses_an_unpredeclared_axis(self) -> None:
        from autonomous_agent.proposal_layer.compiler import (
            CompileError, _render_config)
        primitive = prims.get(PRIMITIVE_ID)
        payload = {"research_question_id": "rq", "hypothesis": "h",
                   "baseline_id": "b"}
        with pytest.raises(CompileError):
            _render_config(payload, primitive,
                           {"error_cluster_axis": "not_predeclared"})

    def test_generator_can_select_the_enabled_primitive(self) -> None:
        # After A3 authorization, the primitive is executable=True and
        # the generator can select it when allow_future_primitives=false.
        import autonomous_agent.proposal_layer.generator as gen  # NOQA: E402
        bias_policy = json.loads(
            (WORKSPACE / "autonomous_agent" / "proposal_layer" / "bias_policy.json")
            .read_text(encoding="utf-8"))
        assert bias_policy["allow_future_primitives"] is False
        enabled = prims.get(PRIMITIVE_ID)
        assert enabled.executable is True
        # The generator's governing loop condition, mirrored directly: the
        # primitive is included when executable=True
        selection_would_include = (
            enabled.executable or bias_policy["allow_future_primitives"])
        assert selection_would_include is True


class TestBackwardCompatibility:
    def test_previously_executable_primitives_are_unchanged(self) -> None:
        must_stay_executable = (
            "feature_arm_comparison", "model_class_comparison",
            "calibration_stability_check", "year_stability_falsifier",
            "minimum_effect_falsifier", "complexity_premium_check",
            "seed_set_replication", "point_in_time_data_audit",
            "purge_sensitivity_probe", "regime_split_analysis",
            "complexity_reduction_check", "target_horizon_robustness",
        )
        for primitive_id in must_stay_executable:
            assert prims.get(primitive_id).executable is True

    def test_the_five_activated_v110_ladder_family_agreements_hold(self) -> None:
        activated = ("purge_sensitivity_probe", "regime_split_analysis",
                     "complexity_reduction_check", "target_horizon_robustness",
                     "point_in_time_data_audit")
        for primitive_id in activated:
            extra = prims.get(primitive_id).extra
            ladder = tv.ladder_for(primitive_id)
            assert extra["frozen_ladder"] == ladder
            family = extra["multiplicity"]["family"]
            if family is None:
                assert primitive_id == "point_in_time_data_audit"
                continue
            declared = mult.FAMILIES[family]
            assert declared["primitive"] == primitive_id
            assert declared["members_per_experiment"] == \
                ladder["members_per_experiment"]

    def test_excluded_primitives_pooling_rule_unchanged(self) -> None:
        # The dormant primitive is NOT in the exclusion set: when it eventually
        # executes, its family feeding goes through its declared family, not
        # through the "never pooled" gate.
        assert PRIMITIVE_ID not in mult.EXCLUDED_PRIMITIVES


class TestOofFrameMaskColumns:
    """Pins the 2026-10-25 OOF-projection defect fix.

    The pooled OOF projection must carry every event-table column that the
    selected axis's frozen rung masks reference, otherwise no mask can be
    evaluated, the collector raises, the harness exits 1 before writing
    evaluation.json, and the diagnostic is adjudicated with all evidence
    gates missing (observed live on rows exp-proposal-5d1d8cf4cc6e et al.).
    """

    EXPECTED = {
        "vix_regime": ("vix_percentile_60d",),
        "first_retest": ("zone_is_first_retest",),
        "volume_confirmation": ("relative_volume20",),
        "departure_magnitude": ("zone_departure_atr_multiple",),
        "departure_candle_direction": ("bullish_candle",),
    }

    def _helper(self):
        from autonomous_agent.recipe_harness import _cluster_axis_columns
        return _cluster_axis_columns

    def test_every_predeclared_axis_masks_on_its_declared_columns(self) -> None:
        helper = self._helper()
        for axis, expected in self.EXPECTED.items():
            assert helper({"error_cluster_axis": axis}) == expected

    def test_non_error_cluster_configs_get_no_extra_columns(self) -> None:
        helper = self._helper()
        assert helper({}) == ()
        assert helper({"error_cluster_axis": "not_predeclared"}) == ()

    def test_every_mask_column_exists_in_the_frozen_event_table(self) -> None:
        header = (WORKSPACE / "study_files" / "outputs" / "study_v1"
                  / "development" / "event_table.csv")
        with header.open(encoding="utf-8") as stream:
            columns = set(stream.readline().strip().split(","))
        for axis, mask_columns in self.EXPECTED.items():
            for column in mask_columns:
                assert column in columns, (axis, column)
