"""Campaign 2 Stage 4 — capability expansion: the 17-point requirement matrix.

Every new primitive must satisfy all 17 points before it may exist in the
reviewed library. Each point maps to its enforcement test(s):

    #  Requirement                            Test(s)
    -  -------------------------------------  -------------------------------
    1  Deterministic (no randomness / LLM)    test_01_generation_deterministic
    2  Bounded parameter grid                 test_01, test_02_bounds_checked
    3  No free-form values                    test_02, test_10
    4  Executable TODAY (config-expressible)  test_03_renders_closed_config
    5  harness_min_version honest             test_03, test_19
    6  Closed harness config compatible       test_03, test_04
    7  Structural mapping only (no free code) test_04_structural_mapping_only
    8  Distinct design signature              test_15_signatures_and_duplicates
    9  Falsifiable rule that can fail         test_13
   10  Null/adverse-capable outcome           test_13
   11  Evidence-grounded (hashed citations)   test_14_provenance_and_blindness
   12  Holdout-blind                          test_12
   13  Outcome-blind selection                test_14
   14  Budget/quota accounting compatible     test_16
   15  Duplicate layers compatible            test_15
   16  Lifecycle + provenance to compile      test_17
   17  Reproducible (byte-identical)          test_18, test_01

Adversarial points (free numeric margins, unknown profiles, unknown params,
code/path-shaped library data, out-of-bounds profiles) are test_07..test_11.

Everything runs on disposable fixtures; nothing executes.
"""
from __future__ import annotations

import dataclasses
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from autonomous_agent.proposal_layer import (
    bias_governor, compiler, generator, primitives, schema, validator,
)
from autonomous_agent.proposal_layer.primitives import LIBRARY, get as get_primitive
from autonomous_agent.recipe_harness import ALLOWED_CONFIG_KEYS, validate_experiment_config
from autonomous_agent.test_proposal_layer import (
    CAMPAIGN1_ATTEMPTS, FIXED_CLOCK, base_policy, build_fixture,
)

NEW_PRIMITIVES = ("minimum_effect_falsifier", "complexity_premium_check",
                  "seed_set_replication")

PARAM_SETS = {
    "minimum_effect_falsifier": {"arm_pair": "C->D",
                                 "estimator": "LogisticRegression",
                                 "n_boot": 500, "min_effect": "meaningful"},
    "complexity_premium_check": {"arm": "C", "n_boot": 1000,
                                 "premium": "high"},
    "seed_set_replication": {"arm_pair": "B->C", "estimator": "LightGBM",
                             "n_boot": 500},
}

RECIPE_MAP = {"feature_arm_nested_ablation": "feature_arm_comparison",
              "model_class_matched_comparison": "model_class_comparison",
              "calibration_stability_check": "calibration_stability_check"}


