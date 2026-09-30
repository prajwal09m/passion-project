from __future__ import annotations

"""Read-only internal-consistency audit of the immutable v1.0.1 result archive.

This script reads the saved event table, saved OOF probabilities, run manifest,
source snapshot CSVs, and model files. It does not regenerate features/events,
fit models, or create prospective artifacts. Passing integrity and point-metric
checks establish internal consistency of retained outputs only; they do not
verify the missing historical source implementation or feature parity. Bootstrap
point estimates are checked separately from interval bounds because the current
reconstruction does not reproduce the archive-reported interval bounds.
"""

import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = ROOT / "outputs" / "study_v1" / "development"
MODEL_DIR = ROOT / "outputs" / "study_v1" / "models"
DATA_DIR = ROOT / "outputs" / "v2" / "_ohlcv"
MANIFEST_PATH = ARCHIVE_DIR / "run_manifest.json"
EVENT_TABLE_PATH = ARCHIVE_DIR / "event_table.csv"
OOF_PATH = ARCHIVE_DIR / "oof_predictions.csv"
REPORT_PATH = ARCHIVE_DIR / "development_report.md"
BASELINE_CODE_SHA256 = "29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b"
BASELINE_PROTOCOL_SHA256 = "486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07"
ESTIMATORS = ("LogisticRegression", "LightGBM")
ARMS = "ABCD"
TOLERANCE = 1e-10


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _assert_hash(path: Path, expected: str, checks: dict[str, Any]) -> None:
    actual = sha256_file(path)
    checks[str(path.relative_to(ROOT))] = {
        "sha256": actual,
        "expected_sha256": expected,
        "matches_manifest": actual == expected,
    }


