"""Frozen census manifest model and validator (H-11, point-in-time audit H-2).

Authorized for implementation 2026-10-12 (gate 3, D2-independent subset).

What this module is: the *rules* the census manifest must satisfy, plus a
scaffolder that derives the column inventory from the development table's
header. What it is not: a completed census. No column is verified here, no
tolerance is derived from observed data, and no verdict is produced — those
happen at freeze time and inside the audit primitive's own execution.

Invariants enforced (plan §"Remaining value-level checks", H-11):

* Every expected feature column appears in the manifest. A missing entry
  blocks audit PASS.
* Tier assignment is a declared input (documented recoverability), never an
  output of observed match/mismatch results.
* A tolerance's origin must be a documented one. ``OBSERVED_MISMATCH`` is
  rejected outright: a tolerance may never be widened (or invented) after a
  mismatch is seen.
* A Tier-2 (parity-UNVERIFIABLE) column can never return PASS, and a value
  mismatch on it can never yield CONFIRMED CONTAMINATION.
* Structural results (as-of ordering, banned columns, label consistency)
  never upgrade a column's value verdict.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

TIER_1 = "TIER_1_RECOMPUTE"
TIER_2 = "TIER_2_UNVERIFIABLE"
TIERS = (TIER_1, TIER_2)

VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
VERDICT_UNVERIFIABLE = "UNVERIFIABLE"
VERDICT_UNTESTED = "UNTESTED"
VERDICTS = (VERDICT_PASS, VERDICT_FAIL, VERDICT_UNVERIFIABLE, VERDICT_UNTESTED)

# Documented origins. Anything else is refused (fail-closed).
ORIGIN_DOCUMENTED_PRECISION = "DOCUMENTED_PRECISION"
ORIGIN_DECLARED_AT_FREEZE = "DECLARED_AT_FREEZE"
ORIGIN_EXACT_EQUALITY = "EXACT_EQUALITY"
ORIGIN_OBSERVED_MISMATCH = "OBSERVED_MISMATCH"   # banned by construction
ALLOWED_ORIGINS = (ORIGIN_DOCUMENTED_PRECISION, ORIGIN_DECLARED_AT_FREEZE,
                   ORIGIN_EXACT_EQUALITY)

KIND_INTEGER = "integer"
KIND_BOOLEAN = "boolean"
KIND_CATEGORICAL = "categorical"
KIND_FLOAT = "float"
KINDS = (KIND_INTEGER, KIND_BOOLEAN, KIND_CATEGORICAL, KIND_FLOAT)
FLOAT_RELATIVE_TOLERANCE = 1e-9     # documented float64 derived-computation chain

# Metadata / label columns of the development event table: never features,
# never recomputed by the census.
NON_FEATURE_COLUMNS: frozenset[str] = frozenset({
    "ticker", "date", "event_id", "zone_id", "signal_close", "signal_timestamp",
    "feature_asof_date", "label_valid", "entry_date", "exit_date", "entry_open",
    "exit_open", "hold1_ret", "label",
})

# Archive-closeout Tier-2 members: V1.0.1 source never recovered, so value
# parity is unverifiable forever. Tier is declared here from documentation,
# never from any observed match/mismatch result.
DOCUMENTED_TIER_2: frozenset[str] = frozenset({"rsi14", "atr_pct", "zone_width_pct"})

# The plan/inventory counts 101 feature columns; the header yields 100
# (114 total minus 14 label/meta). The scaffold reports both rather than
# picking one — the census's expected-column set is a freeze-time ruling.
INVENTORY_FEATURE_COLUMN_COUNT = 101

MANIFEST_SCHEMA_VERSION = 1
DRAFT_STATUS = "DRAFT_NOT_FROZEN_NOT_AN_AUDIT_RESULT"


class CensusError(Exception):
    """Manifest or entry violates a frozen H-11 rule."""


# ------------------------------------------------------------- classification
def column_family(name: str) -> str:
    """Inventory family for a feature column (grouping, not a verdict).

    Corrected 2026-10-12 against the actual header: the scaffold's first
    prefix-only version mis-filed five columns.

    * ``ob_unmitigated_bull_count`` / ``ob_unmitigated_bear_count`` are
      order-block structure (34 = 16 bull + 16 bear + 2 unmitigated), which is
      why the inventory's "ob_bull_*/ob_bear_* = 34" only reproduces when
      they are counted in that family.
    * ``relative_strength_*`` is price/volume technical (the plan's technical
      family lists ``relative_*``), not a market benchmark -- the inventory's
      benchmark family is exactly spy_*/qqq_*/iwm_*/vix_* = 11.

    With these rules the four families sum to the 100 feature columns that
    actually exist (47 + 11 + 8 + 34).
    """
    if name.startswith(("ob_bull_", "ob_bear_", "ob_unmitigated_")):
        return "order_block_structural"
    if name.startswith("zone_base_"):
        return "zone_base"
    if name.startswith(("spy_", "qqq_", "iwm_", "vix_")):
        return "market_benchmark"
    return "price_volume_technical"


# Family counts the header actually yields under column_family above. The
# lineage inventory (2026-10-09 section 3) claims 48/11/8/34 = 101 features
# plus 13 label/meta; the header yields 47/11/8/34 = 100 plus 14. Every family
# except price/volume reproduces exactly, so the inventory is off by one
# column it counted as a technical feature that is in fact label/meta -- a
# freeze-time ruling, not something this scaffold may decide.
EXPECTED_FAMILY_COUNTS = {
    "price_volume_technical": 47,
    "market_benchmark": 11,
    "zone_base": 8,
    "order_block_structural": 34,
}
INVENTORY_FAMILY_COUNTS = {
    "price_volume_technical": 48,
    "market_benchmark": 11,
    "zone_base": 8,
    "order_block_structural": 34,
}


# ------------------------------------------------------------- tolerances
def tolerance_for(kind: str, *, documented_decimals: int | None = None,
                  rounding_step: str | None = None) -> dict[str, Any]:
    """Frozen tolerance policy (H-11): documented precision, not observations.

    integer/boolean/categorical compare at exact equality. float combines
    half a unit of the last documented decimal place of its raw inputs with a
    relative 1e-9 for the float64 derived-computation chain, plus any
    documented rounding step. If the raw inputs' documented precision is not
    on file, the tolerance is NOT derivable here and must be declared at
    freeze — fail-closed, never guessed.
    """
    if kind not in KINDS:
        raise CensusError(f"unknown column kind {kind!r}")
    if kind in (KIND_INTEGER, KIND_BOOLEAN, KIND_CATEGORICAL):
        return {"kind": kind, "abs": 0.0, "rel": 0.0,
                "rule": "exact_equality", "origin": ORIGIN_EXACT_EQUALITY,
                "rounding_step": rounding_step}
    if documented_decimals is None:
        raise CensusError(
            f"tolerance for float column not derivable: documented decimal "
            f"precision of the raw inputs is not on file; declare it at "
            f"freeze (never derive it from observed data)")
    if int(documented_decimals) < 0:
        raise CensusError("documented_decimals must be >= 0")
    return {"kind": KIND_FLOAT,
            "abs": 0.5 * (10.0 ** -int(documented_decimals)),
            "rel": FLOAT_RELATIVE_TOLERANCE,
            "rule": ("half a unit of the last documented decimal place + "
                     "relative 1e-9 for the float64 chain"),
            "origin": ORIGIN_DOCUMENTED_PRECISION,
            "rounding_step": rounding_step}


def entry(*, column: str, tier: str, kind: str, raw_source: str,
          formula_reference: str, tolerance: Mapping[str, Any] | None = None,
          tolerance_origin: str | None = None, rows_compared: int = 0,
          verdict: str = VERDICT_UNTESTED,
          value_mismatch_can_yield_contamination: bool | None = None,
          structural_pass: bool | None = None,
          note: str = "") -> dict[str, Any]:
    """Build one manifest entry, validating the frozen rules as it is built."""
    if tier not in TIERS:
        raise CensusError(f"unknown tier {tier!r}")
    if verdict not in VERDICTS:
        raise CensusError(f"unknown verdict {verdict!r}")
    origin = tolerance_origin or (tolerance or {}).get("origin")
    if tier == TIER_1 and tolerance is None:
        raise CensusError(f"{column}: Tier-1 column needs a frozen tolerance")
    if tier == TIER_1 and origin not in ALLOWED_ORIGINS:
        raise CensusError(
            f"{column}: tolerance origin {origin!r} is not a documented one "
            f"(allowed: {ALLOWED_ORIGINS}); observed results may never set it")
    if tier == TIER_2:
        # Tier-2 is a *declared* parity status from documented
        # unrecoverability, not a result of a run: the manifest marks such a
        # column UNVERIFIABLE, and PASS/FAIL are refused outright.
        if verdict in (VERDICT_PASS, VERDICT_FAIL):
            raise CensusError(
                f"{column}: a Tier-2 (parity-UNVERIFIABLE) column can never "
                f"be {verdict}; its status is declared, never measured")
        verdict = VERDICT_UNVERIFIABLE
        if value_mismatch_can_yield_contamination is None:
            value_mismatch_can_yield_contamination = False
    if value_mismatch_can_yield_contamination is None:
        value_mismatch_can_yield_contamination = True
    if tier == TIER_2 and value_mismatch_can_yield_contamination:
        raise CensusError(
            f"{column}: a Tier-2 (UNVERIFIABLE) column can never yield "
            f"CONFIRMED CONTAMINATION from a value mismatch")
    return {"column": column, "tier": tier, "kind": kind,
            "raw_source": raw_source, "formula_reference": formula_reference,
            "tolerance": dict(tolerance) if tolerance else None,
            "tolerance_origin": origin,
            "rows_compared": int(rows_compared),
            "verdict": verdict,
            "value_mismatch_can_yield_contamination":
                bool(value_mismatch_can_yield_contamination),
            "structural_pass": structural_pass, "note": note}


def tier_for(column: str) -> str:
    return TIER_2 if column in DOCUMENTED_TIER_2 else TIER_1


# ------------------------------------------------------------- validation
def validate_manifest(manifest: Mapping[str, Any],
                      expected_columns: Sequence[str]) -> list[str]:
    """All reasons this manifest cannot back an audit PASS (empty == ok)."""
    errors: list[str] = []
    if not isinstance(manifest, Mapping):
        return ["manifest is not a mapping"]
    columns = manifest.get("columns")
    if not isinstance(columns, list):
        return ["manifest has no columns list"]
    expected = list(expected_columns)
    by_name: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(columns):
        if not isinstance(item, Mapping):
            errors.append(f"entry {index} is not a mapping")
            continue
        name = item.get("column")
        if not isinstance(name, str) or not name:
            errors.append(f"entry {index} has no column name")
            continue
        if name in by_name:
            errors.append(f"duplicate manifest entry for column {name!r}")
        by_name[name] = item

    for name in expected:                       # missing entry blocks PASS
        if name not in by_name:
            errors.append(f"missing manifest entry for column {name!r}")
    for name in by_name:                        # undeclared extras are refused
        if name not in expected:
            errors.append(f"manifest carries column {name!r} that is not an "
                          f"expected feature column")

    for name, item in by_name.items():
        tier = item.get("tier")
        if tier not in TIERS:
            errors.append(f"{name}: unknown tier {tier!r}")
            continue
        verdict = item.get("verdict")
        if verdict not in VERDICTS:
            errors.append(f"{name}: unknown verdict {verdict!r}")
        origin = item.get("tolerance_origin")
        if tier == TIER_1:
            tolerance = item.get("tolerance")
            if not isinstance(tolerance, Mapping):
                errors.append(f"{name}: Tier-1 entry without a frozen tolerance")
            elif tolerance.get("abs") is None or tolerance.get("rel") is None:
                errors.append(f"{name}: Tier-1 tolerance is not frozen "
                              f"(abs/rel undeclared); a draft placeholder "
                              f"cannot back an audit PASS")
            if origin not in ALLOWED_ORIGINS:
                errors.append(f"{name}: tolerance origin {origin!r} is not "
                              f"documented (observed results may never set it)")
            if not isinstance(item.get("raw_source"), str) or \
                    not item.get("raw_source"):
                errors.append(f"{name}: Tier-1 entry without a raw source")
            if not isinstance(item.get("formula_reference"), str) or \
                    not item.get("formula_reference"):
                errors.append(f"{name}: Tier-1 entry without a formula reference")
        if tier == TIER_2:
            if verdict in (VERDICT_PASS, VERDICT_FAIL):
                errors.append(f"{name}: Tier-2 (parity-UNVERIFIABLE) column "
                              f"may never be {verdict}")
            if item.get("value_mismatch_can_yield_contamination"):
                errors.append(f"{name}: Tier-2 column may never yield "
                              f"CONFIRMED CONTAMINATION from a value mismatch")
        if verdict == VERDICT_UNTESTED and item.get("rows_compared"):
            errors.append(f"{name}: UNTESTED column claims rows compared")
    return errors


def can_audit_pass(manifest: Mapping[str, Any],
                   expected_columns: Sequence[str]) -> bool:
    return not validate_manifest(manifest, expected_columns)


def combine_verdict(value_verdict: str, *, structural_pass: bool) -> str:
    """Structural checks never upgrade a column's value verdict.

    An UNVERIFIABLE or FAIL value verdict survives a clean structural result
    unchanged; only a value PASS is PASS. Structure can downgrade nothing and
    upgrade nothing.
    """
    if value_verdict not in VERDICTS:
        raise CensusError(f"unknown value verdict {value_verdict!r}")
    return value_verdict


# ------------------------------------------------------------- scaffolding
def _read_header(path: Path) -> list[str]:
    """Header-only read of the development table (no data rows)."""
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as stream:
        reader = csv.reader(stream)
        return next(reader)


def scaffold_manifest(table_path: Path | str,
                      *, documented_decimals: Mapping[str, int] | None = None
                      ) -> dict[str, Any]:
    """Draft manifest: column inventory + declared tiers, nothing verified.

    Tolerances are attached only where the documented precision is supplied
    (``documented_decimals``) or the column is exact-valued; every float
    column without documented precision stays ``None`` and therefore cannot
    back an audit PASS — which is the point: the freeze must declare them.
    """
    path = Path(table_path)
    header = _read_header(path)
    features = [name for name in header if name not in NON_FEATURE_COLUMNS]
    decimals = dict(documented_decimals or {})
    entries = []
    for name in features:
        tier = tier_for(name)
        family = column_family(name)
        if tier == TIER_2:
            item = entry(
                column=name, tier=tier, kind=KIND_FLOAT,
                raw_source="UNRECOVERED_V1_0_1_SOURCE",
                formula_reference="V1.0.1 source never recovered "
                                  "(archive closeout)",
                tolerance=None, tolerance_origin=ORIGIN_DECLARED_AT_FREEZE,
                note="disclosed Tier-2 member")
            item["family"] = family
            entries.append(item)
            continue
        if name in decimals:
            tolerance = tolerance_for(KIND_FLOAT, documented_decimals=decimals[name])
            origin = tolerance["origin"]
        else:
            # Unknown dtype/precision: declared at freeze, never guessed here.
            tolerance = {"kind": KIND_FLOAT, "abs": None, "rel": None,
                         "rule": "declare at freeze from documented precision",
                         "origin": ORIGIN_DECLARED_AT_FREEZE}
            origin = ORIGIN_DECLARED_AT_FREEZE
        item = entry(
            column=name, tier=tier, kind=KIND_FLOAT,
            raw_source=f"study_files/outputs/study_v1/development/event_table.csv#{name}",
            formula_reference=f"V1 feature definition: {name} "
                              f"(family={family}); formula reference to be "
                              f"pinned at freeze",
            tolerance=tolerance, tolerance_origin=origin,
            note="value parity UNTESTED")
        item["family"] = family
        entries.append(item)
    from collections import Counter
    families = Counter(column_family(name) for name in features)
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "_DRAFT_STATUS": DRAFT_STATUS,
        "source_table": str(path).replace("\\", "/"),
        "source_table_columns": len(header),
        "non_feature_columns": sorted(NON_FEATURE_COLUMNS & set(header)),
        "feature_columns_observed": len(features),
        "feature_columns_in_inventory": INVENTORY_FEATURE_COLUMN_COUNT,
        "inventory_count_matches_observed":
            len(features) == INVENTORY_FEATURE_COLUMN_COUNT,
        "family_counts": dict(sorted(families.items())),
        "inventory_family_counts": dict(sorted(INVENTORY_FAMILY_COUNTS.items())),
        "family_counts_match_inventory": (
            dict(sorted(families.items())) == dict(sorted(INVENTORY_FAMILY_COUNTS.items()))),
        "documented_tier_2": sorted(DOCUMENTED_TIER_2 & set(features)),
        "columns": entries,
        "note": ("DRAFT scaffolding only. No column is verified, no census has "
                 "run, and no verdict here may be cited as evidence. Tier-1 "
                 "tolerances for float columns without documented precision "
                 "are intentionally absent: the freeze must declare them, and "
                 "they may never be derived from observed mismatches. The "
                 "family classifier is a corrected grouping derived from the "
                 "actual header (ob_unmitigated_* counts as order-block "
                 "structure; relative_strength_* counts as price/volume "
                 "technical). The four families sum to the 100 feature "
                 "columns that exist; the lineage inventory's 101/13 split "
                 "and its 48 technical column are off by one and need a "
                 "freeze-time ruling, not a silent reconciliation."),
    }
