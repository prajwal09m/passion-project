"""Reviewed design-primitive library (Phase 1 component 2).

A proposal may ONLY compose these primitives with their declared parameter
grids. Executable behavior lives entirely in the reviewed harness
(``autonomous_agent/recipe_harness.py``); this module declares identity,
class, and executability — never code.

``executable=False`` primitives are forward-declarations: they may be designed
and validated, but the compiler refuses them (``PRIMITIVE_NOT_EXECUTABLE``)
until a reviewed harness version supports them. The default generator never
selects them (``bias_policy.json.allow_future_primitives`` is false).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from autonomous_agent.proposal_layer import schema

PRIMITIVE_LIBRARY_VERSION = schema.PRIMITIVE_LIBRARY_VERSION

# Harness version the five dormant primitives require. The reviewed harness
# accepts a ``harness_version`` selector; when it is absent the harness stays
# byte-identical v1.0.0, so archived specs rerun unchanged.
HARNESS_VERSION_1_1_0 = "1.1.0"


def _v110_extra(primitive_id: str, *, margin_value: float = 0.0,
                ci_lower_min: float = -0.01,
                min_rows: int = 30, min_events: int = 5,
                related_primitive: str | None = None) -> dict[str, Any]:
    """Frozen v1.1.0 acceptance data for one primitive (H-1, H-6, H-10b).

    Composed from the frozen tables in ``autonomous_agent.three_valued`` so
    the primitive definition, the ladder, and the floors cannot drift apart.
    The ladder-family ↔ ``multiplicity.FAMILIES`` agreement is asserted in
    ``test_multiplicity.py`` (the multiplicity machinery stays imported only
    by the loop and its tests — inertness rule). Every margin carries the
    PROVISIONAL marker: -0.01 is a study-consistency margin, not a
    statistically validated bound (H-1).
    """
    from autonomous_agent import three_valued
    ladder = three_valued.ladder_for(primitive_id)
    family = ladder.get("family")
    margin = three_valued.Margin(value=margin_value, ci_lower_min=ci_lower_min)
    extra: dict[str, Any] = {
        "harness_version": HARNESS_VERSION_1_1_0,
        "frozen_ladder": ladder,
        "acceptance_margin": {"value": margin.value,
                              "ci_lower_min": margin.ci_lower_min,
                              "provisional": margin.provisional,
                              "provenance": margin.provenance},
        "sample_floors": {"min_rows": min_rows, "min_events": min_events,
                          "min_boot_for_inference":
                              three_valued.MIN_BOOT_FOR_INFERENCE},
        "multiplicity": {"family": family,
                         "members_per_experiment":
                             ladder["members_per_experiment"],
                         "correction": "holm_step_down",
                         "pooling": "campaign_end_over_complete_family",
                         "formal_refutation_only_at_campaign_end": True},
        "three_valued_model": {"robust": three_valued.ROBUST,
                               "inconclusive": three_valued.INCONCLUSIVE,
                               "formal_refuted_reserved_for_campaign_end":
                                   three_valued.FORMAL_REFUTED,
                               "point_estimate_only_pass": "forbidden"},
    }
    if related_primitive is not None:
        extra["related_primitive"] = related_primitive
    return extra


@dataclass(frozen=True)
class ParamSpec:
    kind: str                      # "enum" | "int"
    values: tuple[Any, ...] = ()   # for enum
    low: int | None = None         # for int
    high: int | None = None

    def check(self, value: Any) -> bool:
        if self.kind == "enum":
            return value in self.values
        if self.kind == "int":
            if isinstance(value, bool) or not isinstance(value, int):
                return False
            return self.low <= value <= self.high
        return False


@dataclass(frozen=True)
class Primitive:
    primitive_id: str
    category: str                  # feature | model | calibration | robustness | analysis
    direction: str                 # research direction it serves
    default_class: str             # confirmatory | falsification | replication | exploration
    falsification_capable: bool
    executable: bool               # supported by the reviewed harness today
    harness_min_version: str
    params: Mapping[str, ParamSpec]
    purpose: str
    # Structural mapping to harness config keys (same shapes the recipes use).
    accepts_arm_pair: bool = False
    accepts_arm: bool = False
    default_metric: str = "pooled_roc_auc_delta"
    config_note: str = ""
    extra: Mapping[str, Any] = field(default_factory=dict)


_ARM_PAIRS = ("A->B", "B->C", "C->D")
_ARMS = ("A", "B", "C", "D")
_ESTIMATORS = ("LogisticRegression", "LightGBM")


LIBRARY: tuple[Primitive, ...] = (
    Primitive(
        primitive_id="feature_arm_comparison",
        category="feature", direction="feature_engineering",
        default_class="confirmatory", falsification_capable=True,
        executable=True, harness_min_version="1.0.0",
        accepts_arm_pair=True,
        params={
            "arm_pair": ParamSpec("enum", _ARM_PAIRS),
            "estimator": ParamSpec("enum", _ESTIMATORS),
            "n_boot": ParamSpec("int", low=100, high=2000),
        },
        purpose="Compare two nested feature arms on identical purged folds.",
        config_note="Non-degradation gates: delta >= 0, CI lower >= -0.01.",
    ),
    Primitive(
        primitive_id="model_class_comparison",
        category="model", direction="model_architecture",
        default_class="confirmatory", falsification_capable=True,
        executable=True, harness_min_version="1.0.0",
        accepts_arm=True,
        params={
            "arm": ParamSpec("enum", _ARMS),
            "n_boot": ParamSpec("int", low=100, high=2000),
        },
        purpose="Compare LogisticRegression vs LightGBM on one fixed arm.",
        config_note="Non-degradation gates: delta >= 0, CI lower >= -0.01.",
    ),
    Primitive(
        primitive_id="calibration_stability_check",
        category="calibration", direction="calibration",
        default_class="confirmatory", falsification_capable=True,
        executable=True, harness_min_version="1.0.0",
        accepts_arm_pair=True,
        params={
            "arm_pair": ParamSpec("enum", _ARM_PAIRS),
            "estimator": ParamSpec("enum", ("LightGBM",)),
            "calibration_bins": ParamSpec("int", low=3, high=20),
            "n_boot": ParamSpec("int", low=100, high=2000),
        },
        purpose="Measure Brier/ECE stability across chronological folds and years.",
        config_note="Calibration gates: Brier <= +0.005, ECE <= +0.02 absolute.",
    ),
    Primitive(
        primitive_id="year_stability_falsifier",
        category="robustness", direction="validation",
        default_class="falsification", falsification_capable=True,
        executable=True, harness_min_version="1.0.0",
        accepts_arm_pair=True,
        params={
            "arm_pair": ParamSpec("enum", _ARM_PAIRS),
            "estimator": ParamSpec("enum", _ESTIMATORS),
            "n_boot": ParamSpec("int", low=100, high=2000),
        },
        purpose="Challenge the pooled gain: does it hold in EVERY predeclared "
                "year, or does at least one year refute it?",
        default_metric="min_year_delta",
        config_note="Framed as a falsifier; harness already reports per-year deltas.",
    ),
    Primitive(
        primitive_id="purge_sensitivity_probe",
        category="robustness", direction="validation",
        default_class="falsification", falsification_capable=True,
        executable=True, harness_min_version="1.1.0",
        accepts_arm_pair=True,
        params={
            "arm_pair": ParamSpec("enum", _ARM_PAIRS),
            # H-10b: family-feeding experiments require n_boot >= 1000
            # (500 is disallowed for Holm-family primitives).
            "n_boot": ParamSpec("int", low=1000, high=2000),
        },
        purpose="Re-run with stricter target-maturity purge widths and test "
                "whether arm ranking survives.",
        default_metric="ci_lower",
        config_note="Purge-sensitivity falsifier: every purge rung must "
                    "independently hold its point + CI requirement "
                    "(IUT); a rung below its sample floor is INCONCLUSIVE.",
        extra=_v110_extra("purge_sensitivity_probe"),
    ),
    Primitive(
        primitive_id="regime_split_analysis",
        category="analysis", direction="error_analysis",
        default_class="exploration", falsification_capable=True,
        executable=True, harness_min_version="1.1.0",
        accepts_arm=True,
        params={
            "arm": ParamSpec("enum", _ARMS),
            # H-10b: regime family (Holm) requires n_boot >= 1000.
            "n_boot": ParamSpec("int", low=1000, high=2000),
        },
        purpose="Slice out-of-fold errors by predeclared volatility/time regimes.",
        default_metric="pooled_roc_auc_delta",
        config_note="Regime-split analysis: both regime cells must "
                    "independently hold their point + CI requirement "
                    "(IUT); an under-sized cell is INCONCLUSIVE.",
        extra=_v110_extra("regime_split_analysis"),
    ),
    Primitive(
        primitive_id="complexity_reduction_check",
        category="model", direction="model_complexity",
        default_class="confirmatory", falsification_capable=True,
        executable=True, harness_min_version="1.1.0",
        accepts_arm=True,
        params={
            "arm": ParamSpec("enum", _ARMS),
            # H-10b: complexity family (Holm, m=1) requires n_boot >= 1000.
            "n_boot": ParamSpec("int", low=1000, high=2000),
        },
        purpose="Test whether a simpler model class retains within-margin "
                "performance under the matched protocol.",
        default_metric="pooled_roc_auc_delta",
        config_note="Complexity-reduction check is a RELATED REANALYSIS of "
                    "model_class_comparison, never independent "
                    "confirmation; the count-once rule applies.",
        extra=_v110_extra("complexity_reduction_check",
                          related_primitive="model_class_comparison"),
    ),
    Primitive(
        primitive_id="target_horizon_robustness",
        category="analysis", direction="target_design",
        default_class="exploration", falsification_capable=True,
        executable=True, harness_min_version="1.1.0",
        accepts_arm=True,
        params={
            "arm": ParamSpec("enum", _ARMS),
            # H-10b: horizon family (Holm) requires n_boot >= 1000.
            "n_boot": ParamSpec("int", low=1000, high=2000),
        },
        purpose="Pre-registered horizon comparison on development folds only.",
        default_metric="pooled_roc_auc_delta",
        config_note="Horizon robustness: every horizon rung rebuilds its "
                    "labels and re-verifies the maturity purge; all rungs "
                    "must independently hold (IUT).",
        extra=_v110_extra("target_horizon_robustness"),
    ),
    Primitive(
        primitive_id="point_in_time_data_audit",
        category="analysis", direction="data_quality",
        default_class="exploration", falsification_capable=False,
        executable=True, harness_min_version="1.1.0",
        accepts_arm=True,
        params={
            "arm": ParamSpec("enum", _ARMS),
            # The declared inference floor (three_valued.MIN_BOOT_FOR_INFERENCE
            # = 1000) binds every v1.1.0 primitive's config, family-feeding
            # or not: the rendered n_boot may never undercut the declared
            # sample floor.
            "n_boot": ParamSpec("int", low=1000, high=2000),
        },
        purpose="Verify source vintage, universe membership, timestamps and "
                "label maturity before modeling.",
        default_metric="pooled_roc_auc_delta",
        config_note="Point-in-time audit is tri-state (CLEAN / "
                    "UNVERIFIABLE / CONFIRMED_CONTAMINATION); UNVERIFIABLE "
                    "never returns PASS, and a disclosed Tier-2 defect is an "
                    "audit FAIL, never contamination (owner ruling R-4).",
        extra=_v110_extra("point_in_time_data_audit"),
    ),
    # -- Campaign 2 Stage 4 (2026-10-05): bounded deterministic expansions ---
    # Every addition renders into the EXISTING closed harness config schema
    # (recipe_harness.ALLOWED_CONFIG_KEYS): acceptance margins and seed sets
    # are predeclared static library data, never free-form input. No new
    # config keys, no new code paths, no execution claim beyond what the
    # reviewed harness runs today.
    Primitive(
        primitive_id="minimum_effect_falsifier",
        category="robustness", direction="validation",
        default_class="falsification", falsification_capable=True,
        executable=True, harness_min_version="1.0.0",
        accepts_arm_pair=True,
        params={
            "arm_pair": ParamSpec("enum", _ARM_PAIRS),
            "estimator": ParamSpec("enum", _ESTIMATORS),
            "n_boot": ParamSpec("int", low=100, high=2000),
            "min_effect": ParamSpec("enum", ("meaningful", "strong")),
        },
        purpose="Challenge a marginal gain: it must clear a predeclared "
                "practically meaningful minimum effect, not merely a "
                "non-negative bar.",
        default_metric="pooled_roc_auc_delta",
        config_note="Minimum-effect gates: pooled OOF AUC delta must meet "
                    "the predeclared practical bar on the frozen purged "
                    "folds.",
        extra={
            "criteria_by_param": {
                "min_effect": {
                    "meaningful": {
                        "primary_metric_min_delta": 0.005,
                        "note": "Minimum-effect gates: pooled OOF AUC delta "
                                "must be at least 0.005 (practically "
                                "meaningful) on the frozen purged folds."},
                    "strong": {
                        "primary_metric_min_delta": 0.01,
                        "note": "Minimum-effect gates: pooled OOF AUC delta "
                                "must be at least 0.01 (strong practical "
                                "effect) on the frozen purged folds."},
                },
            },
        },
    ),
    Primitive(
        primitive_id="complexity_premium_check",
        category="model", direction="model_complexity",
        default_class="confirmatory", falsification_capable=True,
        executable=True, harness_min_version="1.0.0",
        accepts_arm=True,
        params={
            "arm": ParamSpec("enum", _ARMS),
            "n_boot": ParamSpec("int", low=100, high=2000),
            "premium": ParamSpec("enum", ("standard", "high")),
        },
        purpose="The complexer estimator must clear a predeclared complexity "
                "premium over LogisticRegression to justify its extra "
                "complexity, otherwise the simpler model stands.",
        default_metric="pooled_roc_auc_delta",
        config_note="Complexity-premium gates: the candidate estimator must "
                    "clear the predeclared premium over the simpler "
                    "reference.",
        extra={
            "criteria_by_param": {
                "premium": {
                    "standard": {
                        "primary_metric_min_delta": 0.005,
                        "note": "Complexity-premium gates: the candidate "
                                "estimator must beat LogisticRegression by "
                                "at least 0.005 pooled OOF AUC to justify "
                                "the added complexity."},
                    "high": {
                        "primary_metric_min_delta": 0.01,
                        "note": "Complexity-premium gates: the candidate "
                                "estimator must beat LogisticRegression by "
                                "at least 0.01 pooled OOF AUC to justify "
                                "the added complexity."},
                },
            },
        },
    ),
    Primitive(
        primitive_id="seed_set_replication",
        category="robustness", direction="validation",
        default_class="replication", falsification_capable=False,
        executable=True, harness_min_version="1.0.0",
        accepts_arm_pair=True,
        params={
            "arm_pair": ParamSpec("enum", _ARM_PAIRS),
            "estimator": ParamSpec("enum", _ESTIMATORS),
            "n_boot": ParamSpec("int", low=100, high=2000),
        },
        purpose="Re-run the identical comparison on the independent "
                "predeclared seed set 7, 17, 29 so the non-degradation "
                "claim must reproduce on different random draws.",
        default_metric="pooled_roc_auc_delta",
        config_note="Reproduction gates: identical design and gates, "
                    "independent predeclared seed set.",
        extra={"seeds": [7, 17, 29]},
    ),
)

_BY_ID = {primitive.primitive_id: primitive for primitive in LIBRARY}


def get(primitive_id: str) -> Primitive | None:
    return _BY_ID.get(primitive_id)


def all_ids() -> tuple[str, ...]:
    return tuple(sorted(_BY_ID))


def validate_params(primitive_id: str, params: Any) -> list[str]:
    """Return why this primitive/params combination is unusable (empty = ok)."""
    primitive = _BY_ID.get(str(primitive_id))
    if primitive is None:
        return [f"Unknown primitive {primitive_id!r}."]
    if not isinstance(params, dict):
        return [f"Primitive {primitive_id!r} params must be a mapping."]
    unknown = sorted(set(params) - set(primitive.params))
    if unknown:
        return [f"Unknown parameters {unknown} for primitive {primitive_id!r}."]
    missing = sorted(set(primitive.params) - set(params))
    if missing:
        return [f"Missing parameters {missing} for primitive {primitive_id!r}."]
    problems = []
    for key, spec in primitive.params.items():
        if not spec.check(params[key]):
            problems.append(
                f"Parameter {key!r}={params[key]!r} outside reviewed spec "
                f"for primitive {primitive_id!r}.")
    return problems
