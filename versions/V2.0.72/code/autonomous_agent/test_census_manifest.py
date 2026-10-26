"""Tests for the H-11 census manifest rules (frozen tolerances, tiers,
structural non-upgrade, missing-entry blocking) and the header scaffolder.

Authorized 2026-10-12 (gate 3, D2-independent subset). These tests assert
manifest *rules*; they never assert that any column of the real dataset is
correct, and they never read the holdout.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from autonomous_agent.proposal_layer import census

TABLE = Path("study_files/outputs/study_v1/development/event_table.csv")


def tier1_entry(**overrides) -> dict:
    base = dict(column="daily_return", tier=census.TIER_1, kind=census.KIND_FLOAT,
                raw_source="raw.csv#daily_return",
                formula_reference="V1 feature definition: daily_return",
                tolerance=census.tolerance_for(census.KIND_FLOAT, documented_decimals=6),
                tolerance_origin=census.ORIGIN_DOCUMENTED_PRECISION)
    base.update(overrides)
    return census.entry(**base)


class TolerancePolicyTests(unittest.TestCase):
    def test_exact_valued_kinds_compare_at_exact_equality(self) -> None:
        for kind in (census.KIND_INTEGER, census.KIND_BOOLEAN, census.KIND_CATEGORICAL):
            tolerance = census.tolerance_for(kind)
            self.assertEqual(tolerance["abs"], 0.0)
            self.assertEqual(tolerance["rel"], 0.0)
            self.assertEqual(tolerance["origin"], census.ORIGIN_EXACT_EQUALITY)

    def test_float_tolerance_uses_documented_precision(self) -> None:
        tolerance = census.tolerance_for(census.KIND_FLOAT, documented_decimals=6)
        self.assertAlmostEqual(tolerance["abs"], 5e-7)
        self.assertEqual(tolerance["rel"], census.FLOAT_RELATIVE_TOLERANCE)
        self.assertEqual(tolerance["origin"], census.ORIGIN_DOCUMENTED_PRECISION)

    def test_float_tolerance_without_documented_precision_is_refused(self) -> None:
        with self.assertRaises(census.CensusError):
            census.tolerance_for(census.KIND_FLOAT)
        with self.assertRaises(census.CensusError):
            census.tolerance_for(census.KIND_FLOAT, documented_decimals=-1)
        with self.assertRaises(census.CensusError):
            census.tolerance_for("made_up_kind")


class TierRuleTests(unittest.TestCase):
    def test_documented_tier2_columns_are_declared_not_inferred(self) -> None:
        for column in ("rsi14", "atr_pct", "zone_width_pct"):
            self.assertEqual(census.tier_for(column), census.TIER_2)
        self.assertEqual(census.tier_for("daily_return"), census.TIER_1)

    def test_tier2_entry_can_never_be_pass_or_contamination(self) -> None:
        item = census.entry(column="rsi14", tier=census.TIER_2,
                            kind=census.KIND_FLOAT,
                            raw_source="UNRECOVERED_V1_0_1_SOURCE",
                            formula_reference="source never recovered",
                            tolerance=None,
                            tolerance_origin=census.ORIGIN_DECLARED_AT_FREEZE)
        self.assertEqual(item["verdict"], census.VERDICT_UNVERIFIABLE)
        self.assertFalse(item["value_mismatch_can_yield_contamination"])
        with self.assertRaises(census.CensusError):
            census.entry(column="rsi14", tier=census.TIER_2, kind=census.KIND_FLOAT,
                         raw_source="x", formula_reference="y", tolerance=None,
                         tolerance_origin=census.ORIGIN_DECLARED_AT_FREEZE,
                         verdict=census.VERDICT_PASS)
        with self.assertRaises(census.CensusError):
            census.entry(column="rsi14", tier=census.TIER_2, kind=census.KIND_FLOAT,
                         raw_source="x", formula_reference="y", tolerance=None,
                         tolerance_origin=census.ORIGIN_DECLARED_AT_FREEZE,
                         value_mismatch_can_yield_contamination=True)

    def test_tier1_entry_requires_source_formula_and_tolerance(self) -> None:
        with self.assertRaises(census.CensusError):
            census.entry(column="c", tier=census.TIER_1, kind=census.KIND_FLOAT,
                         raw_source="x", formula_reference="y", tolerance=None)
        with self.assertRaises(census.CensusError):
            census.entry(column="c", tier=census.TIER_1, kind=census.KIND_FLOAT,
                         raw_source="x", formula_reference="y",
                         tolerance=census.tolerance_for(census.KIND_FLOAT,
                                                        documented_decimals=4),
                         tolerance_origin=census.ORIGIN_OBSERVED_MISMATCH)


class ManifestValidationTests(unittest.TestCase):
    def _manifest(self, *entries: dict) -> dict:
        return {"schema_version": 1, "columns": list(entries)}

    def test_complete_manifest_passes(self) -> None:
        manifest = self._manifest(tier1_entry(),
                                  census.entry(
                                      column="rsi14", tier=census.TIER_2,
                                      kind=census.KIND_FLOAT,
                                      raw_source="UNRECOVERED_V1_0_1_SOURCE",
                                      formula_reference="source never recovered",
                                      tolerance=None,
                                      tolerance_origin=census.ORIGIN_DECLARED_AT_FREEZE))
        errors = census.validate_manifest(manifest, ["daily_return", "rsi14"])
        self.assertEqual(errors, [])
        self.assertTrue(census.can_audit_pass(manifest, ["daily_return", "rsi14"]))

    def test_missing_entry_blocks_audit_pass(self) -> None:
        manifest = self._manifest(tier1_entry())
        errors = census.validate_manifest(manifest, ["daily_return", "ema20"])
        self.assertTrue(any("missing manifest entry" in e and "ema20" in e
                            for e in errors))
        self.assertFalse(census.can_audit_pass(manifest, ["daily_return", "ema20"]))

    def test_undeclared_extra_column_is_refused(self) -> None:
        manifest = self._manifest(tier1_entry(), tier1_entry(column="surprise"))
        errors = census.validate_manifest(manifest, ["daily_return"])
        self.assertTrue(any("not an expected feature column" in e for e in errors))

    def test_duplicate_entries_are_refused(self) -> None:
        manifest = self._manifest(tier1_entry(), tier1_entry())
        errors = census.validate_manifest(manifest, ["daily_return"])
        self.assertTrue(any("duplicate manifest entry" in e for e in errors))

    def test_unfrozen_tolerance_cannot_back_a_pass(self) -> None:
        draft = tier1_entry(tolerance={"kind": census.KIND_FLOAT, "abs": None,
                                       "rel": None,
                                       "origin": census.ORIGIN_DECLARED_AT_FREEZE},
                            tolerance_origin=census.ORIGIN_DECLARED_AT_FREEZE)
        manifest = self._manifest(draft)
        errors = census.validate_manifest(manifest, ["daily_return"])
        self.assertTrue(any("not frozen" in e for e in errors))
        self.assertFalse(census.can_audit_pass(manifest, ["daily_return"]))

    def test_observed_mismatch_tolerance_is_always_refused(self) -> None:
        # The builder refuses it outright…
        with self.assertRaises(census.CensusError):
            tier1_entry(
                tolerance={"kind": census.KIND_FLOAT, "abs": 0.5, "rel": 0.0,
                           "origin": census.ORIGIN_OBSERVED_MISMATCH},
                tolerance_origin=census.ORIGIN_OBSERVED_MISMATCH)
        # …and the validator still defends against a hand-crafted manifest.
        smuggled = {"column": "daily_return", "tier": census.TIER_1,
                    "kind": census.KIND_FLOAT, "raw_source": "x",
                    "formula_reference": "y",
                    "tolerance": {"kind": census.KIND_FLOAT, "abs": 0.5,
                                  "rel": 0.0,
                                  "origin": census.ORIGIN_OBSERVED_MISMATCH},
                    "tolerance_origin": census.ORIGIN_OBSERVED_MISMATCH,
                    "verdict": census.VERDICT_UNTESTED, "rows_compared": 0}
        errors = census.validate_manifest(self._manifest(smuggled), ["daily_return"])
        self.assertTrue(any("not documented" in e for e in errors))

    def test_unknown_tier_verdict_and_untested_rows_are_refused(self) -> None:
        # Invalid tiers/verdicts are refused by the builder…
        for kwargs in ({"tier": "TIER_3"}, {"verdict": "MAYBE"},
                       {"tier": census.TIER_2, "verdict": census.VERDICT_PASS}):
            with self.assertRaises(census.CensusError):
                tier1_entry(**kwargs)
        # …and by the validator when they are smuggled in as raw dicts.
        for broken in (
                {"column": "daily_return", "tier": "TIER_3",
                 "verdict": census.VERDICT_UNTESTED},
                {"column": "daily_return", "tier": census.TIER_1,
                 "verdict": "MAYBE"},
                {"column": "daily_return", "tier": census.TIER_2,
                 "verdict": census.VERDICT_FAIL},
                tier1_entry(verdict=census.VERDICT_UNTESTED, rows_compared=10),
                tier1_entry(raw_source=""),
                tier1_entry(formula_reference="")):
            column = broken["column"]
            errors = census.validate_manifest(self._manifest(broken), [column])
            self.assertTrue(errors, f"expected errors for {broken}")

    def test_manifest_must_be_a_list_of_mappings(self) -> None:
        self.assertTrue(census.validate_manifest({"columns": "nope"}, ["a"]))
        self.assertTrue(census.validate_manifest({"columns": [{"tier": census.TIER_1}]}, ["a"]))
        self.assertTrue(census.validate_manifest({"columns": [3]}, ["a"]))
        self.assertTrue(census.validate_manifest("not a mapping", ["a"]))


class StructuralNonUpgradeTests(unittest.TestCase):
    def test_structure_never_upgrades_a_value_verdict(self) -> None:
        for verdict in (census.VERDICT_UNVERIFIABLE, census.VERDICT_FAIL,
                        census.VERDICT_UNTESTED):
            self.assertEqual(census.combine_verdict(verdict, structural_pass=True),
                             verdict)
        self.assertEqual(census.combine_verdict(census.VERDICT_PASS,
                                                structural_pass=True),
                         census.VERDICT_PASS)
        with self.assertRaises(census.CensusError):
            census.combine_verdict("SOMETHING_ELSE", structural_pass=True)


class ScaffolderTests(unittest.TestCase):
    """Uses the real development table header only — no data rows, no holdout."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = census.scaffold_manifest(TABLE)

    def test_header_inventory_is_recorded_honestly(self) -> None:
        self.assertEqual(self.manifest["source_table_columns"], 114)
        self.assertEqual(self.manifest["feature_columns_observed"],
                         len(self.manifest["columns"]))
        self.assertEqual(len(self.manifest["non_feature_columns"]),
                         len(census.NON_FEATURE_COLUMNS))
        # The plan's inventory count (101) does not reproduce from the actual
        # header; the scaffold reports the mismatch instead of hiding it.
        self.assertFalse(self.manifest["inventory_count_matches_observed"])

    def test_documented_tier2_members_are_present_and_unverifiable(self) -> None:
        self.assertEqual(set(self.manifest["documented_tier_2"]),
                         set(census.DOCUMENTED_TIER_2))
        by_name = {item["column"]: item for item in self.manifest["columns"]}
        for column in census.DOCUMENTED_TIER_2:
            self.assertEqual(by_name[column]["tier"], census.TIER_2)
            self.assertEqual(by_name[column]["verdict"], census.VERDICT_UNVERIFIABLE)
            self.assertFalse(
                by_name[column]["value_mismatch_can_yield_contamination"])

    def test_draft_is_correctly_insufficient_to_back_an_audit_pass(self) -> None:
        expected = [item["column"] for item in self.manifest["columns"]]
        errors = census.validate_manifest(self.manifest, expected)
        # No *missing* entries, but the undelared float tolerances are
        # intentionally absent, so the draft can never back a PASS.
        self.assertFalse(any("missing manifest entry" in e for e in errors))
        self.assertTrue(any("not frozen" in e for e in errors))
        self.assertFalse(census.can_audit_pass(self.manifest, expected))

    def test_no_non_feature_column_leaks_into_the_census(self) -> None:
        names = {item["column"] for item in self.manifest["columns"]}
        self.assertFalse(names & census.NON_FEATURE_COLUMNS)

    def test_classified_families_cover_every_feature(self) -> None:
        counts = self.manifest["family_counts"]
        self.assertEqual(sum(counts.values()), len(self.manifest["columns"]))
        self.assertEqual(set(counts), {"market_benchmark", "order_block_structural",
                                       "price_volume_technical", "zone_base"})
        # Corrected 2026-10-12 against the real header: ob_unmitigated_* is
        # order-block structure and relative_strength_* is price/volume
        # technical, so the four families reproduce exactly.
        self.assertEqual(counts, census.EXPECTED_FAMILY_COUNTS)
        self.assertEqual(counts["market_benchmark"], 11)
        self.assertEqual(counts["zone_base"], 8)
        self.assertEqual(counts["order_block_structural"], 34)

    def test_unmitigated_and_relative_strength_columns_are_filed_correctly(self) -> None:
        by_name = {item["column"]: item for item in self.manifest["columns"]}
        for column in ("ob_unmitigated_bull_count", "ob_unmitigated_bear_count"):
            self.assertEqual(by_name[column]["family"], "order_block_structural")
        for column in ("relative_strength_spy_20d", "relative_strength_qqq_20d",
                       "relative_strength_iwm_20d"):
            self.assertEqual(by_name[column]["family"], "price_volume_technical")
        self.assertFalse(any(by_name[c]["family"] == "market_benchmark"
                             for c in by_name if c.startswith("relative_strength_")))

    def test_inventory_discrepancy_is_surfaced_not_silenced(self) -> None:
        self.assertFalse(self.manifest["family_counts_match_inventory"])
        self.assertEqual(self.manifest["inventory_family_counts"],
                         census.INVENTORY_FAMILY_COUNTS)
        self.assertEqual(self.manifest["feature_columns_in_inventory"], 101)
        self.assertEqual(self.manifest["feature_columns_observed"], 100)
        # the only family that disagrees is price/volume, by exactly one
        differing = [name for name in census.INVENTORY_FAMILY_COUNTS
                     if census.INVENTORY_FAMILY_COUNTS[name]
                     != census.EXPECTED_FAMILY_COUNTS[name]]
        self.assertEqual(differing, ["price_volume_technical"])


if __name__ == "__main__":
    unittest.main()
