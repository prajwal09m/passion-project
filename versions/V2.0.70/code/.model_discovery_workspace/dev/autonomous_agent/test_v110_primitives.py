"""Harness v1.1.0 activation tests (owner R-3 grant, 2026-10-12).

Covers the plan's required tests for the activated primitives, on synthetic
fixtures only — no real data, no network, no holdout:

* spec-fidelity: the frozen ladder/floors/margin/family in a primitive
  definition match what the harness renders into a config (blocks post-hoc
  drift);
* three-valued evaluator per primitive, including an underpowered wide-CI
  fixture that must be INCONCLUSIVE, and an under-sized regime cell that must
  be INCONCLUSIVE;
* ladder-enum: purge/horizon/regime rungs come from the frozen enums, never
  computed at runtime;
* horizon test: each rung must rebuild labels and re-verify the maturity
  purge;
* PIT tri-state: UNVERIFIABLE never PASS, CONFIRMED halts fail-closed, and a
  disclosed Tier-2 defect is an audit FAIL (owner ruling R-4), never
  contamination;
* v1.0.0 back-compat: a config without the selector is byte-identical in
  validation, and v1.1.0 keys are refused on the v1.0.0 path;
* count-once / claim-prohibition for the mirrored complexity reanalysis.
"""
from __future__ import annotations

import unittest

from autonomous_agent import recipe_harness as harness
from autonomous_agent import three_valued as tv
from autonomous_agent.proposal_layer import compiler, primitives

FLOORS = {"min_rows": 30, "min_events": 5}
FIVE = ("purge_sensitivity_probe", "regime_split_analysis",
        "target_horizon_robustness", "complexity_reduction_check",
        "point_in_time_data_audit")


def good(rung, *, point=0.02, ci=0.005, rows=500, events=40, **extra):
    return {"rung": rung, "cell": rung, "point": point, "ci_lower": ci,
            "n_rows": rows, "n_events": events, **extra}


class FrozenLadderTests(unittest.TestCase):
    def test_every_activated_primitive_carries_a_frozen_ladder(self) -> None:
        for primitive_id in FIVE:
            primitive = primitives.get(primitive_id)
            self.assertTrue(primitive.executable, primitive_id)
            self.assertEqual(primitive.harness_min_version, "1.1.0")
            ladder = primitive.extra["frozen_ladder"]
            self.assertEqual(ladder, tv.ladder_for(primitive_id))

    def test_ladders_are_the_frozen_enums(self) -> None:
        self.assertEqual(tv.ladder_for("purge_sensitivity_probe")["rungs"], [0, 5, 10])
        self.assertEqual(tv.ladder_for("target_horizon_robustness")["rungs"], [1, 2, 3])
        self.assertEqual(tv.ladder_for("regime_split_analysis")["rungs"],
                         ["above_sma200", "below_sma200"])
        self.assertEqual(tv.ladder_for("complexity_reduction_check")["rungs"], ["primary"])

    # The ladder-family <-> multiplicity.FAMILIES agreement test lives in
    # test_multiplicity.py: the multiplicity machinery stays imported only by
    # the loop and its own tests (inertness rule).

    def test_unknown_primitive_has_no_ladder(self) -> None:
        with self.assertRaises(tv.ThreeValuedError):
            tv.ladder_for("not_a_primitive")

    def test_margins_are_marked_provisional_and_carry_a_ci_requirement(self) -> None:
        for primitive_id in FIVE:
            margin = primitives.get(primitive_id).extra["acceptance_margin"]
            self.assertTrue(margin["provisional"], primitive_id)
            self.assertIn("PROVISIONAL", margin["provenance"])
            self.assertIsNotNone(margin["ci_lower_min"])

    def test_margin_without_a_ci_requirement_is_refused(self) -> None:
        with self.assertRaises(tv.ThreeValuedError):
            tv.Margin(value=0.0, ci_lower_min=None)


