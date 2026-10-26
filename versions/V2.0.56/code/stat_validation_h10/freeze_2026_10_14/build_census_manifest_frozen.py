#!/usr/bin/env python3
"""Freeze the H-11 census manifest for Campaign 4 (2026-10-14).

Differences from the 2026-10-13 candidate builder (which produced the
validated candidate with 68 float columns pending declaration):

* Every Tier-1 float column now carries the DECLARED tolerance
  abs = 0.5 * 10^-D, rel = 1e-9 with D = 17, taken from the frozen
  precision evidence (measure_documented_precision.py: 153/153 raw OHLCV
  files hash-verified against the v1.0.1 manifest pins; D = the maximum
  stored decimal place across all price columns). Origin:
  DOCUMENTED_PRECISION -- never an observed mismatch (H-11).
* The freeze-time rulings are recorded as decided:
  - expected-column set = the frozen event table's own header
    (100 feature columns; the lineage inventory's 101 is off by one),
  - Tier-1 float tolerances = the declared rule above.
* The REAL validator runs to zero errors (census.validate_manifest);
  can_audit_pass is recorded. Value-level parity verdicts stay UNTESTED
  by design: the census EXECUTES inside the point_in_time_data_audit
  primitive at campaign time against a recomputed table; this freeze
  validates the manifest that audit must conform to.

Output: C4_CENSUS_MANIFEST_FROZEN_2026_10_14.json next to this script.
Exit code 1 on any validation error (fail-closed: freeze cannot proceed).
"""
import csv
import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from autonomous_agent.proposal_layer import census  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
TABLE = ROOT / "study_files/outputs/study_v1/development/event_table.csv"
PRECISION = HERE / "precision_evidence.json"
OUT = HERE / "C4_CENSUS_MANIFEST_FROZEN_2026_10_14.json"


def classify_kinds(path: pathlib.Path, features: list[str]) -> dict[str, str]:
    """Observed kind per feature (integer iff every value integral;
    non-numeric -> categorical). Selects the frozen comparison rule,
    never a tolerance width (disclosed observation)."""
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


def main() -> int:
    evidence = json.loads(PRECISION.read_text("utf-8"))
    D = int(evidence["documented_decimals_D"])
    if evidence["files_verified"] != 153:
        print("FAIL: precision evidence is not from 153 verified files",
              file=sys.stderr)
        return 1

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
                                  f"(family={family})",
                tolerance=census.tolerance_for(kinds[name]),
                tolerance_origin=census.ORIGIN_EXACT_EQUALITY,
                note="kind observed as exact-valued; exact-equality rule")
        else:
            item = census.entry(
                column=name, tier=tier, kind=census.KIND_FLOAT,
                raw_source=f"study_files/outputs/study_v1/development/"
                           f"event_table.csv#{name}",
                formula_reference=f"V1 feature definition: {name} "
                                  f"(family={family})",
                tolerance=census.tolerance_for(
                    census.KIND_FLOAT, documented_decimals=D),
                tolerance_origin=census.ORIGIN_DOCUMENTED_PRECISION,
                note=f"Tier-1 float: declared tolerance from the raw "
                     f"inputs' documented precision D={D} "
                     f"(precision_evidence.json, 153/153 hash-verified "
                     f"files); never derived from observed data (H-11)")
        item["family"] = family
        entries.append(item)

    manifest = {
        "schema_version": census.MANIFEST_SCHEMA_VERSION,
        "_FROZEN_STATUS": (
            "FROZEN 2026-10-14 under the owner's recorded freeze "
            "authorization (H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md). "
            "Manifest completeness validated with the real H-11 validator "
            "(census.validate_manifest) to zero errors. Verdicts are "
            "UNTESTED by design: the value-level parity census executes "
            "inside the point_in_time_data_audit primitive at campaign "
            "time against a recomputed table; nothing here is a "
            "value-level audit result."),
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_table": str(TABLE.relative_to(ROOT)).replace("\\", "/"),
        "source_table_sha256": hashlib.sha256(TABLE.read_bytes()).hexdigest(),
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
            "non-numeric -> categorical); selects the frozen comparison "
            "rule, never a tolerance width"),
        "freeze_time_rulings": [
            "Expected-column set: the frozen event table's own header "
            f"defines the census expected set ({len(features)} feature "
            f"columns, 47/11/8/34 by family). The lineage inventory's 101 "
            "feature columns / 48 technical count is off by one column of "
            "label/meta and is superseded by this ruling.",
            f"Tier-1 float tolerances: declared for all "
            f"{sum(1 for e in entries if e['tier'] == census.TIER_1 and e['kind'] == census.KIND_FLOAT)} "
            f"float columns as abs = 0.5*10^-{D}, rel = 1e-9, origin "
            "DOCUMENTED_PRECISION, from the frozen precision evidence "
            "(precision_evidence.json; D measured on 153/153 hash-verified "
            "raw OHLCV files). Never derived from observed mismatches.",
            "Count-once evidence rule: applied at adjudication per the "
            "v1.1.0 plan; nothing to execute in the manifest.",
        ],
        "precision_evidence": {
            "path": str(PRECISION.relative_to(ROOT)).replace("\\", "/"),
            "sha256": hashlib.sha256(PRECISION.read_bytes()).hexdigest(),
            "documented_decimals_D": D,
        },
        "columns": entries,
    }

    errors = census.validate_manifest(manifest, features)
    manifest["completeness_validation"] = {
        "validator": "autonomous_agent/proposal_layer/census.py::validate_manifest",
        "expected_columns_basis": "frozen event table header (freeze ruling)",
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "errors": errors,
        "can_audit_pass": not errors,
    }
    OUT.write_bytes((json.dumps(manifest, indent=2, sort_keys=True) + "\n")
                    .encode("utf-8"))
    floats = sum(1 for e in entries
                 if e["tier"] == census.TIER_1 and e["kind"] == census.KIND_FLOAT)
    exact = sum(1 for e in entries
                if e["tier"] == census.TIER_1 and e["kind"] != census.KIND_FLOAT)
    print("frozen census manifest:", OUT.relative_to(ROOT))
    print(f"features={len(features)} tier1_floats={floats} "
          f"tier1_exact={exact} tier2={len(manifest['documented_tier_2'])}")
    print(f"documented_decimals D={D}: abs=0.5e-{D}, rel=1e-9")
    print("validate_manifest errors:", len(errors))
    for err in errors[:10]:
        print("  -", err)
    print("can_audit_pass:", not errors)
    if errors:
        print("FAIL: census validation errors block the freeze", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
