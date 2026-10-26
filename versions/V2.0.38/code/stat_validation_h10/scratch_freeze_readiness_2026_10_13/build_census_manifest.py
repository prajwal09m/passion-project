#!/usr/bin/env python3
"""SCRATCH — build the C4 census-manifest candidate and run the freeze-time
completeness validation (2026-10-13).

What this runs: H-11 census-MANIFEST completeness (the freeze-time check per
CAMPAIGN_4_DEPENDENCY_ORDERED_EXECUTION_CHECKLIST Track 4). What this does
NOT run: the value-level parity census -- that executes inside the
point_in_time_data_audit primitive at campaign time against a recomputed
table; it is not a freeze-time check and no recompute is attempted here.

Tolerances: integer/boolean/categorical columns get the frozen
exact-equality rule (documented rule, not an observation). Float columns
get origin DECLARED_AT_FREEZE with tolerance=None (fail-closed): the raw
inputs' documented decimal precision is not on file anywhere in the
repository, and H-11 forbids deriving tolerances from observed data, so the
freeze must declare them. Kind classification (integer vs float) is
observed from the CSV values and disclosed as such -- it selects which
frozen rule applies, it never sets a tolerance width.

Output: MAIN AUDITS AND REFLECTIONS/C4_CENSUS_MANIFEST_CANDIDATE_2026_10_13.json
plus this script's log. Candidate only; nothing frozen.
"""
import csv
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from autonomous_agent.proposal_layer import census  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
TABLE = ROOT / "study_files/outputs/study_v1/development/event_table.csv"
OUT = (ROOT / "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
              "C4_CENSUS_MANIFEST_CANDIDATE_2026_10_13.json")


def classify_kinds(path: pathlib.Path, features: list[str]) -> dict[str, str]:
    """Observed kind per feature: starts optimistic-integer and downgrades
    to float on the first non-integral value, or categorical on the first
    non-numeric value (disclosed observation; never sets a tolerance
    width)."""
    kinds = {name: "integer" for name in features}
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            for name in features:
                if kinds[name] in ("float", "categorical"):
                    continue
                raw = (row.get(name) or "").strip()
                if raw == "" or raw.lower() in ("nan", "none"):
                    continue
                try:
                    value = float(raw)
                except ValueError:
                    kinds[name] = "categorical"
                    continue
                if not value.is_integer():
                    kinds[name] = "float"
    return kinds