class ThreeValuedEvaluatorTests(unittest.TestCase):
    def test_purge_happy_path_is_robust(self) -> None:
        result = harness.evaluate_purge_rungs(
            [good(r) for r in (0, 5, 10)], floors=FLOORS)
        self.assertEqual(result["status"], tv.ROBUST)
        self.assertFalse(result["formal_refutation"])

    def test_purge_refutation_path_is_provisional_never_formal(self) -> None:
        result = harness.evaluate_purge_rungs(
            [good(0), good(5), good(10, point=-0.05, ci=-0.03)], floors=FLOORS)
        self.assertEqual(result["status"], tv.INCONCLUSIVE)
        self.assertEqual(result["provisional_refutation_conditions"], ["purge_+10"])
        self.assertEqual(result["refutation_signal"], "unadjusted")
        self.assertEqual(result["provisional_displays_as"],
                         "provisional, not a refutation claim")
        # The bare formal label never appears anywhere in the artifact.
        self.assertNotIn(tv.FORMAL_REFUTED, str(result))

    def test_underpowered_wide_ci_fixture_is_inconclusive(self) -> None:
        # A tiny effect with a CI that straddles zero: point estimate alone
        # must never pass (H-1).
        result = harness.evaluate_regime_cells(
            [{"cell": "above_sma200", "point": 0.5, "ci_lower": -0.02,
              "n_rows": 500, "n_events": 40},
             {"cell": "below_sma200", "point": 0.5, "ci_lower": -0.02,
              "n_rows": 500, "n_events": 40}],
            floors=FLOORS)
        self.assertEqual(result["status"], tv.INCONCLUSIVE)
        statuses = {c["status"] for c in result["conditions"]}
        self.assertEqual(statuses, {tv.INCONCLUSIVE})

    def test_underpowered_wide_ci_constructor_always_inconclusive(self) -> None:
        result = tv.underpowered_wide_ci_result(
            "regime_split_analysis", name="cell", point=0.9, ci_lower=-0.5,
            n_rows=12, n_events=1)
        self.assertEqual(result.status, tv.INCONCLUSIVE)

    def test_under_sized_regime_cell_is_inconclusive_never_a_pass(self) -> None:
        # A spectacular point estimate on a 10-row cell must not pass.
        result = harness.evaluate_regime_cells(
            [{"cell": "above_sma200", "point": 0.9, "ci_lower": 0.5,
              "n_rows": 500, "n_events": 40},
             {"cell": "below_sma200", "point": 0.9, "ci_lower": 0.5,
              "n_rows": 10, "n_events": 1}],
            floors=FLOORS)
        self.assertEqual(result["status"], tv.INCONCLUSIVE)
        by_name = {c["name"]: c for c in result["conditions"]}
        self.assertEqual(by_name["cell_below_sma200"]["status"], tv.INCONCLUSIVE)
        self.assertIn("under-sized", by_name["cell_below_sma200"]["reason"])
        self.assertEqual(by_name["cell_above_sma200"]["status"], tv.ROBUST)

    def test_underpowered_event_floor_is_inconclusive(self) -> None:
        result = harness.evaluate_regime_cells(
            [good("above_sma200"), good("below_sma200", events=2)], floors=FLOORS)
        self.assertEqual(result["status"], tv.INCONCLUSIVE)
        by_name = {c["name"]: c for c in result["conditions"]}
        self.assertIn("under-powered", by_name["cell_below_sma200"]["reason"])

    def test_point_pass_with_unmet_ci_is_inconclusive_not_a_pass(self) -> None:
        result = harness.evaluate_complexity_reduction(
            {"rung": "primary", "point": 0.5, "ci_lower": -0.05,
             "n_rows": 500, "n_events": 40}, floors=FLOORS)
        self.assertEqual(result["status"], tv.INCONCLUSIVE)
        condition = result["conditions"][0]
        self.assertIn("point-estimate-only pass", condition["reason"])

    def test_horizon_happy_and_refutation_paths(self) -> None:
        rungs = [good(r, labels_rebuilt=True, maturity_purge_reverified=True)
                 for r in (1, 2, 3)]
        self.assertEqual(harness.evaluate_horizon_rungs(rungs, floors=FLOORS)["status"],
                         tv.ROBUST)
        rungs[-1] = good(3, point=-0.05, ci=-0.03, labels_rebuilt=True,
                         maturity_purge_reverified=True)
        result = harness.evaluate_horizon_rungs(rungs, floors=FLOORS)
        self.assertEqual(result["status"], tv.INCONCLUSIVE)
        self.assertIn("horizon_3", result["provisional_refutation_conditions"])

    def test_horizon_rung_must_rebuild_labels_and_reverify_purge(self) -> None:
        for broken in ({"rung": 1},                       # no rebuild flag
                       {"rung": 1, "labels_rebuilt": True}):  # purge not re-verified
            rungs = [good(r, labels_rebuilt=True, maturity_purge_reverified=True)
                     for r in (2, 3)] + [good(**broken)]
            with self.assertRaises(ValueError):
                harness.evaluate_horizon_rungs(rungs, floors=FLOORS)

    def test_complexity_result_is_never_independent_confirmation(self) -> None:
        result = harness.evaluate_complexity_reduction(
            {"rung": "primary", "point": 0.02, "ci_lower": 0.005,
             "n_rows": 500, "n_events": 40}, floors=FLOORS)
        self.assertEqual(result["status"], tv.ROBUST)
        self.assertEqual(result["related_primitive"], "model_class_comparison")
        self.assertFalse(result["independent_confirmation"])
        self.assertIn("never independent confirmation", result["disclosure"])
        # the two banned claim phrases must not appear anywhere in the artifact
        blob = str(result).lower()
        for banned in ("independently replicated", "corroborated independently"):
            self.assertNotIn(banned, blob)

    def test_complexity_wrong_rung_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            harness.evaluate_complexity_reduction(
                {"rung": "secondary", "point": 0.0, "ci_lower": 0.0}, floors=FLOORS)

    def test_rungs_may_not_be_invented_at_runtime(self) -> None:
        with self.assertRaises(ValueError):
            harness.evaluate_purge_rungs([good(r) for r in (0, 5, 15)], floors=FLOORS)
        with self.assertRaises(ValueError):
            harness.evaluate_regime_cells([good("above_sma200"), good("sideways")],
                                          floors=FLOORS)
        with self.assertRaises(ValueError):
            harness.evaluate_horizon_rungs(
                [good(r, labels_rebuilt=True, maturity_purge_reverified=True)
                 for r in (1, 2, 4)], floors=FLOORS)


