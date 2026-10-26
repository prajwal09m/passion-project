"""Tests for per-campaign multiplicity (Holm), the C-2 missing-member rule,
the provisional→formal firewall, and the H-10 fail-closed p-value gate.

Authorized 2026-10-12 (gate 3, D2-independent subset). These tests assert
the *machinery*, never a statistical claim: no margin, no method, and no
p-value construction is validated here.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autonomous_agent.proposal_layer import multiplicity as mult


def member(*, member_id="m-1", family="regime", primitive="regime_split_analysis",
           experiment_id="exp-1", status=mult.STATUS_AVAILABLE, p=None,
           ci_upper=None, delta=None) -> mult.FamilyMember:
    return mult.FamilyMember(member_id=member_id, family=family, primitive=primitive,
                             experiment_id=experiment_id, status=status,
                             unadjusted_p=p, ci_upper=ci_upper, delta=delta)


class HolmStepDownTests(unittest.TestCase):
    def test_classic_eight_member_example(self) -> None:
        p_values = [0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205]
        adjusted, rejects = mult.holm_step_down(p_values)
        self.assertEqual(rejects[0], True)          # 0.001 <= 0.05/8
        self.assertEqual(rejects[1:], [False] * 7)  # 0.008 > 0.05/7 stops it
        self.assertAlmostEqual(adjusted[0], 0.008)
        self.assertAlmostEqual(adjusted[1], 0.056)
        for value in adjusted[2:]:
            self.assertAlmostEqual(value, 0.234)

    def test_single_member(self) -> None:
        adjusted, rejects = mult.holm_step_down([0.04])
        self.assertEqual(rejects, [True])
        self.assertAlmostEqual(adjusted[0], 0.04)

    def test_nothing_survives_at_one(self) -> None:
        adjusted, rejects = mult.holm_step_down([1.0, 1.0, 0.9])
        self.assertEqual(rejects, [False, False, False])
        self.assertTrue(all(value == 1.0 for value in adjusted))

    def test_adjusted_values_are_monotone_and_capped(self) -> None:
        p_values = [0.02, 0.01, 0.03, 0.5, 0.9]
        adjusted, _ = mult.holm_step_down(p_values)
        order = sorted(range(len(p_values)), key=lambda i: p_values[i])
        seen = [adjusted[i] for i in order]
        self.assertEqual(seen, sorted(seen))
        self.assertTrue(all(0.0 <= value <= 1.0 for value in adjusted))

    def test_ties_are_deterministic(self) -> None:
        first = mult.holm_step_down([0.01, 0.01, 0.5])
        second = mult.holm_step_down([0.01, 0.01, 0.5])
        self.assertEqual(first, second)

    def test_invalid_inputs_raise(self) -> None:
        for bad in ([], [1.5], [-0.1], [float("nan")]):
            with self.assertRaises(mult.MultiplicityError):
                mult.holm_step_down(bad)
        with self.assertRaises(mult.MultiplicityError):
            mult.holm_step_down([0.1], alpha=0.0)
        with self.assertRaises(mult.MultiplicityError):
            mult.holm_step_down([0.1], alpha=1.0)


class FamilyBookkeepingTests(unittest.TestCase):
    def test_every_declared_family_is_feasible_under_d4_bounds(self) -> None:
        # H-10b pre-check under max_per_direction=12 (regime 24, horizon 36,
        # purge 36, complexity 12): B=1000 and M=1000 must each satisfy
        # count+1 >= 20*m, and m <= 50.
        for name, spec in mult.FAMILIES.items():
            ok, reasons = mult.feasibility(mult.MIN_N_BOOT, spec["member_bound"],
                                           n_flips=mult.MIN_N_FLIPS)
            self.assertTrue(ok, f"{name} infeasible at frozen bounds: {reasons}")
            self.assertLessEqual(spec["member_bound"], mult.MAX_FAMILY_SIZE_M)

    def test_missing_n_flips_is_infeasible_never_silently_feasible(self) -> None:
        # Freeze-test gap (D2 review 2026-10-13, Condition 3): a feasibility
        # verdict on n_boot alone can disagree with the p-value's actual
        # resolution, so n_flips=None must be infeasible with the missing
        # value named -- never silently feasible.
        ok, reasons = mult.feasibility(mult.MIN_N_BOOT, 24)
        self.assertFalse(ok)
        self.assertTrue(any("n_flips" in reason for reason in reasons), reasons)

    def test_reduced_makes_family_infeasible_on_the_p_value_side(self) -> None:
        # A reduced M would make formal refutations unattainable while an
        # n_boot-only freeze test passed; the M-side rule must catch it.
        ok, reasons = mult.feasibility(mult.MIN_N_BOOT, 36, n_flips=500)
        self.assertFalse(ok)
        self.assertTrue(any("n_flips+1" in reason for reason in reasons), reasons)
        # And the exact D4 boundary: M=1000 is feasible at m=50 (1001 >=
        # 1000), fails at m=51 via the cap.
        ok, _ = mult.feasibility(mult.MIN_N_BOOT, 50, n_flips=mult.MIN_N_FLIPS)
        self.assertTrue(ok)
        ok, reasons = mult.feasibility(mult.MIN_N_BOOT, 51,
                                       n_flips=mult.MIN_N_FLIPS)
        self.assertFalse(ok)
        self.assertTrue(any("D4 cap" in reason for reason in reasons), reasons)

    def test_family_of_maps_only_the_four_primitives(self) -> None:
        self.assertEqual(mult.family_of("purge_sensitivity_probe"), "purge")
        self.assertIsNone(mult.family_of("seed_set_replication"))

    def test_foreign_primitive_never_enters_a_family(self) -> None:
        for primitive in sorted(mult.EXCLUDED_PRIMITIVES):
            family = mult.family_of(primitive)
            with self.assertRaises(mult.MultiplicityError):
                member(member_id=f"x-{primitive}", family="regime",
                       primitive=primitive, p=0.001)

    def test_undeclared_family_or_mismatched_primitive_refused(self) -> None:
        with self.assertRaises(mult.MultiplicityError):
            member(family="not_a_family", primitive="regime_split_analysis", p=0.1)
        with self.assertRaises(mult.MultiplicityError):
            member(family="horizon", primitive="regime_split_analysis", p=0.1)

    def test_mixed_families_cannot_pool(self) -> None:
        with self.assertRaises(mult.MultiplicityError):
            mult.adjust_family(
                [member(member_id="a", family="horizon",
                        primitive="target_horizon_robustness", p=0.01),
                 member(member_id="b", family="purge",
                        primitive="purge_sensitivity_probe", p=0.01)],
                n_boot=1000, p_value_method="unused")

    def test_member_bound_is_enforced_as_a_cap(self) -> None:
        bound = mult.FAMILIES["complexity"]["member_bound"]
        decisions = [mult.MemberDecision(
            member_id=f"c-{i}", family="complexity",
            experiment_id=f"exp-{i}", status=mult.STATUS_AVAILABLE,
            raw_delta=0.0, raw_ci_upper=0.1, unadjusted_p=0.5, adjusted_p=1.0,
            raw_label=mult.LABEL_NO_SIGNAL, formal_status=mult.FORMAL_INCONCLUSIVE,
            survived_adjustment=False, ci_disagrees_with_p=False)
            for i in range(bound + 1)]
        with self.assertRaises(mult.MultiplicityError):
            mult.assemble_record(campaign_id="c4", n_boot=1000,
                                 p_value_method="unused",
                                 family_decisions={"complexity": decisions})


class MissingMemberRuleTests(unittest.TestCase):
    """C-2 Option A: unavailable counts toward m at p=1.0, never REFUTED."""

    def test_unavailable_counts_toward_family_size(self) -> None:
        # Alone, p=0.03 <= alpha/1 -> would be REFUTED. Adding an unavailable
        # member makes m=2 (it occupies a slot at p=1.0), so the first
        # threshold drops to 0.025 and the signal no longer survives: proof
        # that C-2 really counts the unavailable member toward m.
        self.assertEqual(mult.holm_step_down([0.03])[1], [True])
        members = [member(member_id="a", p=0.03, ci_upper=-0.02),
                   member(member_id="u", status=mult.STATUS_UNAVAILABLE)]
        self.assertEqual([item.effective_p for item in members], [0.03, 1.0])
        _, rejects = mult.holm_step_down([item.effective_p for item in members])
        self.assertEqual(rejects, [False, False])

    def test_unavailable_member_is_never_refuted_and_stays_unavailable(self) -> None:
        members = [member(member_id="a", p=0.0001, ci_upper=-0.2),
                   member(member_id="u", status=mult.STATUS_UNAVAILABLE)]
        # resolve_without_record must preserve the C-2 label without inventing
        # a p-value for the unavailable member.
        decisions = mult.resolve_without_record(members)
        unavailable = [d for d in decisions if d.member_id == "u"][0]
        self.assertEqual(unavailable.raw_label, mult.LABEL_UNAVAILABLE)
        self.assertEqual(unavailable.formal_status, mult.FORMAL_UNAVAILABLE)
        self.assertIsNone(unavailable.unadjusted_p)
        self.assertIsNone(unavailable.adjusted_p)

    def test_available_member_without_p_is_refused(self) -> None:
        with self.assertRaises(mult.MultiplicityError):
            member(member_id="a", p=None)
        with self.assertRaises(mult.MultiplicityError):
            member(member_id="a", p=1.2)


class PValueGateTests(unittest.TestCase):
    """H-10 RESOLVED 2026-10-14: exactly the recorded method may pass."""

    def test_allowlist_matches_the_recorded_h10_decision(self) -> None:
        self.assertEqual(set(mult.approved_p_value_methods()),
                         {"week_level_signflip_holm"})
        basis = mult.family_manifest()["p_value_gate"]
        self.assertIn("H-10", basis)
        self.assertIn("H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md", basis)
        self.assertIn("procedure-level", basis)
        self.assertIn("retracted", basis)

    def test_every_unapproved_method_name_is_refused(self) -> None:
        for name in ("signflip", "sign", "normal_approx", "b", "a", "c", "",
                     "week_level_signflip", "sign_flip", "Week_Level_SignFlip_Holm"):
            with self.assertRaises(mult.PValueMethodUnresolved):
                mult.require_approved_method(name)
        with self.assertRaises(mult.PValueMethodUnresolved):
            mult.require_approved_method(None)

    def test_recorded_method_passes_and_runs_holm_end_to_end(self) -> None:
        self.assertEqual(mult.require_approved_method("week_level_signflip_holm"),
                         "week_level_signflip_holm")
        decisions = mult.adjust_family(
            [member(member_id="sig", p=0.001, ci_upper=-0.2),
             member(member_id="quiet", p=0.4, ci_upper=0.3)],
            n_boot=mult.MIN_N_BOOT, n_flips=mult.MIN_N_FLIPS,
            p_value_method="week_level_signflip_holm")
        by_id = {d.member_id: d for d in decisions}
        self.assertEqual(by_id["sig"].unadjusted_p, 0.001)
        self.assertEqual(by_id["sig"].formal_status, mult.FORMAL_REFUTED)
        self.assertTrue(by_id["sig"].survived_adjustment)
        self.assertNotEqual(by_id["quiet"].formal_status, mult.FORMAL_REFUTED)
        self.assertFalse(by_id["quiet"].survived_adjustment)

    def test_adjust_family_refuses_before_computing_anything(self) -> None:
        with self.assertRaises(mult.PValueMethodUnresolved):
            mult.adjust_family([member(member_id="a", p=0.0001, ci_upper=-1.0)],
                               n_boot=1000, p_value_method="signflip")

    def test_campaign_end_record_refuses_before_computing_anything(self) -> None:
        with self.assertRaises(mult.PValueMethodUnresolved):
            mult.campaign_end_record(campaign_id="c4",
                                     families={"regime": [member(member_id="a", p=0.01)]},
                                     n_boot=1000, p_value_method="signflip")

    def test_infeasible_granularity_never_produces_a_refutation(self) -> None:
        # Even if a method existed, B=500 with a horizon-sized family is
        # infeasible; the machinery must return INCONCLUSIVE, not REFUTED.
        members = [member(member_id=f"h-{i}", family="horizon",
                          primitive="target_horizon_robustness",
                          experiment_id=f"exp-{i}", p=1e-6, ci_upper=-0.5)
                   for i in range(36)]
        feasibility, reasons = mult.feasibility(500, 36,
                                                n_flips=mult.MIN_N_FLIPS)
        self.assertFalse(feasibility)
        self.assertTrue(any("20*m" in reason for reason in reasons))
        ok, _ = mult.feasibility(mult.MIN_N_BOOT, 36,
                                 n_flips=mult.MIN_N_FLIPS)
        self.assertTrue(ok)


class FirewallTests(unittest.TestCase):
    def test_bare_refuted_is_detected_in_nested_artifacts(self) -> None:
        artifact = {"rows": [{"detail": {"label": "REFUTED"}}]}
        hits = mult.find_formal_refutation_labels(artifact)
        self.assertEqual(len(hits), 1)
        with self.assertRaises(mult.FirewallViolation):
            mult.assert_firewall_intact(artifact, context="ledger")

    def test_provisional_markers_are_legal_everywhere(self) -> None:
        artifact = {"rows": [{"detail": {
            "refutation_signal": "unadjusted",
            "formal_refutation": False,
            "provisional_label": "provisional_refutation_signal",
            "provisional_displays_as": "provisional, not a refutation claim"}}]}
        self.assertEqual(mult.find_formal_refutation_labels(artifact), [])
        mult.assert_firewall_intact(artifact, context="ledger")   # must not raise

    def test_free_text_assertion_is_blocked(self) -> None:
        with self.assertRaises(mult.FirewallViolation):
            mult.scan_text_for_formal_refutation(
                "the regime family was REFUTED at campaign end", context="report")
        mult.scan_text_for_formal_refutation(
                "a provisional_refutation_signal exists, not a claim", context="report")

    def test_signal_fields_carry_no_formal_status(self) -> None:
        fields = member(member_id="a", p=0.4, ci_upper=-0.01).signal_fields()
        self.assertEqual(fields[mult.REFUTATION_SIGNAL_FIELD], "unadjusted")
        self.assertIs(fields[mult.FORMAL_REFUTATION_FIELD], False)
        self.assertNotIn("formal_status", fields)

    def test_describe_provisional_strips_formal_fields(self) -> None:
        decisions = mult.resolve_without_record(
            [member(member_id="a", p=0.4, ci_upper=-0.05)])
        rendered = mult.describe_provisional(decisions)
        self.assertNotIn("formal_status", rendered[0])
        self.assertNotIn("survived_adjustment", rendered[0])
        self.assertIs(rendered[0][mult.FORMAL_REFUTATION_FIELD], False)
        self.assertEqual(rendered[0]["provisional_displays_as"],
                         "provisional, not a refutation claim")


class RecordTests(unittest.TestCase):
    def _decision(self, member_id="a", adjusted_p=0.004,
                  formal=mult.FORMAL_REFUTED) -> mult.MemberDecision:
        return mult.MemberDecision(
            member_id=member_id, family="complexity", experiment_id="exp-1",
            status=mult.STATUS_AVAILABLE, raw_delta=-0.03, raw_ci_upper=-0.02,
            unadjusted_p=0.002, adjusted_p=adjusted_p,
            raw_label=mult.LABEL_PROVISIONAL_REFUTATION, formal_status=formal,
            survived_adjustment=(formal == mult.FORMAL_REFUTED),
            ci_disagrees_with_p=False)

    def test_unadjusted_numbers_are_retained_alongside_adjusted(self) -> None:
        record = mult.assemble_record(campaign_id="c4", n_boot=1000,
                                      p_value_method="unused",
                                      family_decisions={"complexity": [self._decision()]})
        row = record["families"]["complexity"]["members"][0]
        for key in ("raw_delta", "raw_ci_upper", "unadjusted_p", "adjusted_p",
                    "formal_status", "raw_label"):
            self.assertIn(key, row)
        self.assertEqual(row["raw_delta"], -0.03)
        self.assertEqual(row["raw_ci_upper"], -0.02)
        self.assertEqual(row["unadjusted_p"], 0.002)
        self.assertEqual(row["adjusted_p"], 0.004)
        self.assertTrue(record["unadjusted_retained"])

    def test_record_carries_n_flips_and_both_feasibility_rules(self) -> None:
        # Freeze-test gap fix (D2 review 2026-10-13): the recorded
        # feasibility must include M so it can never disagree with the
        # actual p-value resolution.
        record = mult.assemble_record(campaign_id="c4", n_boot=1000,
                                      n_flips=1000, p_value_method="unused",
                                      family_decisions={"complexity": [self._decision()]})
        block = record["families"]["complexity"]["feasibility"]
        self.assertEqual(block["n_boot"], 1000)
        self.assertEqual(block["n_flips"], 1000)
        self.assertIn("n_boot + 1 >= 20 * m", block["rules"])
        self.assertIn("n_flips + 1 >= 20 * m", block["rules"])
        self.assertTrue(block["feasible"], block["reasons"])
        # Without M the block is infeasible and says why -- never feasible.
        record = mult.assemble_record(campaign_id="c4", n_boot=1000,
                                      p_value_method="unused",
                                      family_decisions={"complexity": [self._decision()]})
        block = record["families"]["complexity"]["feasibility"]
        self.assertIsNone(block["n_flips"])
        self.assertFalse(block["feasible"])
        self.assertTrue(any("n_flips" in reason for reason in block["reasons"]))
        # The reader-facing note discloses the MC-resolution limitation.
        self.assertIn("Monte-Carlo resolution", record["note"])
        self.assertIn("procedure-level", record["note"])

    def test_formal_status_never_claimed_without_adjusted_p(self) -> None:
        decision = self._decision(adjusted_p=None, formal=mult.FORMAL_REFUTED)
        with self.assertRaises(mult.MultiplicityError):
            mult.assemble_record(campaign_id="c4", n_boot=1000,
                                 p_value_method="unused",
                                 family_decisions={"complexity": [decision]})

    def test_record_is_append_only_and_final_per_campaign(self) -> None:
        record = mult.assemble_record(campaign_id="c4", n_boot=1000,
                                      p_value_method="unused",
                                      family_decisions={"complexity": [self._decision()]})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "multiplicity.jsonl"
            mult.append_record(path, record)
            mult.append_record(path, mult.assemble_record(
                campaign_id="c5", n_boot=1000, p_value_method="unused",
                family_decisions={"complexity": [self._decision(member_id="b")]}))
            rows = mult.read_records(path)
            self.assertEqual([row["campaign_id"] for row in rows], ["c4", "c5"])
            # recomputing c4 is refused, not silently overwritten
            with self.assertRaises(mult.MultiplicityError):
                mult.append_record(path, record)
            # a foreign row type is refused
            with self.assertRaises(mult.MultiplicityError):
                mult.append_record(path, {"record_type": "something_else",
                                          "campaign_id": "c6"})
            self.assertEqual(mult.formal_refuted_members(rows[0]), ["a"])

    def test_missing_record_resolves_everything_inconclusive(self) -> None:
        decisions = mult.resolve_without_record(
            [member(member_id="sig", p=1e-6, ci_upper=-0.9),
             member(member_id="quiet", p=0.9, ci_upper=0.1),
             member(member_id="gone", status=mult.STATUS_UNAVAILABLE)])
        by_id = {d.member_id: d for d in decisions}
        self.assertEqual(by_id["sig"].formal_status, mult.FORMAL_INCONCLUSIVE)
        self.assertEqual(by_id["sig"].raw_label, mult.LABEL_PROVISIONAL_REFUTATION)
        self.assertEqual(by_id["quiet"].formal_status, mult.FORMAL_INCONCLUSIVE)
        self.assertEqual(by_id["gone"].formal_status, mult.FORMAL_UNAVAILABLE)


class AuditStopSignalTests(unittest.TestCase):
    def test_confirmed_contamination_fires_the_pit_stop(self) -> None:
        stop = mult.audit_stop_signal(
            {"results": {"point_in_time_audit": {"status": "CONFIRMED_CONTAMINATION"}}})
        self.assertEqual(stop[0], mult.STOP_POINT_IN_TIME_CONTAMINATION)

    def test_unverifiable_lineage_fires_the_lineage_stop(self) -> None:
        stop = mult.audit_stop_signal({"point_in_time_audit": {"lineage_status": "UNVERIFIABLE"}})
        self.assertEqual(stop[0], mult.STOP_UNVERIFIABLE_LINEAGE)

    def test_absence_signals_nothing(self) -> None:
        self.assertIsNone(mult.audit_stop_signal({}))
        self.assertIsNone(mult.audit_stop_signal({"results": {"status": "PASS"}}))
        self.assertIsNone(mult.audit_stop_signal(
            {"results": {"point_in_time_audit": {"status": "CLEAN"}}}))

    def test_disclosed_tier2_column_verdict_never_halts_a_campaign(self) -> None:
        # A Tier-2 (parity-UNVERIFIABLE) column is a documented, disclosed
        # outcome of the census — it must never be mistaken for an
        # unverifiable-lineage stop.
        self.assertIsNone(mult.audit_stop_signal({
            "results": {"census": [
                {"column": "rsi14", "verdict": "UNVERIFIABLE"},
                {"column": "atr_pct", "verdict": "UNVERIFIABLE"},
                {"column": "daily_return", "verdict": "PASS"},
            ]}}))

    def test_recorded_signal_survives_a_restart(self) -> None:
        rows = [{"row_type": "transition", "detail": {}},
                {"row_type": "transition", "detail": {
                    "results": {"point_in_time_audit": {"status": "CONFIRMED_CONTAMINATION"}}}}]
        stop = mult.recorded_audit_stop(rows)
        self.assertEqual(stop[0], mult.STOP_POINT_IN_TIME_CONTAMINATION)
        self.assertIsNone(mult.recorded_audit_stop([{"detail": {}}]))

    def test_declared_stop_names_are_the_wired_ones(self) -> None:
        self.assertEqual(mult.AUDIT_STOP_CONDITIONS,
                         {"point_in_time_contamination_detected",
                          "unverifiable_lineage_detected"})


class FamilyManifestTests(unittest.TestCase):
    def test_manifest_matches_the_frozen_table(self) -> None:
        manifest = mult.family_manifest()
        self.assertEqual(manifest["max_family_size_m"], mult.MAX_FAMILY_SIZE_M)
        self.assertEqual(manifest["min_n_boot"], mult.MIN_N_BOOT)
        self.assertEqual(manifest["familywise_alpha"], mult.FAMILYWISE_ALPHA)
        self.assertEqual(manifest["correction"], "holm_step_down")
        self.assertEqual(manifest["approved_p_value_methods"],
                         ["week_level_signflip_holm"])
        self.assertIn("H-10", manifest["p_value_gate"])
        self.assertEqual(set(manifest["families"]), set(mult.FAMILIES))


class LadderFamilyAgreementTests(unittest.TestCase):
    """Frozen ladder family <-> FAMILIES table agreement (owner R-3 grant).

    This cross-check lives here (not in primitives.py) so the multiplicity
    machinery keeps its inertness boundary: only the loop and this test
    module import it.
    """

    def test_every_activated_primitive_family_matches_the_frozen_table(self) -> None:
        from autonomous_agent import three_valued as tv
        from autonomous_agent.proposal_layer import primitives
        activated = ("purge_sensitivity_probe", "regime_split_analysis",
                     "complexity_reduction_check", "target_horizon_robustness",
                     "point_in_time_data_audit")
        for primitive_id in activated:
            extra = primitives.get(primitive_id).extra
            ladder = tv.ladder_for(primitive_id)
            self.assertEqual(extra["frozen_ladder"], ladder, primitive_id)
            family = extra["multiplicity"]["family"]
            if family is None:
                # Only the audit may stay out of a family.
                self.assertEqual(primitive_id, "point_in_time_data_audit")
                continue
            declared = mult.FAMILIES[family]
            self.assertEqual(declared["primitive"], primitive_id)
            self.assertEqual(declared["members_per_experiment"],
                             ladder["members_per_experiment"])
            self.assertEqual(extra["multiplicity"]["members_per_experiment"],
                             ladder["members_per_experiment"])

    def test_family_feeding_primitives_respect_the_h10b_floor(self) -> None:
        # H-10b: n_boot >= 1000 (and >= 20*m - 1) for every family-feeding
        # primitive; the ParamSpec bounds enforce it at the source.
        from autonomous_agent.proposal_layer import primitives
        for family, declared in mult.FAMILIES.items():
            primitive = primitives.get(declared["primitive"])
            low = primitive.params["n_boot"].low
            self.assertGreaterEqual(low, mult.MIN_N_BOOT,
                                    f"{family}: n_boot floor {low} < "
                                    f"{mult.MIN_N_BOOT}")
            m = declared["members_per_experiment"]
            self.assertGreaterEqual(low + 1, 20 * m,
                                    f"{family}: B+1 < 20*m under the floor")


if __name__ == "__main__":
    unittest.main()