def main() -> None:
    with open(TABLE, "r", encoding="utf-8", errors="replace", newline="") as fh:
        header = next(csv.reader(fh))
    non_feature = sorted(census.NON_FEATURE_COLUMNS & set(header))
    features = [name for name in header if name not in census.NON_FEATURE_COLUMNS]
    kinds = classify_kinds(TABLE, features)

    entries = []
    for name in features:
        tier = census.tier_for(name)
        family = census.column_family(name)
        if tier == census.TIER_2:
            item = census.entry(
                column=name, tier=tier, kind=census.KIND_FLOAT,
                raw_source="UNRECOVERED_V1_0_1_SOURCE",
                formula_reference="V1.0.1 source never recovered (archive closeout)",
                tolerance=None,
                tolerance_origin=census.ORIGIN_DECLARED_AT_FREEZE,
                note="disclosed Tier-2 member (parity unverifiable forever)")
        elif kinds[name] in (census.KIND_INTEGER, census.KIND_BOOLEAN,
                             census.KIND_CATEGORICAL):
            item = census.entry(
                column=name, tier=tier, kind=kinds[name],
                raw_source=f"study_files/outputs/study_v1/development/"
                           f"event_table.csv#{name}",
                formula_reference=f"V1 feature definition: {name} "
                                  f"(family={family}); formula reference to be "
                                  f"pinned at freeze",
                tolerance=census.tolerance_for(kinds[name]),
                tolerance_origin=census.ORIGIN_EXACT_EQUALITY,
                note="kind observed as exact-valued; exact-equality rule")
        else:
            item = census.entry(
                column=name, tier=tier, kind=census.KIND_FLOAT,
                raw_source=f"study_files/outputs/study_v1/development/"
                           f"event_table.csv#{name}",
                formula_reference=f"V1 feature definition: {name} "
                                  f"(family={family}); formula reference to be "
                                  f"pinned at freeze",
                tolerance={"kind": census.KIND_FLOAT, "abs": None, "rel": None,
                           "rule": "declare at freeze from the raw inputs' "
                                   "documented decimal precision (never from "
                                   "observed data)",
                           "origin": census.ORIGIN_DECLARED_AT_FREEZE,
                           "rounding_step": None},
                tolerance_origin=census.ORIGIN_DECLARED_AT_FREEZE,
                note="Tier-1 float: documented raw-input precision is not on "
                     "file; tolerance is a freeze-time declaration, never "
                     "derived from observed data (H-11)")
        item["family"] = family
        entries.append(item)

    manifest = {
        "schema_version": census.MANIFEST_SCHEMA_VERSION,
        "_CANDIDATE_STATUS": (
            "CANDIDATE_NOT_FROZEN_NOT_AN_AUDIT_RESULT (2026-10-13). "
            "Manifest-completeness scaffolding + freeze-time validation only. "
            "No column value is verified here; the value-level parity census "
            "runs inside the point_in_time_data_audit primitive at campaign "
            "time against a recomputed table."),
        "source_table": str(TABLE.relative_to(ROOT)).replace("\\", "/"),
        "source_table_columns": len(header),
        "non_feature_columns": non_feature,
        "feature_columns_observed": len(features),
        "feature_columns_in_inventory": census.INVENTORY_FEATURE_COLUMN_COUNT,
        "inventory_count_matches_observed":
            len(features) == census.INVENTORY_FEATURE_COLUMN_COUNT,
        "family_counts": {
            fam: sum(1 for name in features
                     if census.column_family(name) == fam)
            for fam in sorted({census.column_family(n) for n in features})},
        "inventory_family_counts": dict(sorted(
            census.INVENTORY_FAMILY_COUNTS.items())),
        "documented_tier_2": sorted(census.DOCUMENTED_TIER_2 & set(features)),
        "kind_classification": (
            "observed from CSV values (integer iff every value is integral; "
            "non-numeric -> categorical); selects the frozen comparison rule, "
            "never a tolerance width"),
        "columns": entries,
        "freeze_time_rulings_required": [
            "Expected-column set: the header yields "
            f"{len(features)} feature columns; the lineage inventory counts "
            f"{census.INVENTORY_FEATURE_COLUMN_COUNT}. The census module "
            "documents this off-by-one as a freeze-time ruling, not a silent "
            "reconciliation. Proposed ruling (owner confirms): the frozen "
            "table's own header defines the expected set.",
            f"Tier-1 float tolerances: {sum(1 for e in entries if e['tier'] == census.TIER_1 and (e['tolerance'] or {}).get('abs') is None)} "
            "float columns carry origin DECLARED_AT_FREEZE with no width. "
            "The freeze must declare each from the raw inputs' documented "
            "decimal precision (never from observed mismatches). No "
            "documented-precision source exists in the repository today.",
            "Count-once evidence rule: applied at freeze/adjudication per "
            "the v1.1.0 plan; nothing to execute in the manifest.",
        ],
    }

    errors = census.validate_manifest(manifest, features)
    manifest["completeness_validation"] = {
        "expected_columns_basis": "observed feature header (proposed ruling)",
        "errors": errors,
        "can_audit_pass": not errors,
    }
    OUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                   "utf-8")
    print("candidate manifest:", OUT.relative_to(ROOT))
    print("features:", len(features), "| tier1 floats pending declaration:",
          sum(1 for e in entries
              if e["tier"] == census.TIER_1
              and (e["tolerance"] or {}).get("abs") is None))
    print("exact-equality columns:", sum(1 for e in entries
          if e["tier"] == census.TIER_1
          and (e["tolerance"] or {}).get("abs") is not None))
    print("documented Tier-2:", len(manifest["documented_tier_2"]))
    print("completeness errors:", len(errors))
    for err in errors[:5]:
        print("  -", err)
    if errors:
        print("NOTE: errors are the expected fail-closed signal naming the "
              "freeze-time declarations still required; the manifest is "
              "complete as a candidate, not as an audit PASS.")


if __name__ == "__main__":
    main()