class PointInTimeAuditTests(unittest.TestCase):
    def test_clean_audit(self) -> None:
        checks = {name: "CLEAN" for name in
                  tv.ladder_for("point_in_time_data_audit")["rungs"]}
        result = harness.evaluate_point_in_time_audit(checks)
        self.assertEqual(result["status"], "CLEAN")

    def test_unverifiable_never_passes(self) -> None:
        checks = {name: "CLEAN" for name in
                  tv.ladder_for("point_in_time_data_audit")["rungs"]}
        checks["source_vintage"] = "UNVERIFIABLE"
        result = harness.evaluate_point_in_time_audit(checks)
        self.assertEqual(result["status"], "UNVERIFIABLE")
        self.assertNotEqual(result["status"], "PASS")

    def test_confirmed_contamination_halts(self) -> None:
        checks = {name: "CLEAN" for name in
                  tv.ladder_for("point_in_time_data_audit")["rungs"]}
        checks["timestamps"] = "CONFIRMED_CONTAMINATION"
        result = harness.evaluate_point_in_time_audit(checks)
        self.assertEqual(result["status"], "CONFIRMED_CONTAMINATION")

    def test_audit_is_all_or_nothing(self) -> None:
        with self.assertRaises(ValueError):
            harness.evaluate_point_in_time_audit({"source_vintage": "CLEAN"})
        with self.assertRaises(ValueError):
            harness.evaluate_point_in_time_audit(
                {**{n: "CLEAN" for n in tv.ladder_for("point_in_time_data_audit")["rungs"]},
                 "made_up": "CLEAN"})

    def test_unknown_verdict_is_refused(self) -> None:
        checks = {name: "CLEAN" for name in
                  tv.ladder_for("point_in_time_data_audit")["rungs"]}
        checks["timestamps"] = "MAYBE"
        with self.assertRaises(tv.ThreeValuedError):
            harness.evaluate_point_in_time_audit(checks)

    def test_manifest_errors_block_a_clean_pass(self) -> None:
        # R-1: a census manifest with an unfrozen tolerance or a missing
        # entry (caller-supplied validation errors) turns CLEAN into
        # UNVERIFIABLE -- never PASS, never a silent clean bill.
        checks = {name: "CLEAN" for name in
                  tv.ladder_for("point_in_time_data_audit")["rungs"]}
        blocked = harness.evaluate_point_in_time_audit(
            checks, manifest_errors=["zone_base_width: unfrozen tolerance"])
        self.assertEqual(blocked["status"], "UNVERIFIABLE")
        self.assertTrue(blocked["manifest_blocked_pass"])
        clean = harness.evaluate_point_in_time_audit(checks, manifest_errors=[])
        self.assertEqual(clean["status"], "CLEAN")
        self.assertFalse(clean["manifest_blocked_pass"])

    def test_ruling_r4_tier2_defect_is_fail_never_contamination(self) -> None:
        # A mismatch on a disclosed Tier-2 column is a provenance limitation,
        # not look-ahead: FAIL, never CONFIRMED_CONTAMINATION, never PASS.
        verdict = tv.tier2_only_defect_is_fail(
            unverifiable_columns=["rsi14", "atr_pct", "zone_width_pct"],
            mismatched_columns=["rsi14"])
        self.assertEqual(verdict, "FAIL")
        # A non-Tier-2 column disagreeing IS contamination.
        self.assertEqual(tv.tier2_only_defect_is_fail(
            unverifiable_columns=["rsi14"], mismatched_columns=["daily_return"]),
            "CONFIRMED_CONTAMINATION")
        # No mismatch at all is clean.
        self.assertEqual(tv.tier2_only_defect_is_fail(
            unverifiable_columns=["rsi14"], mismatched_columns=[]), "CLEAN")