class Stage4Case(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="stage4_cap_"))
        self.root = self.tmp / "ws"
        self.root.mkdir(parents=True)
        build_fixture(self.root)
        from autonomous_agent.proposal_layer import evidence_view, ledger
        self.ledger = ledger.ProposalLedger(
            self.root / "autonomous_agent/state/proposal_ledger.jsonl",
            clock=FIXED_CLOCK)
        self.view = evidence_view.build(
            self.root, clock=FIXED_CLOCK,
            ledger_rows=self.ledger.read_rows())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make_payload(self, primitive_id, params=None, proposal_class="falsification"):
        payload = generator.payload_for(
            self.view, primitive_id, params or PARAM_SETS[primitive_id],
            proposal_class)
        payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
        return payload

    def validate(self, payload, policy=None, proposal_id=None):
        return validator.validate_proposal(
            payload, root=self.root, view=self.view,
            merged_history=self.ledger.all_proposals(),
            policy=policy or base_policy(), proposal_id=proposal_id)

    # -- 1/2: determinism and bounded grids ---------------------------------
    def test_01_generation_deterministic(self):
        from autonomous_agent.proposal_layer.generator import _param_grid
        # 2026-10-15 owner-directed candidate-space expansion (generator
        # v1.1.0): the n_boot grid now also emits the reviewed bucket-l
        # point (2000), so each n_boot-bearing grid is 3/2 the old size
        # (24->36, 16->24, 12->18). Boundedness, purity, ordering, and
        # determinism below are asserted exactly as before; the grid is
        # still a finite cross product of reviewed, in-bounds values.
        expected = {"minimum_effect_falsifier": 36,
                    "complexity_premium_check": 24,
                    "seed_set_replication": 18}
        for primitive_id, size in expected.items():
            primitive = get_primitive(primitive_id)
            grid = _param_grid(primitive)
            self.assertEqual(len(grid), size, primitive_id)
            self.assertEqual(grid, _param_grid(primitive))  # pure, ordered
        policy = base_policy()
        first = generator.generate_proposals(self.view, policy, seed=11, limit=6)
        second = generator.generate_proposals(self.view, policy, seed=11, limit=6)
        self.assertEqual(json.dumps(first, sort_keys=True, default=str),
                         json.dumps(second, sort_keys=True, default=str))
        self.assertTrue(first)

    # -- 2/3: bounds and no free-form values --------------------------------
    def test_02_bounds_checked(self):
        from autonomous_agent.proposal_layer.generator import _param_grid
        for primitive_id in NEW_PRIMITIVES:
            primitive = get_primitive(primitive_id)
            self.assertTrue(primitive.executable, primitive_id)
            for params in _param_grid(primitive):
                self.assertEqual(
                    primitives.validate_params(primitive_id, params), [],
                    params)
                for key, value in params.items():
                    spec = primitive.params[key]
                    if spec.kind == "int":
                        self.assertTrue(spec.low <= value <= spec.high)
                    else:
                        self.assertIn(value, spec.values)
                    text = str(value)
                    self.assertFalse(schema.looks_like_code(text), text)
                    self.assertFalse(schema.looks_like_path(text), text)

    # -- 4/5/6: renders into the existing closed harness config -------------
    def test_03_renders_closed_config(self):
        for primitive_id in NEW_PRIMITIVES:
            primitive = get_primitive(primitive_id)
            self.assertEqual(primitive.harness_min_version, "1.0.0")
            payload = self.make_payload(primitive_id)
            spec = compiler.preview_spec(payload, root=self.root)
            spec.validate()
            config = json.loads(spec.changes()[-1].content)
            self.assertEqual(validate_experiment_config(config), [],
                             primitive_id)
            self.assertEqual(set(config), set(ALLOWED_CONFIG_KEYS))
        # Seed sets: primary default everywhere except the replication
        # primitive's independent predeclared seed set.
        cfg = json.loads(compiler.preview_spec(
            self.make_payload("seed_set_replication"),
            root=self.root).changes()[-1].content)
        self.assertEqual(cfg["seeds"], [7, 17, 29])
        for primitive_id in ("minimum_effect_falsifier",
                             "complexity_premium_check"):
            cfg = json.loads(compiler.preview_spec(
                self.make_payload(primitive_id),
                root=self.root).changes()[-1].content)
            self.assertEqual(cfg["seeds"], [42, 43, 44])

    # -- 7: structural mapping only -----------------------------------------
    def test_04_structural_mapping_only(self):
        payload = self.make_payload("complexity_premium_check")
        spec = compiler.preview_spec(payload, root=self.root)
        code_files = spec.changes()[:2]
        joined = "\n".join(entry.content for entry in code_files)
        for token in ("premium", "primary_metric_min_delta",
                      "criteria_by_param"):
            self.assertNotIn(token, joined)
        # The protocol the spec declares is exactly the criteria the config
        # carries: provenance can never disagree with what the harness runs.
        config = json.loads(spec.changes()[-1].content)
        self.assertEqual(spec.evaluation_protocol["acceptance_criteria"],
                         config["evaluation_criteria"])

    # -- 5/6: legacy primitives unchanged (regression) ----------------------
    def test_05_existing_primitives_render_unchanged(self):
        cases = {
            "feature_arm_comparison": (
                {"arm_pair": "C->D", "estimator": "LogisticRegression",
                 "n_boot": 1500},
                {"primary_metric_min_delta": 0.0, "ci_lower_min": -0.01,
                 "min_folds": 3}, [42, 43, 44]),
            "calibration_stability_check": (
                {"arm_pair": "B->C", "estimator": "LightGBM",
                 "calibration_bins": 5, "n_boot": 500},
                {"primary_metric_min_delta": 0.0, "ci_lower_min": -0.01,
                 "min_folds": 3, "max_brier_degradation": 0.005,
                 "max_ece_degradation": 0.02}, [42, 43, 44]),
            "model_class_comparison": (
                {"arm": "B", "n_boot": 500},
                {"primary_metric_min_delta": 0.0, "ci_lower_min": -0.01,
                 "min_folds": 3}, [42, 43, 44]),
            "year_stability_falsifier": (
                {"arm_pair": "A->B", "estimator": "LightGBM", "n_boot": 500},
                {"primary_metric_min_delta": 0.0, "ci_lower_min": -0.01,
                 "min_folds": 3}, [42, 43, 44]),
        }
        for primitive_id, (params, criteria, seeds) in cases.items():
            payload = self.make_payload(primitive_id, params)
            config = json.loads(compiler.preview_spec(
                payload, root=self.root).changes()[-1].content)
            self.assertEqual(config["seeds"], seeds, primitive_id)
            self.assertEqual(config["evaluation_criteria"]["note"],
                             get_primitive(primitive_id).config_note,
                             primitive_id)
            for key, value in criteria.items():
                self.assertEqual(config["evaluation_criteria"][key], value,
                                 (primitive_id, key))

    # -- criteria profiles map to reviewed margins --------------------------
    def test_06_criteria_profiles_map_to_reviewed_margins(self):
        cases = {
            "minimum_effect_falsifier": [
                ({**PARAM_SETS["minimum_effect_falsifier"],
                  "min_effect": "meaningful"}, 0.005),
                ({**PARAM_SETS["minimum_effect_falsifier"],
                  "min_effect": "strong"}, 0.01)],
            "complexity_premium_check": [
                ({**PARAM_SETS["complexity_premium_check"],
                  "premium": "standard"}, 0.005),
                ({**PARAM_SETS["complexity_premium_check"],
                  "premium": "high"}, 0.01)],
        }
        for primitive_id, expectations in cases.items():
            for params, expected_delta in expectations:
                payload = self.make_payload(primitive_id, params)
                config = json.loads(compiler.preview_spec(
                    payload, root=self.root).changes()[-1].content)
                self.assertEqual(
                    config["evaluation_criteria"]["primary_metric_min_delta"],
                    expected_delta, (primitive_id, params))
                self.assertLessEqual(abs(expected_delta), 1.0)

    # -- adversarial: free numeric margins, unknown profiles/params ---------
    def test_07_free_numeric_margin_refused(self):
        payload = self.make_payload(
            "minimum_effect_falsifier",
            {**PARAM_SETS["minimum_effect_falsifier"], "min_effect": 0.5})
        report = self.validate(payload)
        self.assertFalse(report.passed)
        self.assertEqual(report.failed_gate, schema.GATE_SURFACE)
        self.assertEqual(report.reason_code, schema.RC_INVALID_PARAMETER)

    def test_08_unknown_profile_refused(self):
        payload = self.make_payload(
            "minimum_effect_falsifier",
            {**PARAM_SETS["minimum_effect_falsifier"],
             "min_effect": "extreme"})
        report = self.validate(payload)
        self.assertFalse(report.passed)
        self.assertEqual(report.reason_code, schema.RC_INVALID_PARAMETER)

    def test_09_unknown_param_refused(self):
        payload = self.make_payload(
            "complexity_premium_check",
            {**PARAM_SETS["complexity_premium_check"],
             "margin_free": 0.5})
        report = self.validate(payload)
        self.assertFalse(report.passed)
        self.assertEqual(report.reason_code, schema.RC_INVALID_PARAMETER)

    def test_10_library_data_free_of_code_and_paths(self):
        for primitive_id in NEW_PRIMITIVES:
            primitive = get_primitive(primitive_id)
            texts = [primitive.purpose, primitive.config_note,
                     primitive.direction, primitive.category]
            for profiles in (primitive.extra.get("criteria_by_param")
                             or {}).values():
                for patch in profiles.values():
                    texts.extend(str(v) for v in patch.values())
            for seed in (primitive.extra.get("seeds") or []):
                texts.append(str(seed))
            for text in texts:
                self.assertFalse(schema.looks_like_code(text), text)
                self.assertFalse(schema.looks_like_path(text), text)

    def test_11_bad_criteria_profile_fails_closed_at_render(self):
        payload = self.make_payload("minimum_effect_falsifier")
        params = dict(PARAM_SETS["minimum_effect_falsifier"])
        primitive = get_primitive("minimum_effect_falsifier")
        # Unknown criterion key smuggled into static profile data.
        fake_unknown = dataclasses.replace(
            primitive,
            extra={"criteria_by_param": {"min_effect": {
                "meaningful": {"sneaky_margin": 1.0}}}})
        with self.assertRaises(compiler.CompileError) as ctx:
            compiler._render_config(payload, fake_unknown, params)
        self.assertEqual(ctx.exception.code, schema.RC_SPEC_CONTRACT)
        # Out-of-bounds margin in profile data.
        fake_bounds = dataclasses.replace(
            primitive,
            extra={"criteria_by_param": {"min_effect": {
                "meaningful": {"primary_metric_min_delta": 5.0}}}})
        with self.assertRaises(compiler.CompileError) as ctx:
            compiler._render_config(payload, fake_bounds, params)
        self.assertEqual(ctx.exception.code, schema.RC_SPEC_CONTRACT)

    # -- 12: holdout-blind ---------------------------------------------------
    def test_12_holdout_reference_refused(self):
        payload = self.make_payload("complexity_premium_check")
        payload["rationale"]["evidence_gap"] = (
            "leak attempt at study_files/outputs/study_v1/prospective/secret.csv")
        payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
        report = self.validate(payload)
        self.assertFalse(report.passed)
        self.assertEqual(report.failed_gate, schema.GATE_HOLDOUT)
        self.assertEqual(report.reason_code, schema.RC_HOLDOUT_REFERENCE)

    # -- 9/10: falsifiable, null/adverse-capable ----------------------------
    def test_13_falsification_rules_and_classes(self):
        for primitive_id, proposal_class in (
                ("minimum_effect_falsifier", "falsification"),
                ("complexity_premium_check", "falsification"),
                ("seed_set_replication", "replication")):
            payload = self.make_payload(primitive_id, proposal_class=proposal_class)
            rule = payload["falsification_rule"]
            self.assertEqual(rule["metric"], "pooled_roc_auc_delta")
            self.assertEqual(rule["comparator"], "<")
            self.assertEqual(rule["threshold"], 0.0)
            self.assertIn(rule["metric"], schema.FALSIFICATION_METRICS)
            # An adverse delta (< 0) satisfies the refutation rule: the
            # proposal can genuinely fail; nothing guarantees acceptance.
        replication = get_primitive("seed_set_replication")
        self.assertEqual(replication.default_class, "replication")
        self.assertFalse(replication.falsification_capable)
        from autonomous_agent.proposal_layer.generator import _framed_classes
        self.assertEqual(_framed_classes(replication), ("replication",))
        for primitive_id in ("minimum_effect_falsifier",
                             "complexity_premium_check"):
            self.assertIn("falsification",
                          _framed_classes(get_primitive(primitive_id)))

    # -- 11/13: provenance + outcome-blind selection ------------------------
    def test_14_provenance_and_blindness(self):
        payload = self.make_payload("minimum_effect_falsifier")
        for key in schema.REQUIRED_PAYLOAD_KEYS:
            self.assertIn(key, payload)
        self.assertEqual(payload["generator_type"],
                         schema.GENERATOR_TYPE_DETERMINISTIC)
        self.assertTrue(payload["evidence_citations"])
        for citation in payload["evidence_citations"]:
            self.assertEqual(len(citation["sha256"]), 64)
        self.assertIn("basis", payload["preregistered_expectation"])
        # Candidate ranking for the new primitives carries only the closed
        # input set: no predicted/expected outcome fields exist in a candidate.
        policy = base_policy()
        governor = bias_governor.BiasGovernor(policy)
        candidates = generator._build_candidates(self.view, policy, governor)
        fresh = [c for c in candidates
                 if c["primitive_id"] in NEW_PRIMITIVES]
        self.assertTrue(fresh, "new primitives must enter the candidate pool")
        for candidate in fresh:
            self.assertEqual(set(candidate),
                             {"direction", "proposal_class", "primitive",
                              "primitive_id", "params", "design_signature",
                              "novelty_score", "evidence_gap_score",
                              "quota_pressure", "priority",
                              "attempts_in_direction", "prior_counts"})
            key = generator._ranking_key(candidate, governor)
            self.assertEqual(key, generator._ranking_key(candidate, governor))

    # -- 8/15: distinct signatures and duplicate layers ---------------------
    def test_15_signatures_and_duplicates(self):
        new_signatures = set()
        for primitive_id in NEW_PRIMITIVES:
            payload = self.make_payload(primitive_id)
            new_signatures.add(payload["design_signature"])
            # Recipe-replay signatures from Campaign 1 can never equal a
            # new-primitive signature.
            for attempt in CAMPAIGN1_ATTEMPTS:
                recipe_signature = schema.signature_from_recipe_attempt(
                    attempt["recipe_id"], attempt["selected_parameters"])
                self.assertNotIn(recipe_signature, new_signatures)
            report = self.validate(payload)
            self.assertTrue(report.passed, report.to_dict())
        self.assertEqual(len(new_signatures), len(NEW_PRIMITIVES))
        # Layer 1: byte-identical re-ask refused.
        payload = self.make_payload("minimum_effect_falsifier")
        first_id = self.ledger.create_proposal(payload)
        self.ledger.transition(first_id, schema.STATUS_VALIDATING)
        first = self.validate(payload, proposal_id=first_id)
        self.assertTrue(first.passed, first.to_dict())
        duplicate = dict(payload)
        second_id = self.ledger.create_proposal(duplicate)
        self.ledger.transition(second_id, schema.STATUS_VALIDATING)
        second = self.validate(duplicate, proposal_id=second_id)
        self.assertFalse(second.passed)
        self.assertEqual(second.reason_code, schema.RC_DUPLICATE)

    # -- 14: budget/quota accounting ----------------------------------------
    def test_16_capacity_respects_caps(self):
        policy = base_policy(max_total_proposals=5, max_per_direction=1,
                             max_signature_count=1)
        payloads = generator.generate_proposals(self.view, policy,
                                                seed=3, limit=50)
        self.assertTrue(payloads)
        self.assertLessEqual(len(payloads), 5)
        by_direction: dict[str, int] = {}
        for payload in payloads:
            by_direction[payload["direction"]] = \
                by_direction.get(payload["direction"], 0) + 1
            self.assertLessEqual(by_direction[payload["direction"]], 1)
            # Post-creation accounting, exactly as the loop records them:
            # the generator may never emit a budget-doomed payload (OBS-2).
            pid = self.ledger.create_proposal(payload)
            self.ledger.transition(pid, schema.STATUS_VALIDATING)
            report = self.validate(payload, policy=policy, proposal_id=pid)
            self.assertNotEqual(report.reason_code, schema.RC_BUDGET_EXHAUSTED,
                                payload["design_signature"])
            self.assertNotEqual(report.reason_code, schema.RC_CAMPAIGN_MISMATCH,
                                payload["design_signature"])

    # -- 16: lifecycle + provenance to compile ------------------------------
    def test_17_full_chain_to_compile(self):
        payload = self.make_payload("minimum_effect_falsifier")
        pid = self.ledger.create_proposal(payload)
        self.ledger.transition(pid, schema.STATUS_VALIDATING)
        report = self.validate(payload, proposal_id=pid)
        self.assertTrue(report.passed, report.to_dict())
        self.ledger.transition(
            pid, schema.STATUS_ACCEPTED_FOR_EXECUTION,
            reason_code="HUMAN_APPROVAL",
            detail={"approval_policy": "revalidate_at_approval@1.0.0",
                    "approved_by": "policy:stage4",
                    "quota_state": {"total": 1}})
        spec, spec_sha = compiler.compile_proposal(
            payload, root=self.root, status=self.ledger.status(pid))
        spec.validate()
        self.assertTrue(spec.experiment_id.startswith("exp-proposal-"))
        self.assertIn("proposal_fingerprint", spec.provenance)
        self.assertIs(spec.provenance["llm_involved"], False)
        self.assertFalse(spec.allow_repeat)
        # Duplicate spec registry refuses the same spec again.
        from autonomous_agent import hardening
        hardening.SpecRegistry(self.root / "autonomous_agent/state").record(
            spec.to_dict(), spec.experiment_id, FIXED_CLOCK())
        with self.assertRaises(compiler.CompileError) as ctx:
            compiler.compile_proposal(
                payload, root=self.root,
                status=schema.STATUS_ACCEPTED_FOR_EXECUTION)
        self.assertEqual(ctx.exception.code, schema.RC_DUPLICATE)

    # -- 17: reproducible ----------------------------------------------------
    def test_18_regeneration_reproducible(self):
        first = self.make_payload("seed_set_replication")
        second = self.make_payload("seed_set_replication")
        self.assertEqual(first["proposal_fingerprint"],
                         second["proposal_fingerprint"])
        self.assertEqual(first["design_signature"], second["design_signature"])
        policy = base_policy()
        run_a = generator.generate_proposals(self.view, policy,
                                             seed=5, limit=8)
        run_b = generator.generate_proposals(self.view, policy,
                                             seed=5, limit=8)
        self.assertEqual(json.dumps(run_a, sort_keys=True, default=str),
                         json.dumps(run_b, sort_keys=True, default=str))
        report_a = generator.scheduler_report(self.view, policy)
        report_b = generator.scheduler_report(self.view, policy)
        self.assertEqual(report_a, report_b)    # -- 5: unsupported primitives stay refused (mechanism, not library state)
    def test_19_future_primitives_still_refused(self):
        # Owner R-3 grant (2026-10-12) activated the five v1.1.0 primitives,
        # so the library holds no dormant member anymore. The refusal
        # mechanism is still under test: a patched non-executable clone must
        # be refused by the compiler and never selected by the default
        # policy -- if either gate ever stops firing, this test fails.
        dormant = dataclasses.replace(get_primitive("purge_sensitivity_probe"),
                                      primitive_id="dormant-clone-probe",
                                      executable=False)
        payload = self.make_payload("purge_sensitivity_probe",
                                    {"arm_pair": "A->B", "n_boot": 1000})
        with mock.patch.object(compiler, "get_primitive",
                               return_value=dormant):
            with self.assertRaises(compiler.CompileError) as ctx:
                compiler.preview_spec(payload, root=self.root)
        self.assertEqual(ctx.exception.code,
                         schema.RC_PRIMITIVE_NOT_EXECUTABLE)
        policy = base_policy(allow_future_primitives=False)
        with mock.patch.object(generator, "LIBRARY",
                               tuple(LIBRARY) + (dormant,)):
            payloads = generator.generate_proposals(self.view, policy,
                                                    seed=9, limit=50)
        for generated in payloads:
            generated_id = generated["design"]["primitives"][0]["primitive_id"]
            self.assertNotEqual(generated_id, "dormant-clone-probe")
            self.assertTrue(get_primitive(generated_id).executable,
                            generated_id)
        # And the activated primitives are now compilable -- with the 1.1.0
        # selector rendered from their frozen definitions.
        spec = compiler.preview_spec(payload, root=self.root)
        config = json.loads(spec.changes()[-1].content)
        self.assertEqual(validate_experiment_config(config), [])
        self.assertEqual(config["harness_version"], "1.1.0")
        self.assertEqual(config["primitive_id"], "purge_sensitivity_probe")
        self.assertGreaterEqual(config["n_boot"], 1000)


if __name__ == "__main__":
    unittest.main()
