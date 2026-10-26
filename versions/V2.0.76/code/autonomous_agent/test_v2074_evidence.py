"""Era-pinned verification of champion V2.0.74's evidence (Campaign 5 audit).

Reproduces everything reproducible WITHOUT refitting models (fits would be
new market-data fitting, which is prohibited):
  * the predeclared decision gate recomputed from the reported ROUNDED
    values (the gate itself gates on rounded values, so this reproduces the
    exact accept decision from retained artifacts);
  * internal consistency between the evaluation layers (release metadata vs
    results block) and the candidate workspace;
  * byte-identity of the audited code with the workspace that ran and the
    immutable version snapshot (the live tree is pinned separately: it is
    the owner-authorized harness v1.3.0, not the v1.1.0 audit artifact);
  * predeclared experiment parameters (arm pair, n_boot, seeds, premium);
  * holdout non-access facts.

These are evidence-integrity tests, not generalization claims: they pin
what THIS artifact reports and how it was gated. See
test_protocol_fingerprint.py for the fingerprint-era pins.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from autonomous_agent.recipe_harness import decision_criteria_pass

WORKSPACE = Path(__file__).resolve().parents[1]
VERSION_DIR = WORKSPACE / "versions" / "V2.0.74"
CANDIDATE_DIR = (WORKSPACE / "autonomous_agent" / "candidates"
                 / "exp-proposal-a987db219da2")
LEADER = "exp-proposal-a987db219da2"
PIN_DELTA = 0.023312
PIN_CI = (0.008653, 0.036973)

pytestmark = pytest.mark.skipif(
    not (VERSION_DIR / "evaluation.json").is_file()
    or not (CANDIDATE_DIR / "workspace" / "outputs" / "evaluation.json").is_file(),
    reason="V2.0.74 artifacts unavailable in this checkout")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluation_layers() -> tuple[dict, dict, dict, dict]:
    version = _load(VERSION_DIR / "version.json")
    snap_eval = _load(VERSION_DIR / "evaluation.json")
    work_eval = _load(CANDIDATE_DIR / "workspace" / "outputs" / "evaluation.json")
    config = _load(CANDIDATE_DIR / "workspace" / "autonomous_agent"
                   / "experiments" / "experiment_config.json")
    return version, snap_eval, work_eval, config


def test_reported_values_are_pinned() -> None:
    _, snap_eval, work_eval, _ = evaluation_layers()
    primary = snap_eval["results"]["primary_metric"]
    assert primary["delta"] == PIN_DELTA == work_eval["results"]["primary_metric"]["delta"]
    ci = snap_eval["results"]["uncertainty_interval"]
    assert (ci["lower"], ci["upper"]) == PIN_CI
    # Beta-vs-alpha orientation and the workspace/snapshot agreement.
    assert primary["value"] > primary["champion_value"]
    assert snap_eval["results"] == work_eval["results"]


def test_decision_gate_reproduces_from_rounded_reported_values() -> None:
    """The predeclared gate acts on the rounded reported values, so the
    ACCEPT decision is exactly reproducible from evaluation.json alone:
    delta >= 0.01, ci_lower >= -0.01, folds >= 3 (arm C, premium=high
    predeclared no Brier/ECE degradation caps -> absent margins)."""
    version, snap_eval, _, config = evaluation_layers()
    results = snap_eval["results"]
    delta = results["primary_metric"]["delta"]
    ci_lower = results["uncertainty_interval"]["lower"]
    n_folds = len(config["folds"])
    passed, detail = decision_criteria_pass(
        delta, ci_lower, n_folds, results["calibration"],
        config["evaluation_criteria"])
    assert passed is True, detail
    assert snap_eval["results"]["decision_criteria_passed"] is True
    assert version["evaluation"]["acceptance_recommendation"] == "PROMOTE"
    # The predeclared complexity premium threshold itself.
    assert config["evaluation_criteria"]["primary_metric_min_delta"] == 0.01


def test_release_metadata_matches_results_and_pins() -> None:
    _, snap_eval, _, _ = evaluation_layers()
    release = snap_eval["release_metadata"]
    metrics = release["metrics"]
    results = snap_eval["results"]
    assert metrics["delta_auc"] == results["primary_metric"]["delta"] == PIN_DELTA
    assert metrics["pooled_roc_auc_b"] == results["primary_metric"]["value"]
    assert metrics["pooled_roc_auc_a"] == results["primary_metric"]["champion_value"]
    # Complexity delta: same 65-feature arm on both sides (estimator-only contrast).
    assert results["complexity_delta"] == {
        "delta": 0, "feature_count_a": 65, "feature_count_b": 65}
    # No trading simulation is claimed anywhere.
    assert snap_eval["results"]["backtest"]["status"] == "NOT_RUN"


def test_bootstraps_predeclared_parameters_are_pinned() -> None:
    _, snap_eval, _, config = evaluation_layers()
    ci = snap_eval["results"]["uncertainty_interval"]
    assert ci["method"] == "moving_block_bootstrap"
    assert ci["block_weeks"] == 4  # frozen protocol block definition
    assert ci["level"] == 0.95
    assert config["n_boot"] == 2000          # hypothesis/primitive n_boot
    assert config["seeds"] == [42, 43, 44]   # predeclared seed set
    assert config["estimator_a"] == "LogisticRegression"
    assert config["estimator_b"] == "LightGBM"
    # The 95% CI answers a different question than any campaign-wide
    # multiplicity adjustment: pin that the artifact records no adjusted
    # p-value and that a campaign-5 multiplicity record is absent.
    ledger = WORKSPACE / "autonomous_agent" / "state" / "campaign_end_multiplicity.jsonl"
    rows = [json.loads(line) for line in
            ledger.read_text(encoding="utf-8").splitlines() if line.strip()] \
        if ledger.is_file() else []
    assert not any(str(r.get("campaign_id", "")).startswith("campaign-5")
                   for r in rows), \
        "era-pinned: C5 multiplicity record must not exist yet"


def test_audited_code_is_byte_identical_to_runner_and_snapshot() -> None:
    """The CI/method audit (paired rows, circular moving blocks, seeded,
    percentile CI) applies to exactly the code that ran: the version snapshot
    and the runner workspace must agree with each other, and the study file
    must agree everywhere.

    The LIVE tree harness is pinned separately below: it advanced to
    harness v1.3.0 (owner A3 authorization, 2026-10-25, error-clustering
    support) after V2.0.74 was audited under v1.1.0, so live-vs-artifact
    byte identity is no longer expected and must not be silently restored."""
    sha = lambda p: (WORKSPACE / p).read_bytes()  # noqa: E731
    harness = "autonomous_agent/recipe_harness.py"
    study = "study_files/backend/demand_zone_study_v1.py"
    snap_prefix = "autonomous_agent/candidates/exp-proposal-a987db219da2/workspace"
    # The audited artifact chain (what actually ran) is untouched.
    assert bytes(sha(f"{snap_prefix}/{harness}")) == \
        bytes(sha(f"versions/V2.0.74/code/{harness}"))
    assert bytes(sha(study)) == bytes(sha(f"{snap_prefix}/{study}"))
    assert bytes(sha(study)) == bytes(sha(f"versions/V2.0.74/code/{study}"))


def test_live_harness_is_authorized_v130_not_the_v110_artifact() -> None:
    """Era-pin for the post-A3 live tree: the live harness is the v1.3.0
    extension (owner A3 authorization, 2026-10-25; see
    'MAIN AUDITS AND REFLECTIONS/C5_ERROR_CLUSTER_AUTHORIZATION_SUMMARY'
    '_2026_10_25.md') and deliberately differs from the frozen v1.1.0
    artifact that V2.0.74 ran under. Pins the live digest prefix and the
    version markers so further live edits still fail loudly here.

    2026-10-25 defect-fix re-pin (same A3 countersign scope): the pooled
    OOF frame now carries the predeclared axis mask columns
    (_cluster_axis_columns fix); without them the error-cluster collector
    raised on its own frozen masks and every diagnostic exited 1 before
    evaluation.json existed. No definition, mask, threshold, gate, or
    multiplicity rule changed."""
    live = (WORKSPACE / "autonomous_agent" / "recipe_harness.py").read_bytes()
    import hashlib
    assert hashlib.sha256(live).hexdigest().startswith(
        "f724c33081d706e9")  # live v1.3.0 harness (post-A3, 2026-10-25 OOF-mask-column fix)
    assert b'HARNESS_VERSION_1_3_0 = "1.3.0"' in live
    assert b"owner A3 authorization, 2026-10-25" in live
    snap = (WORKSPACE / "autonomous_agent" / "candidates"
            / "exp-proposal-a987db219da2" / "workspace"
            / "autonomous_agent" / "recipe_harness.py").read_bytes()
    assert snap != live  # artifact stays the frozen v1.1.0 bytes
    assert b'HARNESS_VERSION_1_3_0' not in snap


def test_holdout_never_touched_and_no_prospective_use() -> None:
    _, snap_eval, _, _ = evaluation_layers()
    version = _load(VERSION_DIR / "version.json")
    assert snap_eval["holdout_touched"] is False
    assert version["holdout_touched"] is False
    assert version["baseline_id"] == "BASELINE_RECONSTRUCTED_2026_10"
    assert version["parent_champion"] == "V2.0.73"
    # Runtime ledger facts: this is the campaign-5 complexity_premium member.
    assert version["experiment_id"] == LEADER


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