class SpecFidelityTests(unittest.TestCase):
    """The harness renders exactly what the primitive definition declares."""

    def test_rendered_config_matches_the_frozen_definition(self) -> None:
        for primitive_id in FIVE:
            primitive = primitives.get(primitive_id)
            params = {"arm": "B", "n_boot": 1000}
            if "arm_pair" in primitive.params:
                params = {"arm_pair": "A->B", "n_boot": 1000}
                if "estimator" in primitive.params:
                    params["estimator"] = "LightGBM"
            config = compiler._render_v110_config(
                {"research_question_id": "rq", "hypothesis": "h",
                 "baseline_id": "b"}, primitive, params)
            extra = primitive.extra
            self.assertEqual(config["harness_version"], "1.1.0")
            self.assertEqual(config["primitive_id"], primitive_id)
            self.assertEqual(config["evaluation_criteria"]["ci_lower_min"],
                             extra["acceptance_margin"]["ci_lower_min"])
            self.assertGreaterEqual(config["n_boot"],
                                    extra["sample_floors"]["min_boot_for_inference"])

    def test_rendered_config_is_refused_for_a_bad_primitive_or_params(self) -> None:
        primitive = primitives.get("regime_split_analysis")
        with self.assertRaises(compiler.CompileError):
            compiler._render_v110_config({}, primitive, {"arm": "Z", "n_boot": 1000})
        with self.assertRaises(compiler.CompileError):
            compiler._render_v110_config({}, primitive, {"arm": "B", "n_boot": 500})

    def test_n_boot_floor_is_enforced_at_the_primitive_spec(self) -> None:
        # H-10b: 500 is disallowed for every v1.1.0 primitive at the spec
        # level, so neither the generator grid nor a hand-built payload can
        # undercut the declared inference floor.
        for primitive_id in FIVE:
            self.assertGreaterEqual(
                primitives.get(primitive_id).params["n_boot"].low, 1000,
                primitive_id)


class BackCompatTests(unittest.TestCase):
    def test_v100_config_is_still_valid_and_untouched(self) -> None:
        base = _base_v100()
        self.assertEqual(harness.validate_experiment_config(base), [])
        self.assertNotIn("harness_version", base)

    def test_v110_keys_are_refused_on_the_v100_path(self) -> None:
        config = _base_v100()
        config["harness_version"] = "1.1.0"
        problems = harness.validate_experiment_config(config)
        self.assertTrue(any("primitive_id" in p for p in problems))

    def test_valid_v110_config_is_accepted(self) -> None:
        config = _base_v100()
        config.update({"harness_version": "1.1.0",
                       "primitive_id": "regime_split_analysis"})
        self.assertEqual(harness.validate_experiment_config(config), [])

    def test_unknown_primitive_and_version_are_refused(self) -> None:
        config = _base_v100()
        config.update({"harness_version": "1.1.0", "primitive_id": "nope"})
        self.assertTrue(harness.validate_experiment_config(config))
        config = _base_v100()
        config["harness_version"] = "9.9.9"
        self.assertTrue(harness.validate_experiment_config(config))

    def test_only_the_five_primitives_are_v110(self) -> None:
        self.assertEqual(harness.V110_PRIMITIVES, set(FIVE))


def _base_v100() -> dict:
    return {"schema_version": 1, "generator": "deterministic_compositional",
            "recipe_id": "proposal_layer", "recipe_version": "1.0.0",
            "hypothesis_id": "q", "hypothesis_text": "t", "baseline_id": "b",
            "arm_a": "A", "arm_b": "B", "estimator_a": "LogisticRegression",
            "estimator_b": "LightGBM", "seeds": [42, 43, 44], "n_boot": 500,
            "calibration_bins": 10, "folds": [2023, 2024, 2025],
            "evaluation_criteria": {"primary_metric_min_delta": 0.0,
                                    "ci_lower_min": -0.01, "min_folds": 3,
                                    "note": "n"}}


if __name__ == "__main__":
    unittest.main()