def summarize_predictions(frame: pd.DataFrame, score_col: str) -> dict[str, Any]:
    labels = frame.label.astype(int).to_numpy()
    scores = pd.to_numeric(frame[score_col], errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(labels).all() or not np.isfinite(scores).all():
        raise AssertionError(f"Non-finite label or score in {score_col}")
    auc = float(roc_auc_score(labels, scores)) if len(np.unique(labels)) == 2 else None
    ap = float(average_precision_score(labels, scores)) if len(np.unique(labels)) == 2 else None
    data = frame[["date", "label", score_col]].copy()
    data["date"] = pd.to_datetime(data.date)
    daily_auc: list[float] = []
    top5: list[float] = []
    prevalences: list[float] = []
    for _, group in data.groupby("date", sort=True):
        if group.label.nunique() > 1:
            daily_auc.append(float(roc_auc_score(group.label.astype(int), group[score_col])))
        count = max(1, int(math.ceil(len(group) * 0.05)))
        top = group.nlargest(count, score_col)
        top5.append(float(top.label.mean()))
        prevalences.append(float(group.label.mean()))
    top5_mean = float(np.mean(top5)) if top5 else None
    prevalence_mean = float(np.mean(prevalences)) if prevalences else None
    return {
        "events": int(len(data)),
        "positive_rate": float(np.mean(labels)) if len(labels) else None,
        "pooled_auc": auc,
        "average_precision": ap,
        "daily_auc_mean_two_class_dates": float(np.mean(daily_auc)) if daily_auc else None,
        "daily_auc_eligible_dates": len(daily_auc),
        "top5pct_precision_mean_per_date": top5_mean,
        "same_date_base_rate_mean": prevalence_mean,
        "top5pct_lift_mean_per_date": top5_mean - prevalence_mean if top5_mean is not None and prevalence_mean is not None else None,
    }


def block_bootstrap_delta(
    frame: pd.DataFrame,
    score_a: str,
    score_b: str,
    *,
    n_boot: int = 1000,
    block_weeks: int = 4,
    seed: int = 42,
) -> dict[str, Any]:
    data = frame[["date", "label", score_a, score_b]].copy()
    if data[["label", score_a, score_b]].isna().any().any():
        raise AssertionError(f"Missing paired data for {score_a} and {score_b}")
    data["date"] = pd.to_datetime(data.date)
    labels = data.label.astype(int)
    if labels.nunique() < 2:
        raise AssertionError("AUC contrast requires both labels")
    base = roc_auc_score(labels, data[score_a]) - roc_auc_score(labels, data[score_b])
    weeks = data.date.dt.to_period("W-SUN")
    week_values = sorted(weeks.unique())
    if len(week_values) < block_weeks:
        raise AssertionError("Insufficient weeks for the specified bootstrap")
    rng = np.random.default_rng(seed)
    deltas: list[float] = []
    for _ in range(n_boot):
        indices: list[int] = []
        while len(indices) < len(data):
            start = int(rng.integers(0, len(week_values)))
            block = [week_values[(start + offset) % len(week_values)] for offset in range(block_weeks)]
            for week in block:
                indices.extend(np.flatnonzero((weeks == week).to_numpy()).tolist())
        sample = data.iloc[indices[: len(data)]]
        if sample.label.nunique() == 2:
            deltas.append(float(roc_auc_score(sample.label.astype(int), sample[score_a]) - roc_auc_score(sample.label.astype(int), sample[score_b])))
    if not deltas:
        raise AssertionError("No valid bootstrap resamples")
    low, high = np.quantile(deltas, [0.025, 0.975])
    return {
        "delta_auc": float(base),
        "ci_95": [float(low), float(high)],
        "n_boot_valid": len(deltas),
        "block_weeks": block_weeks,
        "seed": seed,
    }


def _assert_close(actual: Any, expected: Any, key: str, differences: dict[str, Any]) -> None:
    if actual is None or expected is None:
        equal = actual is None and expected is None
    elif isinstance(actual, (int, np.integer)) and isinstance(expected, (int, np.integer)):
        equal = int(actual) == int(expected)
    else:
        equal = bool(np.isclose(float(actual), float(expected), rtol=TOLERANCE, atol=TOLERANCE, equal_nan=True))
    if not equal:
        differences[key] = {"recomputed_from_saved_oof": actual, "manifest": expected}


def _report_table_values(report: str) -> dict[str, dict[str, float | int]]:
    values: dict[str, dict[str, float | int]] = {}
    for line in report.splitlines():
        if not line.startswith("| LogisticRegression | ") and not line.startswith("| LightGBM | "):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 9:
            continue
        estimator, arm = cells[0].replace(" ", ""), cells[1]
        daily = re.match(r"([0-9.]+)", cells[6])
        if not daily:
            continue
        values[f"{estimator}_{arm}"] = {
            "events": int(cells[2].replace(",", "")),
            "positive_rate": float(cells[3]),
            "pooled_auc": float(cells[4]),
            "average_precision": float(cells[5]),
            "daily_auc_mean_two_class_dates": float(daily.group(1)),
            "top5pct_precision_mean_per_date": float(cells[7]),
            "same_date_base_rate_mean": float(cells[8]),
        }
    return values


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("protocol_version") != "1.0.1":
        raise AssertionError("The immutable baseline manifest is not the expected v1.0.1 archive")
    if manifest.get("code_sha256") != BASELINE_CODE_SHA256 or manifest.get("protocol_sha256") != BASELINE_PROTOCOL_SHA256:
        raise AssertionError("The baseline manifest identity differs from the recorded immutable v1.0.1 hashes")

    hash_checks: dict[str, Any] = {}
    for name, expected in manifest["artifact_sha256"].items():
        _assert_hash(ARCHIVE_DIR / name, expected, hash_checks)
    for name, expected in manifest["model_artifacts_sha256"].items():
        _assert_hash(MODEL_DIR / name, expected, hash_checks)
    source_checks: dict[str, bool] = {}
    for symbol, expected in manifest["source_data_sha256"].items():
        path = DATA_DIR / f"{symbol}.csv"
        source_checks[symbol] = path.exists() and sha256_file(path) == expected

    # Load archived results only; do not regenerate candidate events or fit estimators.
    oof = pd.read_csv(OOF_PATH)
    event_columns = ["ticker", "date", "event_id", "label", "hold1_ret", "entry_date", "exit_date"]
    events = pd.read_csv(EVENT_TABLE_PATH, usecols=event_columns)
    score_columns = [f"{estimator}_{arm}" for estimator in ESTIMATORS for arm in ARMS]
    expected_count = int(manifest["event_generation"]["oof_events"])
    if len(oof) != expected_count or not oof.event_id.is_unique or oof.duplicated(["ticker", "date"]).any():
        raise AssertionError("Saved OOF row count/identity does not match the archive manifest")
    if not set(score_columns).issubset(oof.columns):
        raise AssertionError("Saved OOF file is missing one or more model scores")
    scores = oof[score_columns].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(scores).all() or oof[["date", "label", "hold1_ret", "entry_date", "exit_date", "fold"]].isna().any().any():
        raise AssertionError("Saved OOF file contains a missing/non-finite score or required field")

    oof["date"] = pd.to_datetime(oof.date)
    oof["entry_date"] = pd.to_datetime(oof.entry_date)
    oof["exit_date"] = pd.to_datetime(oof.exit_date)
    if (oof.date >= pd.Timestamp("2026-01-01")).any():
        raise AssertionError("Saved OOF contains a signal on/after the protocol's exclusive cutoff")
    label_from_return = (pd.to_numeric(oof.hold1_ret).to_numpy(dtype=float) >= 0.02).astype(int)
    if not np.array_equal(oof.label.astype(int).to_numpy(), label_from_return):
        raise AssertionError("Saved OOF labels do not match the saved inclusive 2% return threshold")
    if not (oof.entry_date > oof.date).all() or not (oof.exit_date > oof.entry_date).all():
        raise AssertionError("Saved OOF label entry/exit dates are not strictly forward")
    for fold, group in oof.groupby("fold", sort=True):
        if not group.date.dt.year.astype(str).eq(str(fold)).all():
            raise AssertionError(f"OOF fold {fold} contains signal dates from another year")

    # Verify all scored OOF event/label/outcome keys are present and identical in the event table.
    for frame in (oof, events):
        frame["date_key"] = pd.to_datetime(frame.date).dt.strftime("%Y-%m-%d")
        frame["entry_key"] = pd.to_datetime(frame.entry_date).dt.strftime("%Y-%m-%d")
        frame["exit_key"] = pd.to_datetime(frame.exit_date).dt.strftime("%Y-%m-%d")
    oof_keys = oof.set_index("event_id")[["ticker", "date_key", "label", "hold1_ret", "entry_key", "exit_key"]].sort_index()
    event_keys = events.set_index("event_id")[["ticker", "date_key", "label", "hold1_ret", "entry_key", "exit_key"]].sort_index()
    if len(events) != int(manifest["event_generation"]["candidate_events"]):
        raise AssertionError("Saved event-table row count does not match the archive manifest")
    if not events.event_id.is_unique:
        raise AssertionError("Saved event-table event IDs are duplicated")
    missing = oof_keys.index.difference(event_keys.index)
    if len(missing):
        raise AssertionError(f"{len(missing)} OOF events are absent from the archived event table")
    paired = oof_keys.join(event_keys.add_suffix("_archive"), how="left")
    row_mismatches: dict[str, int] = {}
    for field in ("ticker", "date_key", "label", "entry_key", "exit_key"):
        row_mismatches[field] = int(paired[field].fillna("").astype(str).ne(paired[f"{field}_archive"].fillna("").astype(str)).sum())
    left_returns = pd.to_numeric(paired.hold1_ret, errors="coerce").to_numpy(dtype=float)
    right_returns = pd.to_numeric(paired.hold1_ret_archive, errors="coerce").to_numpy(dtype=float)
    row_mismatches["hold1_ret"] = int((~np.isclose(left_returns, right_returns, rtol=TOLERANCE, atol=TOLERANCE, equal_nan=True)).sum())
    if any(row_mismatches.values()):
        raise AssertionError(f"OOF/event-table row mismatches: {row_mismatches}")

    pooled_metrics: dict[str, Any] = {}
    pooled_differences: dict[str, Any] = {}
    for score_column in score_columns:
        got = summarize_predictions(oof, score_column)
        pooled_metrics[score_column] = got
        expected = manifest["pooled_oof_metrics"][score_column]
        for field, value in got.items():
            _assert_close(value, expected.get(field), f"{score_column}.{field}", pooled_differences)

    fold_metrics: dict[str, Any] = {}
    fold_differences: dict[str, Any] = {}
    for fold, group in oof.groupby("fold", sort=True):
        fold_key = str(fold)
        saved_fold = next(item for item in manifest["chronological_development_folds"] if item["fold"] == fold_key)
        fold_metrics[fold_key] = {}
        for score_column in score_columns:
            got = summarize_predictions(group, score_column)
            fold_metrics[fold_key][score_column] = got
            expected = saved_fold["metrics"][score_column]
            for field, value in got.items():
                _assert_close(value, expected.get(field), f"{fold_key}.{score_column}.{field}", fold_differences)

    pairs = {
        "primary_LightGBM_A_minus_LogisticRegression_A": ("LightGBM_A", "LogisticRegression_A"),
        "primary_LightGBM_C_minus_LightGBM_B": ("LightGBM_C", "LightGBM_B"),
        "secondary_LogisticRegression_B_minus_A": ("LogisticRegression_B", "LogisticRegression_A"),
        "secondary_LightGBM_B_minus_A": ("LightGBM_B", "LightGBM_A"),
        "secondary_LogisticRegression_C_minus_B": ("LogisticRegression_C", "LogisticRegression_B"),
        "secondary_LogisticRegression_D_minus_C": ("LogisticRegression_D", "LogisticRegression_C"),
        "secondary_LightGBM_D_minus_C": ("LightGBM_D", "LightGBM_C"),
    }
    recompute_bootstrap = os.environ.get("AUDIT_RECOMPUTE_BOOTSTRAP") == "1"
    contrasts: dict[str, Any] = {}
    contrast_point_differences: dict[str, Any] = {}
    interval_differences: dict[str, Any] = {}
    for name, (score_a, score_b) in pairs.items():
        expected = manifest["paired_week_block_bootstrap_1000"][name]
        point_delta = float(roc_auc_score(oof.label.astype(int), oof[score_a]) - roc_auc_score(oof.label.astype(int), oof[score_b]))
        got: dict[str, Any] = {
            "delta_auc_from_saved_oof_scores": point_delta,
            "archive_reported_ci_95": expected["ci_95"],
            "archive_reported_valid_bootstrap_resamples": expected["valid_bootstrap_resamples"],
            "interval_recalculation_performed": recompute_bootstrap,
        }
        _assert_close(point_delta, expected["delta_auc"], f"{name}.delta_auc", contrast_point_differences)
        if recompute_bootstrap:
            recalculated = block_bootstrap_delta(oof, score_a, score_b, n_boot=1000, block_weeks=4, seed=42)
            got["current_helper_ci_95"] = recalculated["ci_95"]
            got["current_helper_valid_bootstrap_resamples"] = recalculated["n_boot_valid"]
            _assert_close(recalculated["n_boot_valid"], expected["valid_bootstrap_resamples"], f"{name}.valid_bootstrap_resamples", contrast_point_differences)
            _assert_close(recalculated["ci_95"][0], expected["ci_95"][0], f"{name}.ci_95_low", interval_differences)
            _assert_close(recalculated["ci_95"][1], expected["ci_95"][1], f"{name}.ci_95_high", interval_differences)
            got["recomputed_ci_matches_archive"] = not any(key.startswith(f"{name}.") for key in interval_differences)
        contrasts[name] = got

    report = REPORT_PATH.read_text(encoding="utf-8")
    report_values = _report_table_values(report)
    report_differences: dict[str, Any] = {}
    for score_column, expected in pooled_metrics.items():
        published = report_values.get(score_column)
        if published is None:
            report_differences[score_column] = "missing report table row"
            continue
        for field, shown in published.items():
            if round(float(expected[field]), 4) != round(float(shown), 4):
                report_differences[f"{score_column}.{field}"] = {"saved_oof": expected[field], "report": shown}

    protocol_path = ROOT / "MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json"
    code_path = ROOT / "backend" / "demand_zone_study_v1.py"
    result = {
        "scope": "read-only calculations from saved v1.0.1 archive outputs; no event replay or model fitting",
        "archive_protocol_version": manifest["protocol_version"],
        "archive_code_sha256": manifest["code_sha256"],
        "archive_protocol_sha256": manifest["protocol_sha256"],
        "current_protocol_sha256": sha256_file(protocol_path),
        "current_reconstruction_sha256": sha256_file(code_path),
        "current_files_match_v1_0_1_code_protocol_hashes": {
            "code": sha256_file(code_path) == manifest["code_sha256"],
            "protocol": sha256_file(protocol_path) == manifest["protocol_sha256"],
        },
        "events": {
            "event_table_rows": len(events),
            "oof_rows": len(oof),
            "unique_oof_event_ids": int(oof.event_id.nunique()),
            "fold_counts": {str(key): int(value) for key, value in oof.groupby("fold").size().items()},
            "signal_date_min": str(oof.date.min().date()),
            "signal_date_max": str(oof.date.max().date()),
            "signal_cutoff_exclusive": "2026-01-01",
            "all_oof_keys_match_event_table": not any(row_mismatches.values()),
            "oof_event_table_row_mismatches": row_mismatches,
            "all_oof_scores_finite": bool(np.isfinite(scores).all()),
        },
        "archive_artifact_hashes": hash_checks,
        "source_snapshot_files_checked": len(source_checks),
        "source_snapshot_hash_mismatches": sorted(symbol for symbol, matches in source_checks.items() if not matches),
        "pooled_metrics_match_manifest": not pooled_differences,
        "pooled_metric_differences": pooled_differences,
        "fold_metrics_match_manifest": not fold_differences,
        "fold_metric_differences": fold_differences,
        "paired_bootstrap_point_estimates_match_manifest": not contrast_point_differences,
        "paired_bootstrap_point_differences": contrast_point_differences,
        "current_helper_bootstrap_interval_recalculation_performed": recompute_bootstrap,
        "archived_paired_bootstrap_intervals_reproduced_by_current_helper": (not interval_differences) if recompute_bootstrap else None,
        "paired_bootstrap_interval_differences": interval_differences,
        "archived_interval_status": (
            "recalculated in this run; compare differences above"
            if recompute_bootstrap
            else "kept as manifest-reported values; prior full check did not reproduce any of seven interval bounds; not rerun in this closeout"
        ),
        "report_table_matches_saved_oof_to_four_decimals": not report_differences,
        "report_table_differences": report_differences,
        "recomputed_pooled_metrics": pooled_metrics,
        "recomputed_primary_contrasts": {key: value for key, value in contrasts.items() if key.startswith("primary_")},
    }
    result["archive_integrity_and_saved_point_metrics_verified"] = bool(
        all(item["matches_manifest"] for item in hash_checks.values())
        and not result["source_snapshot_hash_mismatches"]
        and not any(row_mismatches.values())
        and not pooled_differences
        and not fold_differences
        and not report_differences
        and not contrast_point_differences
    )
    result["archive_ci_bounds_reproduced"] = (not interval_differences) if recompute_bootstrap else None
    print(json.dumps(result, indent=2, default=str))
    if not result["archive_integrity_and_saved_point_metrics_verified"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
