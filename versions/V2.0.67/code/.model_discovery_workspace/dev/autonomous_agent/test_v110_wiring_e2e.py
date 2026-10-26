"""End-to-end acceptance tests for the v1.1.0 measurement wiring (2026-10-16).

Owner-required acceptance evidence for the Campaign 4 measurement-wiring
remediation (``C4_MEASUREMENT_WIRING_FINDING_OWNER_DECISION_RECORD_2026_10_16.md``
section 2): measurements must be produced by ACTUAL EXECUTION through the
production entry point (``python -m autonomous_agent.experiments.run_experiment``,
byte-identical to the adapter's command), reach the persisted per-member
records with correct family/association/provenance, and feed the intended
multiplicity procedure (``week_level_signflip_holm`` + Holm) with results
independently verified against known test cases.

Isolation contract: every execution runs in a temporary synthetic root
(synthetic frozen-study module, synthetic event table, synthetic OHLCV
cache).  No real campaign is launched, no campaign execution budget is
consumed, no persistent campaign state is written, the sealed holdout is
never present in any fixture, and module-level guards prove the
historical Campaign 4 artifacts are bit-identical before and after the
whole suite.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]


def _verify_staged_fixture(relative: str) -> Path:
    """Refuse unmanifested or drifted source snapshots in this dev tree."""
    manifest_path = REPO / "FIXTURE_PROVENANCE.json"
    if not manifest_path.is_file():
        raise RuntimeError("missing dev/FIXTURE_PROVENANCE.json; stage fixtures first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record = next((row for row in manifest.get("files", [])
                   if row.get("path") == relative), None)
    path = REPO / relative
    if record is None or not path.is_file():
        raise RuntimeError(f"authoritative development fixture is absent/unlisted: {relative}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != record.get("sha256"):
        raise RuntimeError(f"development fixture hash mismatch for {relative}")
    return path


# The consumption module and independent reference implementation are
# staged from explicit retained sources into this dev-only fixture tree by
# restore_dev_test_fixtures.py. Do not fall back to importing the source
# checkout: a missing fixture should fail collection clearly.
_STAT_VALIDATION_FIXTURES = REPO / "stat_validation_h10"
_verify_staged_fixture("stat_validation_h10/family_records.py")
_verify_staged_fixture("stat_validation_h10/campaign_end_finalization.py")
_verify_staged_fixture("stat_validation_h10/simh10.py")
sys.path.insert(0, str(_STAT_VALIDATION_FIXTURES))
import family_records as fr                                    # noqa: E402
from autonomous_agent import hardening                         # noqa: E402
from autonomous_agent import recipe_harness as rh            # noqa: E402
from autonomous_agent import three_valued as tv              # noqa: E402
from autonomous_agent.proposal_layer import signflip         # noqa: E402
from autonomous_agent.proposal_layer import compiler         # noqa: E402
from autonomous_agent.proposal_layer.primitives import get as get_primitive  # noqa: E402
from autonomous_agent import spec_recipes                    # noqa: E402
import campaign_end_finalization as cef                       # noqa: E402
from autonomous_agent.core import write_json_atomic           # noqa: E402
from autonomous_agent.experiment_adapter import (             # noqa: E402
    ExperimentAdapter, ExperimentResult, ExperimentSpec)

# ---------------------------------------------------------------------------
# Historical-artifact guards: bit-identical before and after the whole suite.
# ---------------------------------------------------------------------------
_FIXTURE_MANIFEST = REPO / "FIXTURE_PROVENANCE.json"


_GUARDED_FILES = (
    REPO / "autonomous_agent" / "state" / "campaign_end_multiplicity.jsonl",
    REPO / "autonomous_agent" / "MAIN AUDITS AND REFLECTIONS"
    / "CAMPAIGN_4_FINAL_ARCHIVE_2026-10-16" / "SHA256SUMS.txt",
    REPO / "autonomous_agent" / "MAIN AUDITS AND REFLECTIONS"
    / "C4_MEASUREMENT_WIRING_FINDING_OWNER_DECISION_RECORD_2026_10_16.md",
    REPO / "stat_validation_h10" / "launch_gates.json",
    REPO / "stat_validation_h10" / "family_records.py",
    REPO / "stat_validation_h10" / "campaign_end_finalization.py",
)
_HOLDOUT = REPO / "study_files" / "outputs" / "study_v1" / "prospective"
_before: dict[str, str] = {}


def _digest(path: Path) -> str:
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if path.is_dir():
        rows = sorted(f"{p.relative_to(path).as_posix()}:{p.stat().st_size}"
                      for p in path.rglob("*") if p.is_file())
        return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()
    return "ABSENT"


def setUpModule() -> None:
    if not _FIXTURE_MANIFEST.is_file():
        raise RuntimeError("missing dev/FIXTURE_PROVENANCE.json; stage fixtures first")
    for path in _GUARDED_FILES:
        _before[str(path)] = _digest(path)
    _before["holdout"] = _digest(_HOLDOUT)


def tearDownModule() -> None:
    for path in _GUARDED_FILES:
        assert _digest(path) == _before[str(path)], \
            f"HISTORICAL ARTIFACT MUTATED: {path}"
    assert _digest(_HOLDOUT) == _before["holdout"], "HOLDOUT STATE CHANGED"


# ---------------------------------------------------------------------------
# Synthetic frozen study (fixture module, same contracts as the real one).
# ---------------------------------------------------------------------------
SYNTHETIC_STUDY = '''\
"""Synthetic frozen study for v1.1.0 wiring E2E fixtures (fixture only).

Mirrors the real study module's reviewed contracts: FEATURE_ARMS, purged
chronological make_folds, deterministic fit/predict pipelines, the exact
moving-block bootstrap, and the OHLCV reader.  No real data, no network.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "outputs" / "v2" / "_ohlcv"

FEATURE_ARMS = {
    "A": ["f1"],
    "B": ["f1", "f2"],
    "C": ["f1", "f2", "f3"],
    "D": ["f1", "f2", "f3", "f4"],
}


def make_folds(frame, years=(2023, 2024, 2025)):
    dates, exits = pd.to_datetime(frame.date), pd.to_datetime(frame.exit_date)
    folds = []
    expected = [str(year) for year in years]
    for year in map(int, expected):
        start, end = pd.Timestamp(f"{year}-01-01"), pd.Timestamp(f"{year + 1}-01-01")
        train = (dates < start) & (exits < start)
        valid = (dates >= start) & (dates < end)
        if train.any() and valid.any():
            folds.append({"name": str(year), "start": start, "end": end,
                          "train_mask": train.to_numpy(), "valid_mask": valid.to_numpy()})
    if [f["name"] for f in folds] != expected:
        raise RuntimeError(f"Expected chronological folds {expected}, got {[f['name'] for f in folds]}")
    return folds


def fit_pipeline(estimator, features, rows, labels):
    x = rows[features].to_numpy(dtype=float)
    labels = np.asarray(labels).astype(int)
    if len(set(labels.tolist())) < 2:
        raise RuntimeError("fixture fit needs both label classes")
    w = x[labels == 1].mean(axis=0) - x[labels == 0].mean(axis=0)
    return {"w": np.asarray(w, dtype=float), "estimator": estimator,
            "features": list(features)}


def predict_pipeline(pipeline, rows):
    x = rows[pipeline["features"]].to_numpy(dtype=float)
    scores = x @ pipeline["w"]
    if pipeline["estimator"] == "LogisticRegression":
        scores = scores + 0.04 * np.sin(np.arange(len(scores)))
    return scores


def block_bootstrap_delta(frame, score_a, score_b, *, n_boot=1000, block_weeks=4, seed=42):
    valid = frame[[score_a, score_b, "label"]].notna().all(axis=1)
    data = frame.loc[valid].copy()
    if data.label.nunique() < 2:
        raise ValueError("AUC comparison requires two label classes")
    base = roc_auc_score(data.label, data[score_a]) - roc_auc_score(data.label, data[score_b])
    weeks = pd.to_datetime(data.date).dt.to_period("W-SUN")
    week_values = sorted(weeks.unique())
    if len(week_values) < block_weeks:
        raise ValueError("Insufficient calendar weeks for moving-block bootstrap")
    rng = np.random.default_rng(seed)
    deltas = []
    for _ in range(n_boot):
        indices = []
        while len(indices) < len(data):
            start = int(rng.integers(0, len(week_values)))
            block = [week_values[(start + offset) % len(week_values)] for offset in range(block_weeks)]
            for week in block:
                indices.extend(np.flatnonzero((weeks == week).to_numpy()).tolist())
        sample = data.iloc[indices[:len(data)]]
        if sample.label.nunique() == 2:
            deltas.append(roc_auc_score(sample.label, sample[score_a]) - roc_auc_score(sample.label, sample[score_b]))
    if not deltas:
        raise RuntimeError("No valid moving-block bootstrap resamples")
    low, high = np.quantile(deltas, [0.025, 0.975])
    return {"score_a": score_a, "score_b": score_b, "delta_auc": float(base),
            "ci_95": [float(low), float(high)], "n_boot_valid": len(deltas),
            "block_weeks": block_weeks, "seed": seed}


def read_ohlcv(symbol, data_dir=DATA_DIR):
    path = data_dir / f"{symbol.replace('^', 'X')}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing local OHLCV file: {path}")
    frame = pd.read_csv(path)
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce").dt.tz_localize(None)
    frame = frame.dropna(subset=["Date"]).drop_duplicates("Date", keep="last").sort_values("Date").set_index("Date")
    required = {"Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing OHLCV columns in {path}")
    for column in required:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame
'''

FIXTURE_SMOKE_TEST = '''\
import unittest


class FixtureSmoke(unittest.TestCase):
    def test_ok(self):
        self.assertTrue(True)
'''

TICKERS = ("AAA", "BBB", "CCC")


def _build_fixture(tmp: Path, *, thin_below_cell: bool = False,
                   drop_regime_column: bool = False,
                   starve_below_cell: bool = False,
                   drop_spy: bool = False) -> dict:
    """Build a complete synthetic workspace root; returns fixture facts."""
    rng = np.random.default_rng(20261016)
    sessions = pd.date_range("2021-01-06", "2025-11-26", freq="W-WED")
    n_sessions = len(sessions)

    # --- OHLCV cache: per-ticker open chains with prescribed odd-step returns
    opens: dict[str, np.ndarray] = {}
    returns_by_ticker: dict[str, dict[int, float]] = {}
    for t, ticker in enumerate(TICKERS):
        base = 50.0 + 10.0 * t
        r = 0.001 * rng.standard_normal(n_sessions)
        ret_map = {}
        # One event per session per ticker: signal j, entry j+1, exit j+2;
        # the 1-session hold return is the open-to-open step j+1 -> j+2.
        for j in range(0, n_sessions - 4):
            u = float(rng.standard_normal())
            hold = 0.02 + 0.04 * u
            r[j + 2] = hold           # open step entry -> exit
            ret_map[j] = u
        series = np.empty(n_sessions)
        series[0] = base
        for j in range(1, n_sessions):
            series[j] = series[j - 1] * (1.0 + r[j])
        opens[ticker] = series
        returns_by_ticker[ticker] = ret_map
    spy = 100.0 * np.cumprod(1.0 + 0.002 * rng.standard_normal(n_sessions) + 0.0005)

    ohlcv_dir = tmp / "study_files" / "outputs" / "v2" / "_ohlcv"
    ohlcv_dir.mkdir(parents=True)
    for ticker in list(TICKERS) + ([] if drop_spy else ["SPY"]):
        values = spy if ticker == "SPY" else opens[ticker]
        frame = pd.DataFrame({"Date": sessions.strftime("%Y-%m-%d"),
                              "Open": values, "High": values * 1.01,
                              "Low": values * 0.99, "Close": values,
                              "Volume": np.full(n_sessions, 1_000_000)})
        frame.to_csv(ohlcv_dir / f"{ticker}.csv", index=False)

    # --- event table derived from the same chains (anchor-safe by construction)
    rows = []
    for t, ticker in enumerate(TICKERS):
        for j in sorted(returns_by_ticker[ticker]):
            u = returns_by_ticker[ticker][j]
            hold = 0.02 + 0.04 * u
            entry_open = opens[ticker][j + 1]
            exit_open = opens[ticker][j + 2]
            computed = exit_open / entry_open - 1.0
            # predeclared binary regime feature: SPY above its trailing
            # 60-session median (fixture analogue of the frozen SMA-200
            # regime split; data-derived, deterministic, both cells live)
            spy_above = 1 if spy[j] >= float(
                np.median(spy[max(0, j - 59):j + 1])) else 0
            rows.append({
                "date": str(sessions[j].date()),
                "ticker": ticker,
                "event_id": f"{ticker}-{j}",
                "entry_date": str(sessions[j + 1].date()),
                "exit_date": str(sessions[j + 2].date()),
                "entry_open": round(float(entry_open), 10),
                "exit_open": round(float(exit_open), 10),
                "hold1_ret": round(float(computed), 10),
                "label": 1 if computed >= 0.02 else 0,
                "label_valid": True,
                "spy_above_sma200": spy_above,
                "f1": float(u) + 0.3 * float(rng.standard_normal()),
                "f2": float(rng.standard_normal()),
                "f3": float(rng.standard_normal()),
                "f4": float(rng.standard_normal()),
            })
    if thin_below_cell:
        # Force a degenerate below-SMA cell: only two rows, single class.
        for index, row in enumerate(rows):
            row["spy_above_sma200"] = 1
        rows[-2]["spy_above_sma200"] = 0
        rows[-1]["spy_above_sma200"] = 0
        rows[-2]["label"] = 1
        rows[-1]["label"] = 1
    table = pd.DataFrame(rows).sort_values(["date", "ticker"]).reset_index(drop=True)
    if starve_below_cell:
        # Squeeze the below-cell rows into the final three sessions
        # (three W-SUN calendar weeks): the cell keeps both label
        # classes, rows, and events (never degenerate-unavailable), but
        # has fewer weeks than the frozen block bootstrap's minimum
        # (block_weeks = 4), so the member measurement must fail the
        # run closed instead of writing any evaluation output.
        starved = table["date"].isin(sorted(table["date"].unique())[-3:])
        table["spy_above_sma200"] = 1
        table.loc[starved, "spy_above_sma200"] = 0
        for index, position in enumerate(table.index[starved]):
            table.at[position, "label"] = index % 2
    dev = tmp / "study_files" / "outputs" / "study_v1" / "development"
    dev.mkdir(parents=True)
    table.to_csv(dev / "event_table.csv", index=False)

    # --- frozen-study module + unit-test role target
    backend = tmp / "study_files" / "backend"
    backend.mkdir(parents=True)
    (backend / "demand_zone_study_v1.py").write_text(SYNTHETIC_STUDY, encoding="utf-8")
    (backend / "tests").mkdir()
    (backend / "tests" / "test_fixture_smoke.py").write_text(
        FIXTURE_SMOKE_TEST, encoding="utf-8")

    # --- workspace package: byte-identical harness copies + real shim/config
    package = tmp / "autonomous_agent"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    for name in ("recipe_harness.py", "three_valued.py"):
        shutil.copyfile(REPO / "autonomous_agent" / name, package / name)
    experiments = package / "experiments"
    experiments.mkdir()
    (experiments / "__init__.py").write_text(
        spec_recipes.INIT_CONTENT, encoding="utf-8")
    (experiments / "run_experiment.py").write_text(
        spec_recipes.EXPERIMENT_ENTRYPOINT, encoding="utf-8")
    # The production workspace is a whole-tree copy of the live repo, so
    # the harness's consumption-side imports (multiplicity / signflip via
    # the family-block firewall stamp) resolve the same way they do in
    # production candidate workspaces.
    shutil.copytree(REPO / "autonomous_agent" / "proposal_layer",
                    package / "proposal_layer",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    return {"root": tmp, "table": table, "weeks": None,
            "drop_regime_column": drop_regime_column}


def _render_config(primitive_id: str, params: dict) -> str:
    payload = {"research_question_id": "rq-wiring-fixture",
               "hypothesis": "fixture hypothesis for the wiring acceptance run",
               "baseline_id": "BASELINE_FIXTURE"}
    config = compiler._render_v110_config(
        payload, get_primitive(primitive_id), params)
    return json.dumps(config, indent=2, sort_keys=True) + "\n"


def _run_entrypoint(tmp: Path, config_text: str,
                    *, drop_regime_column: bool = False) -> subprocess.CompletedProcess:
    experiments = tmp / "autonomous_agent" / "experiments"
    (experiments / "experiment_config.json").write_text(config_text, encoding="utf-8")
    if drop_regime_column:
        dev = tmp / "study_files" / "outputs" / "study_v1" / "development"
        table = pd.read_csv(dev / "event_table.csv").drop(
            columns=["spy_above_sma200"])
        table.to_csv(dev / "event_table.csv", index=False)
    env = {key: os.environ.get(key, "") for key in
           ("PATH", "SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP")}
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "autonomous_agent.experiments.run_experiment"],
        cwd=str(tmp), env=env, capture_output=True, text=True, timeout=600)


def _campaign_config(W: int, M: int = 1000) -> dict:
    _, draw = signflip.draw_flips(W, M, 20261016)
    return {"multiplicity_policy": {"flip_draw": draw.to_dict(),
                                    "n_flips": M}}


# ---------------------------------------------------------------------------
# F-6 fixtures: authoritative configuration/specification identity helpers.
# These build a *source of truth* (spec-style mapping whose installed
# experiment_config.json content is hashed) so the consumption cross-check
# can be exercised against an independent artifact instead of the record.
# ---------------------------------------------------------------------------
_SYNTH_CONFIG = {
    "schema_version": 1, "generator": "deterministic_compositional",
    "recipe_id": "proposal_layer", "recipe_version": "1.1.0",
    "harness_version": "1.1.0",
    "primitive_id": "complexity_reduction_check",
    "hypothesis_id": "rq", "hypothesis_text": "fixture hypothesis",
    "baseline_id": "BASELINE_FIXTURE",
    "arm_a": "B", "arm_b": "B", "estimator_a": "LogisticRegression",
    "estimator_b": "LightGBM", "seeds": [42, 43, 44], "n_boot": 1000,
    "calibration_bins": 10, "folds": [2023, 2024, 2025],
    "evaluation_criteria": {"primary_metric_min_delta": 0.0,
                            "ci_lower_min": -0.01, "min_folds": 3},
}
_SYNTH_IDENTITY = {
    "hypothesis_id": "rq", "recipe_id": "proposal_layer",
    "arm_a": "B", "arm_b": "B", "estimator_a": "LogisticRegression",
    "estimator_b": "LightGBM", "seeds": [42, 43, 44], "n_boot": 1000,
    "folds": [2023, 2024, 2025],
    "config_sha256": fr.config_identity_sha256(_SYNTH_CONFIG),
}


def _synth_spec(config: dict | None = None) -> dict:
    config = _SYNTH_CONFIG if config is None else config
    return {
        "experiment_id": "exp-synth",
        "parent_version": "V2.0.61",
        "hypothesis": "fixture hypothesis for F-6 provenance fixtures",
        "proposed_change": {"summary": "fixture only",
                             "files": [{"path": ("autonomous_agent/experiments/"
                                                  "experiment_config.json"),
                                        "content": (json.dumps(config, indent=2,
                                                                sort_keys=True)
                                                    + "\n")}]},
        "files_allowed_to_change": ["autonomous_agent/experiments"],
        "evaluation_protocol": {"acceptance_criteria":
                                 {"primary_metric_min_delta": -1.0}},
        "random_seed": 42, "resource_limits": {}, "timeout": 900.0,
        "allow_repeat": False, "baseline_id": None, "provenance": {},
    }


def _synth_authority(*experiment_ids: str, config: dict | None = None) -> dict:
    spec = _synth_spec(config)
    recorded = hardening.spec_fingerprint(spec)
    return {eid: fr.authoritative_identity(
        spec, experiment_id=eid, ledger_spec_sha256=recorded)
        for eid in experiment_ids}


def _fixture_authority(tmp: Path, experiment_id: str) -> dict:
    """Authority from the workspace's ACTUAL executed config file."""
    config_text = (tmp / "autonomous_agent" / "experiments"
                   / "experiment_config.json").read_text(encoding="utf-8")
    spec = {
        "experiment_id": experiment_id,
        "parent_version": "V2.0.61",
        "hypothesis": "fixture authority spec (F-6)",
        "proposed_change": {"summary": "fixture only",
                             "files": [{"path": ("autonomous_agent/experiments/"
                                                  "experiment_config.json"),
                                        "content": config_text}]},
        "files_allowed_to_change": ["autonomous_agent/experiments"],
        "evaluation_protocol": {}, "random_seed": 42,
        "resource_limits": {}, "timeout": 900.0, "allow_repeat": False,
        "baseline_id": None, "provenance": {},
    }
    return fr.authoritative_identity(
        spec, experiment_id=experiment_id,
        ledger_spec_sha256=hardening.spec_fingerprint(spec))


def _execute_in_fixture(case: unittest.TestCase, primitive_id: str,
                        params: dict, *, config_mutator=None, **fixture):
    """Build a fresh fixture, run the real entry point, load evaluation.

    Shared by the F-2 fail-closed negative tests; every invocation is a
    throwaway temporary root removed by test cleanup.
    """
    tmp = Path(tempfile.mkdtemp(prefix=f"f2_{primitive_id}_"))
    case.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
    _build_fixture(tmp, **fixture)
    config_text = _render_config(primitive_id, params)
    if config_mutator is not None:
        config_text = config_mutator(config_text)
    result = _run_entrypoint(tmp, config_text)
    evaluation = tmp / "outputs" / "evaluation.json"
    return (tmp, result,
            (json.loads(evaluation.read_text(encoding="utf-8"))
             if evaluation.is_file() else None))


def _write_campaign_config(state_dir: Path, *, campaign_id: str, W: int,
                           M: int = 1000, seed: int = 20261016,
                           n_boot: int = 1000,
                           flip_rows_sha256: str | None = None,
                           flip_w_override: int | None = None) -> dict:
    """Frozen-shape campaign config + pin sidecar for a fixture campaign."""
    _, draw = signflip.draw_flips(W, M, seed)
    draw_block = draw.to_dict()
    if flip_rows_sha256 is not None:
        # tamper: the recorded rows hash matches no regenerated draw
        draw_block["rows_sha256"] = flip_rows_sha256
    if flip_w_override is not None:
        draw_block["W"] = int(flip_w_override)
    config = {"campaign_id": campaign_id,
              "multiplicity_policy": {
                  "flip_draw": draw_block, "n_flips": M,
                  "n_boot": n_boot,
                  "missing_member_rule": "C-2_option_A",
                  "missing_member_p": 1.0,
                  "campaign_end_record_required": True,
                  "p_value_method": "week_level_signflip_holm"}}
    payload = (json.dumps(config, indent=2, sort_keys=True) + "\n").encode("utf-8")
    state_dir.mkdir(parents=True, exist_ok=True)
    config_path = state_dir / "campaign_config.json"
    config_path.write_bytes(payload)
    (state_dir / "campaign_config.sha256").write_bytes(
        (hashlib.sha256(payload).hexdigest() + "\n").encode("utf-8"))
    return config


def _write_ledger(path: Path, *, campaign_id: str, proposal_id: str,
                  experiment_id: str, primitive_id: str,
                  adjudicated: bool = True,
                  spec_sha256: str = "a" * 64) -> None:
    """Synthetic ledger rows in the production row shapes (detail pins
    campaign_id and experiment_id exactly as continuous_loop writes them)."""
    rows = [
        {"row_type": "proposal", "proposal_id": proposal_id,
         "proposal": {"campaign_id": campaign_id,
                      "design": {"primitives": [
                          {"primitive_id": primitive_id,
                           "params": {"arm": "B", "n_boot": 1000}}]}}},
        {"row_type": "transition", "proposal_id": proposal_id,
         "from": "ACCEPTED_FOR_EXECUTION", "to": "COMPILED",
         "detail": {"campaign_id": campaign_id,
                    "experiment_id": experiment_id,
                    "spec_sha256": spec_sha256}},
        {"row_type": "transition", "proposal_id": proposal_id,
         "from": "COMPILED", "to": "EXECUTED",
         "detail": {"campaign_id": campaign_id,
                    "experiment_id": experiment_id,
                    "phase": "started", "spec_sha256": spec_sha256}},
    ]
    if adjudicated:
        rows.append({"row_type": "transition", "proposal_id": proposal_id,
                     "from": "EXECUTED", "to": "ADJUDICATED",
                     "detail": {"campaign_id": campaign_id,
                                "experiment_id": experiment_id,
                                "result": "REJECTED"}})
    path.write_bytes(b"".join(
        (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")
        for row in rows))


def _independent_p(delta_hat, g, S, n_pos, n_neg) -> float:
    """Independent (pure-python) re-derivation of the reference p-value."""
    total = 0
    count = 0
    for row in S:
        flip = sum(int(s) * float(x) for s, x in zip(row, g)) / (
            2.0 * n_pos * n_neg)
        total += 1
        if flip <= float(delta_hat):
            count += 1
    return (1 + count) / (total + 1)


def _independent_holm(p_values, alpha=0.05):
    """Independent Holm step-down: returns (adjusted, rejected)."""
    order = sorted(range(len(p_values)), key=lambda i: (p_values[i], i))
    adjusted = [0.0] * len(p_values)
    running = 0.0
    rejected = [False] * len(p_values)
    stop = False
    m = len(p_values)
    for rank, index in enumerate(order):
        threshold = alpha / (m - rank)
        running = max(running, (m - rank) * p_values[index])
        adjusted[index] = min(1.0, running)
        if stop or p_values[index] > threshold:
            stop = True
        else:
            rejected[index] = True
    return adjusted, rejected



class LinearFormEquivalenceTests(unittest.TestCase):
    """The production linear form must equal brute-force AUC recomputation."""

    def test_matches_brute_force_week_swaps(self) -> None:
        from sklearn.metrics import roc_auc_score
        rng = np.random.default_rng(7)
        n = 240
        labels = rng.integers(0, 2, n)
        ref = rng.random(n)
        cand = ref + 0.1 * rng.standard_normal(n) + 0.05 * (2 * labels - 1)
        weeks = rng.integers(0, 40, n)
        g, n_pos, n_neg, delta = rh.week_level_g(labels, ref, cand, weeks, 40)
        S = rng.choice([-1, 1], size=(60, 40))
        worst = 0.0
        for row in S:
            swap = np.isin(weeks, np.flatnonzero(row == -1))
            ref2 = np.where(swap, cand, ref)
            cand2 = np.where(swap, ref, cand)
            brute = (roc_auc_score(labels, cand2)
                     - roc_auc_score(labels, ref2))
            linear = float(row @ g) / (2 * n_pos * n_neg)
            worst = max(worst, abs(brute - linear))
        self.assertLess(worst, 1e-9)
        self.assertLess(abs(float(np.ones(40) @ g) / (2 * n_pos * n_neg)
                            - delta), 1e-9)
        self.assertLess(abs(delta - (roc_auc_score(labels, cand)
                                     - roc_auc_score(labels, ref))), 1e-9)


class ProductionEntryPointE2ETests(unittest.TestCase):
    """Through the actual production entry point, on synthetic fixtures."""

    def _execute(self, primitive_id: str, params: dict, **fixture):
        tmp = Path(tempfile.mkdtemp(prefix=f"e2e_{primitive_id}_"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        _build_fixture(tmp, **fixture)
        result = _run_entrypoint(tmp, _render_config(primitive_id, params))
        evaluation = tmp / "outputs" / "evaluation.json"
        return tmp, result, (json.loads(evaluation.read_text(encoding="utf-8"))
                             if evaluation.is_file() else None)

    def _check_no_holdout(self, tmp: Path) -> None:
        self.assertFalse((tmp / "study_files" / "outputs" / "study_v1"
                          / "prospective").exists())

    # -- link 1+2: execution -> persisted, associated member records --------

    def test_regime_family_execution_to_persistence(self) -> None:
        tmp, result, evaluation = self._execute(
            "regime_split_analysis", {"arm": "B", "n_boot": 1000})
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self._check_no_holdout(tmp)
        assert evaluation is not None
        self.assertEqual(evaluation["harness_version"], "1.1.0")
        block = evaluation["results"]["family_measurements"]
        self.assertEqual(block["schema"], fr.SCHEMA)
        self.assertTrue(block["applicable"])
        self.assertTrue(block["member_set_complete"])
        self.assertEqual(block["family"], "regime")
        self.assertEqual(block["primitive_id"], "regime_split_analysis")
        members = {m["member_key"]: m for m in block["members"]}
        self.assertEqual(sorted(members), ["above_sma200", "below_sma200"])
        identity = block["identity"]
        self.assertEqual(identity["arm_a"], "B")
        self.assertEqual(identity["estimator_b"], "LightGBM")
        self.assertEqual(identity["n_boot"], 1000)
        self.assertEqual(len(identity["config_sha256"]), 64)
        for member in members.values():
            self.assertEqual(member["identity"], identity)
            self.assertEqual(member["family"], "regime")
            self.assertEqual(member["primitive_id"], "regime_split_analysis")
            self.assertEqual(member["measurement_status"], "ok")
            self.assertFalse(member["formal_refutation"])
            self.assertEqual(member["refutation_signal"], "unadjusted")
            payload = member["signflip"]
            self.assertEqual(payload["W"], block["week_index"]["W"])
            g = np.asarray(payload["g"])
            self.assertEqual(g.shape, (block["week_index"]["W"],))
            self.assertEqual(payload["n_pos"], member["n_events"])
            self.assertEqual(payload["n_pos"] + payload["n_neg"],
                             member["n_rows"])
            # fail-closed identity inside the persisted record
            self.assertAlmostEqual(
                float(g.sum()),
                2.0 * payload["n_pos"] * payload["n_neg"]
                * payload["delta_hat"], places=6)
        # nontrivial values: both cells are well above the frozen floors
        # (min 50 rows / 5 events), with dozens of positive events each
        for member in members.values():
            self.assertGreater(member["n_rows"], 60)
            self.assertGreater(member["n_events"], 20)
        self.assertIn(block["iut_result"]["status"],
                      (tv.ROBUST, tv.INCONCLUSIVE))
        self.assertEqual(len(block["iut_result"]["conditions"]), 2)
        self.assertFalse(block["iut_result"]["formal_refutation"])
        # pooled evaluation is still complete (the gates read it)
        self.assertIn("primary_metric", evaluation["results"])

    def test_horizon_family_refits_and_flags(self) -> None:
        tmp, result, evaluation = self._execute(
            "target_horizon_robustness", {"arm": "B", "n_boot": 1000})
        # (arm params: arm_a == arm_b == "B", estimators LR vs LightGBM)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self._check_no_holdout(tmp)
        assert evaluation is not None
        block = evaluation["results"]["family_measurements"]
        self.assertEqual(block["family"], "horizon")
        members = {int(m["member_key"]): m for m in block["members"]}
        self.assertEqual(sorted(members), [1, 2, 3])
        pooled_delta = evaluation["results"]["primary_metric"]["delta"]
        for member in members.values():
            self.assertTrue(member["flags"]["labels_rebuilt"])
            self.assertTrue(member["flags"]["maturity_purge_reverified"])
            self.assertEqual(member["measurement_status"], "ok")
        # the 1-session rung IS the frozen reference target: exact anchor
        self.assertAlmostEqual(members[1]["point"], pooled_delta, places=6)
        self.assertAlmostEqual(
            members[1]["signflip"]["delta_hat"], pooled_delta, places=6)
        # per-rung rebuilds change the measurement (not pooled reuse)
        self.assertNotEqual(members[2]["point"], members[1]["point"])
        self.assertNotEqual(members[3]["point"], members[1]["point"])
        self.assertEqual(len(block["iut_result"]["conditions"]), 3)

    def test_purge_family_refits_and_anchors(self) -> None:
        # purge_sensitivity_probe is an arm-pair primitive (A->B, same
        # estimator both arms): the pooled primary delta is the nested-arm
        # comparison, and every purge rung re-measures it.
        tmp, result, evaluation = self._execute(
            "purge_sensitivity_probe", {"arm_pair": "A->B", "n_boot": 1000})
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self._check_no_holdout(tmp)
        assert evaluation is not None
        block = evaluation["results"]["family_measurements"]
        self.assertEqual(block["family"], "purge")
        members = {int(m["member_key"]): m for m in block["members"]}
        self.assertEqual(sorted(members), [0, 5, 10])
        pooled_delta = evaluation["results"]["primary_metric"]["delta"]
        self.assertAlmostEqual(members[0]["point"], pooled_delta, places=6)
        self.assertIn("frozen study rule", members[0]["flags"]["train_rule"])
        self.assertIn("5 market sessions", members[5]["flags"]["train_rule"])
        self.assertIn("10 market sessions", members[10]["flags"]["train_rule"])
        # stricter purges refit: the measured delta changes
        self.assertNotEqual(members[5]["signflip"]["delta_hat"],
                            members[0]["signflip"]["delta_hat"])
        self.assertNotEqual(members[10]["signflip"]["delta_hat"],
                            members[0]["signflip"]["delta_hat"])

    def test_complexity_family_single_primary_rung(self) -> None:
        tmp, result, evaluation = self._execute(
            "complexity_reduction_check", {"arm": "B", "n_boot": 1000})
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self._check_no_holdout(tmp)
        assert evaluation is not None
        block = evaluation["results"]["family_measurements"]
        self.assertEqual(block["family"], "complexity")
        members = block["members"]
        self.assertEqual(len(members), 1)
        member = members[0]
        self.assertEqual(member["member_key"], "primary")
        self.assertTrue(member["flags"]["related_reanalysis"])
        self.assertFalse(member["flags"]["independent_confirmation"])
        self.assertAlmostEqual(
            member["point"],
            evaluation["results"]["primary_metric"]["delta"], places=6)

    # -- link 3: persistence -> multiplicity, verified independently --------

    def test_campaign_end_record_from_persisted_records(self) -> None:
        from autonomous_agent.proposal_layer import signflip as sf
        tmp, result, evaluation = self._execute(
            "regime_split_analysis", {"arm": "B", "n_boot": 1000})
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        assert evaluation is not None
        block = fr.load_member_block(evaluation)
        W = block["week_index"]["W"]
        campaign = _campaign_config(W)
        families = fr.family_members_from_records(
            [(block, "exp-fixture-regime")], campaign_config=campaign,
            identity_authority={"exp-fixture-regime":
                                _fixture_authority(tmp, "exp-fixture-regime")})
        self.assertEqual(sorted(families), ["regime"])
        members = families["regime"]
        self.assertEqual(len(members), 2)
        seed, S, draw = sf.load_campaign_flip_draw(campaign, W=W)
        for member, record in zip(sorted(members, key=lambda m: m.member_id),
                                  sorted(block["members"],
                                         key=lambda m: m["member_key"])):
            payload = record["signflip"]
            self.assertEqual(member.status, fr.STATUS_AVAILABLE)
            # independent pure-python re-derivation of the same p-value
            expected = _independent_p(payload["delta_hat"], payload["g"],
                                      S, payload["n_pos"], payload["n_neg"])
            self.assertAlmostEqual(member.unadjusted_p, expected, places=12)
            self.assertEqual(member.family, "regime")
            self.assertEqual(member.primitive, "regime_split_analysis")
            self.assertEqual(member.experiment_id, "exp-fixture-regime")
        record = fr.campaign_end_record(
            campaign_id="fixture-e2e", families=families, n_boot=1000,
            n_flips=1000, p_value_method=fr.APPROVED_P_VALUE_METHOD)
        family_block = record["families"]["regime"]
        self.assertEqual(family_block["m"], 2)
        self.assertTrue(family_block["feasibility"]["feasible"])
        self.assertEqual(record["p_value_method"], "week_level_signflip_holm")
        rows = {m["member_id"]: m for m in family_block["members"]}
        for row in rows.values():
            self.assertIn(row["formal_status"],
                          (fr.FORMAL_REFUTED, fr.FORMAL_INCONCLUSIVE))
            self.assertIsNotNone(row["unadjusted_p"])

    # -- fail-closed: missing measurements are never pooled-only fallback ---

    def test_fail_closed_when_frozen_column_missing(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="e2e_failclosed_"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        _build_fixture(tmp)
        result = _run_entrypoint(
            tmp, _render_config("regime_split_analysis",
                                {"arm": "B", "n_boot": 1000}),
            drop_regime_column=True)
        self.assertNotEqual(result.returncode, 0,
                            "a v1.1.0 run missing its frozen column must fail")
        self.assertFalse((tmp / "outputs" / "evaluation.json").exists(),
                         "no evaluation output may be written on failure "
                         "(never pooled-only)")
        self.assertIn("spy_above_sma200", result.stderr)

    def test_degenerate_cell_recorded_unavailable_and_inconclusive(self) -> None:
        tmp, result, evaluation = self._execute(
            "regime_split_analysis", {"arm": "B", "n_boot": 1000},
            thin_below_cell=True)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        assert evaluation is not None
        block = evaluation["results"]["family_measurements"]
        members = {m["member_key"]: m for m in block["members"]}
        self.assertEqual(members["below_sma200"]["measurement_status"],
                         "unavailable")
        self.assertIn("degenerate",
                      members["below_sma200"]["unavailable_reason"])
        self.assertEqual(members["above_sma200"]["measurement_status"], "ok")
        # the IUT can never pass with a missing member
        self.assertEqual(block["iut_result"]["status"], tv.INCONCLUSIVE)
        # and consumption maps it to the frozen C-2 Option A treatment
        families = fr.family_members_from_records(
            [(block, "exp-fixture-degenerate")],
            campaign_config=_campaign_config(block["week_index"]["W"]),
            identity_authority={"exp-fixture-degenerate":
                                _fixture_authority(
                                    tmp, "exp-fixture-degenerate")})
        by_status = {m.member_id: m.status for m in families["regime"]}
        self.assertEqual(by_status["exp-fixture-degenerate:below_sma200"],
                         fr.STATUS_UNAVAILABLE)
        self.assertEqual(by_status["exp-fixture-degenerate:above_sma200"],
                         fr.STATUS_AVAILABLE)


class FamilyRecordNegativeTests(unittest.TestCase):
    """Missing / malformed / mismatched records fail closed."""

    @staticmethod
    def _valid_block(*, W: int = 8, primitive="complexity_reduction_check",
                     family="complexity", keys=("primary",), complete=True):
        identity = dict(_SYNTH_IDENTITY)
        members = []
        for key in keys:
            g = [-1.0] * W
            members.append({
                "member_key": key, "family": family, "primitive_id": primitive,
                "n_rows": 20, "n_events": 10, "identity": identity,
                "flags": {}, "refutation_signal": "unadjusted",
                "formal_refutation": False, "measurement_status": "ok",
                "point": -0.05, "ci_lower": -0.08, "ci_upper": -0.01,
                "signflip": {"delta_hat": sum(g) / (2 * 10 * 10), "g": g,
                             "n_pos": 10, "n_neg": 10, "W": W,
                             "linear_form": "(S @ g) / (2 * n_pos * n_neg)",
                             "identity": "sum(g) == 2 * n_pos * n_neg * delta_hat"},
                "provisional_label": "provisional_refutation_signal",
            })
        return {"schema": fr.SCHEMA, "applicable": True,
                "harness_version": "1.1.0", "primitive_id": primitive,
                "family": family, "identity": identity,
                "week_index": {"W": W, "convention": "fixture", "weeks": []},
                "member_bound": 12, "members": members,
                "iut_result": {"status": "INCONCLUSIVE"},
                "member_set_complete": complete,
                "p_value_method_at_campaign_end": "week_level_signflip_holm",
                "firewall": {"refutation_signal": "unadjusted",
                             "formal_refutation": False, "note": "fixture"}}

    def _consume(self, block, experiment_id="exp-1", W=8, authority=None):
        if authority is None:
            authority = _synth_authority(experiment_id)
        return fr.family_members_from_records(
            [(block, experiment_id)], campaign_config=_campaign_config(W),
            identity_authority=authority)

    def test_missing_block_raises(self) -> None:
        with self.assertRaises(fr.MemberRecordError):
            fr.load_member_block({"something": 1})
        with self.assertRaises(fr.MemberRecordError):
            fr.load_member_block({"family_measurements": {"schema": "bogus"}})

    def test_non_applicable_block_raises(self) -> None:
        block = self._valid_block()
        block["applicable"] = False
        with self.assertRaises(fr.MemberRecordError):
            self._consume(block)

    def test_incomplete_member_set_raises(self) -> None:
        block = self._valid_block(keys=("primary",))
        block["members"] = block["members"] + [dict(block["members"][0],
                                                    member_key="ghost")]
        # even with a "complete" flag, the frozen ladder disagrees
        with self.assertRaises(fr.MemberRecordError):
            self._consume(block)

    def test_family_primitive_mismatch_raises(self) -> None:
        block = self._valid_block(family="horizon",
                                  primitive="regime_split_analysis",
                                  keys=("1",))
        block["members"][0]["member_key"] = 1
        with self.assertRaises(fr.MemberRecordError):
            self._consume(block)

    def test_week_index_mismatch_raises(self) -> None:
        first = self._valid_block()
        second = self._valid_block(W=9)
        with self.assertRaises(fr.MemberRecordError):
            fr.family_members_from_records(
                [(first, "exp-1"), (second, "exp-2")],
                campaign_config=_campaign_config(8),
                identity_authority=_synth_authority("exp-1", "exp-2"))

    def test_broken_identity_raises(self) -> None:
        block = self._valid_block()
        payload = block["members"][0]["signflip"]
        payload["g"][0] += 1.0     # violates sum(g) == 2 P delta_hat
        with self.assertRaises(fr.MemberRecordError):
            self._consume(block)

    def test_wrong_g_length_raises(self) -> None:
        block = self._valid_block()
        block["members"][0]["signflip"]["g"] = [0.0] * 7
        with self.assertRaises(fr.MemberRecordError):
            self._consume(block)

    def test_duplicate_member_ids_raise(self) -> None:
        block = self._valid_block()
        with self.assertRaises(fr.MemberRecordError):
            fr.family_members_from_records(
                [(block, "exp-1"), (block, "exp-1")],
                campaign_config=_campaign_config(8),
                identity_authority=_synth_authority("exp-1"))

    def test_bare_refutation_label_is_firewalled(self) -> None:
        block = self._valid_block()
        block["members"][0]["note"] = "this member is REFUTED"
        with self.assertRaises(fr.FirewallViolation):
            fr.load_member_block({"family_measurements": block})

    def test_member_identity_mismatch_fails_closed(self) -> None:
        # F-2: a member whose identity conflicts with its enclosing
        # block must be refused (the member-vs-block identity check).
        block = self._valid_block()
        conflicting = dict(block["members"][0]["identity"])
        conflicting["config_sha256"] = "f" * 64
        conflicting["n_boot"] = 999
        block["members"][0]["identity"] = conflicting
        with self.assertRaises(fr.MemberRecordError) as caught:
            self._consume(block)
        self.assertIn("different experiment identity",
                      str(caught.exception))


class HandVerifiedMultiplicityTests(unittest.TestCase):
    """Known-case multiplicity: engineered p-values, independent Holm."""

    def _block(self, g_value: float, *, key="primary", W=8,
               unavailable=False):
        identity = dict(_SYNTH_IDENTITY)
        g = [g_value] * W
        member = {
            "member_key": key, "family": "complexity",
            "primitive_id": "complexity_reduction_check",
            "n_rows": 20, "n_events": 10, "identity": identity, "flags": {},
            "refutation_signal": "unadjusted", "formal_refutation": False,
            "point": sum(g) / 200.0, "ci_lower": -0.09, "ci_upper": -0.02,
            "signflip": {"delta_hat": sum(g) / (2 * 10 * 10), "g": g,
                         "n_pos": 10, "n_neg": 10, "W": W,
                         "linear_form": "(S @ g) / (2 * n_pos * n_neg)",
                         "identity": "sum(g) == 2 * n_pos * n_neg * delta_hat"},
            "provisional_label": "provisional_refutation_signal",
        }
        if unavailable:
            member = {**member, "measurement_status": "unavailable",
                      "unavailable_reason": "fixture unavailability"}
        else:
            member["measurement_status"] = "ok"
        return {"schema": fr.SCHEMA, "applicable": True,
                "harness_version": "1.1.0",
                "primitive_id": "complexity_reduction_check",
                "family": "complexity", "identity": identity,
                "week_index": {"W": W, "convention": "fixture", "weeks": []},
                "member_bound": 12, "members": [member],
                "iut_result": {"status": "INCONCLUSIVE"},
                "member_set_complete": True,
                "p_value_method_at_campaign_end": "week_level_signflip_holm",
                "firewall": {"refutation_signal": "unadjusted",
                             "formal_refutation": False, "note": "fixture"}}

    def test_engineered_p_values_and_hand_computed_holm(self) -> None:
        W = 8
        campaign = _campaign_config(W)
        seed, S, draw = signflip.load_campaign_flip_draw(campaign, W=W)
        blocks = [
            (self._block(-1.0, key="primary"), "exp-strong"),
            (self._block(0.0, key="primary"), "exp-null"),
            (self._block(1.0, key="primary"), "exp-positive"),
            (self._block(-1.0, key="primary", unavailable=True), "exp-missing"),
        ]
        families = fr.family_members_from_records(
            blocks, campaign_config=campaign,
            identity_authority=_synth_authority(
                "exp-strong", "exp-null", "exp-positive", "exp-missing"))
        members = families["complexity"]
        self.assertEqual(len(members), 4)
        by_id = {m.member_id: m for m in members}
        strong = by_id["exp-strong:primary"]
        null = by_id["exp-null:primary"]
        positive = by_id["exp-positive:primary"]
        missing = by_id["exp-missing:primary"]
        # known cases, independently re-derived (pure python)
        self.assertAlmostEqual(strong.unadjusted_p,
                               _independent_p(-0.04, [-1.0] * W, S, 10, 10),
                               places=12)
        self.assertLess(strong.unadjusted_p, 0.05)     # g all-negative: delta is the minimum
        self.assertGreaterEqual(null.unadjusted_p, 0.9)
        self.assertGreaterEqual(positive.unadjusted_p, 0.9)
        self.assertEqual(missing.status, fr.STATUS_UNAVAILABLE)
        record = fr.campaign_end_record(
            campaign_id="fixture-holm", families=families, n_boot=1000,
            n_flips=1000, p_value_method=fr.APPROVED_P_VALUE_METHOD)
        rows = {m["member_id"]: m for m in
                record["families"]["complexity"]["members"]}
        # independent Holm over the full family: the unavailable member
        # enters at effective p = 1.0 (C-2 Option A), so m = 4 governs the
        # step-down thresholds.
        available = [strong, null, positive]
        pvals = [m.unadjusted_p for m in available] + [1.0]
        adjusted, rejected = _independent_holm(pvals)
        for member, adj, rej in zip(available, adjusted[:3], rejected[:3]):
            row = rows[member.member_id]
            self.assertAlmostEqual(row["adjusted_p"], adj, places=9)
            self.assertEqual(row["formal_status"] ==
                             fr.FORMAL_REFUTED, rej)
        # the unavailable member counts toward m at p = 1.0 (C-2 Option A),
        # is stored without an unadjusted p, and is never formally refuted
        self.assertEqual(rows["exp-missing:primary"]["formal_status"],
                         fr.FORMAL_UNAVAILABLE)
        self.assertIsNone(rows["exp-missing:primary"]["unadjusted_p"])
        self.assertGreaterEqual(rows["exp-missing:primary"]["adjusted_p"],
                                strong.unadjusted_p)
        self.assertTrue(rejected[0])                 # the strong member refutes
        self.assertFalse(rejected[1] or rejected[2])
        self.assertIn("unadjusted_p", rows["exp-strong:primary"])
        self.assertIn("adjusted_p", rows["exp-strong:primary"])


class BoundaryAndDriftTests(unittest.TestCase):
    """The wiring must respect the frozen import boundary and never drift.

    The freeze-integrity and T12 tests enforce that the execution side
    never imports the multiplicity machinery; these localized guards pin
    the same invariant on the files this remediation touched and prove
    the execution-side mirrors of the campaign-side constants are
    byte-identical to their authorities.
    """

    def test_execution_side_source_free_of_multiplicity_machinery(self) -> None:
        # Needle concatenated exactly as test_freeze_integrity builds it,
        # so this assertion cannot match its own source text.
        needle = "import " + "multiplicity"
        source = (REPO / "autonomous_agent" / "recipe_harness.py").read_text(
            encoding="utf-8")
        self.assertNotIn("proposal_layer", source)
        self.assertNotIn(needle, source)
        self.assertNotIn("import signflip", source)
        # The test file itself is scanned by the freeze needle too.
        own = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn(needle, own)

    def test_execution_side_constants_match_their_campaign_side_authority(self) -> None:
        # Family member bounds: three_valued mirrors the frozen family
        # table the consumption side delegates to.
        self.assertEqual(
            tv.FAMILY_MEMBER_BOUNDS,
            {name: spec["member_bound"] for name, spec in fr.FAMILIES.items()})
        # Firewall vocabulary: identical tokens on both sides, so a
        # stamped record round-trips through the consumption firewall.
        self.assertEqual(tv.REFUTATION_SIGNAL_VALUE, fr.REFUTATION_SIGNAL_VALUE)
        self.assertEqual(tv.LABEL_PROVISIONAL_REFUTATION,
                         fr.LABEL_PROVISIONAL_REFUTATION)
        self.assertEqual(tv.LABEL_NO_SIGNAL, fr.LABEL_NO_SIGNAL)
        # The harness's stamped method name is the approved method itself.
        self.assertEqual(rh.CAMPAIGN_END_P_VALUE_METHOD,
                         fr.APPROVED_P_VALUE_METHOD)
        self.assertEqual(rh.CAMPAIGN_END_P_VALUE_METHOD,
                         "week_level_signflip_holm")

    def test_consumption_facade_is_the_frozen_api_only(self) -> None:
        # The facade delegates; it must not re-implement.  Every member is
        # the frozen module's own object, reached without a second
        # statistics path.
        import importlib
        mult = importlib.import_module(
            "autonomous_agent.proposal_layer.multiplicity")
        signflip = importlib.import_module(
            "autonomous_agent.proposal_layer.signflip")
        self.assertIs(fr.campaign_end_record, mult.campaign_end_record)
        self.assertIs(fr.FirewallViolation, mult.FirewallViolation)
        self.assertIs(fr.FAMILIES, mult.FAMILIES)
        # F-1 facade extension: the finalization successor's surface is
        # pure delegation too (no second statistics path).
        self.assertIs(fr.append_record, mult.append_record)
        self.assertIs(fr.read_records, mult.read_records)
        self.assertIs(fr.FamilyMember, mult.FamilyMember)
        self.assertIs(fr.require_approved_method,
                      mult.require_approved_method)
        self.assertEqual(fr.APPROVED_P_VALUE_METHOD,
                         signflip.APPROVED_METHOD_NAME)
        self.assertEqual(fr.FAMILIES["regime"]["primitive"],
                         "regime_split_analysis")


class ExecutionFailClosedNegativeTests(unittest.TestCase):
    """F-2 negative coverage of fail-closed execution-side branches.

    Every test runs the real production entry point in a throwaway
    fixture and verifies the exact error, that NO evaluation output is
    written on the fail-closed paths, and that no partial artifact could
    be mistaken for a completed family evaluation.
    """

    def test_h10b_n_boot_floor_is_refused_before_evaluation_output(self) -> None:
        # Layer 1: the compiler refuses a below-floor family config at
        # render time (H-10b floor lives in the primitive ParamSpec).
        with self.assertRaises(compiler.CompileError) as caught:
            compiler._render_v110_config(
                {"research_question_id": "rq-floor",
                 "hypothesis": "the H-10b floor must bind at render time",
                 "baseline_id": "BASELINE_FIXTURE"},
                get_primitive("regime_split_analysis"),
                {"arm": "B", "n_boot": 500})
        self.assertIn("n_boot", str(caught.exception))
        # Layer 2: the execution-side raise — a hand-written config that
        # bypasses the compiler must still fail closed, and no
        # evaluation output may be produced below the floor.
        def below_floor(text: str) -> str:
            config = json.loads(text)
            config["n_boot"] = 500
            return json.dumps(config, indent=2, sort_keys=True) + "\n"

        tmp, result, evaluation = _execute_in_fixture(
            self, "regime_split_analysis", {"arm": "B", "n_boot": 1000},
            config_mutator=below_floor)
        self.assertNotEqual(result.returncode, 0,
                            "a below-floor family config must fail the run")
        self.assertIsNone(
            evaluation,
            "no evaluation output may exist below the H-10b floor")
        self.assertFalse((tmp / "outputs" / "evaluation.json").exists())
        self.assertIn("n_boot >= 1000", result.stderr)
        self.assertIn("got 500", result.stderr)

    def test_non_family_v110_primitive_emits_applicable_false(self) -> None:
        tmp, result, evaluation = _execute_in_fixture(
            self, "point_in_time_data_audit", {"arm": "B", "n_boot": 1000})
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        assert evaluation is not None
        block = evaluation["results"]["family_measurements"]
        self.assertEqual(block["schema"], fr.SCHEMA)
        self.assertIs(block["applicable"], False)
        self.assertEqual(block["primitive_id"], "point_in_time_data_audit")
        self.assertIn("no Holm family", block["reason"])
        for key in ("members", "iut_result", "member_set_complete",
                    "family"):
            self.assertNotIn(
                key, block,
                "an applicable-false block may never claim a completed "
                "family evaluation")
        # consumption loads it (schema sound) but refuses it outright
        loaded = fr.load_member_block(evaluation)
        with self.assertRaises(fr.MemberRecordError) as caught:
            fr.family_members_from_records(
                [(loaded, "exp-audit")],
                campaign_config=_campaign_config(8),
                identity_authority={"exp-audit":
                                    _fixture_authority(tmp, "exp-audit")})
        self.assertIn("no applicable family measurements",
                      str(caught.exception))
        self.assertFalse((tmp / "study_files" / "outputs" / "study_v1"
                          / "prospective").exists())

    def test_member_frame_below_block_weeks_fails_the_run_closed(self) -> None:
        tmp, result, evaluation = _execute_in_fixture(
            self, "regime_split_analysis", {"arm": "B", "n_boot": 1000},
            starve_below_cell=True)
        self.assertNotEqual(
            result.returncode, 0,
            "a member frame under the block-bootstrap week floor must "
            "fail the run closed (never recorded, never pooled-only)")
        self.assertIsNone(evaluation)
        self.assertFalse((tmp / "outputs" / "evaluation.json").exists(),
                         "no partial evaluation may be written")
        self.assertIn("Insufficient calendar weeks", result.stderr)

    def test_purge_family_without_the_spy_calendar_fails_closed(self) -> None:
        tmp, result, evaluation = _execute_in_fixture(
            self, "purge_sensitivity_probe",
            {"arm_pair": "A->B", "n_boot": 1000}, drop_spy=True)
        self.assertNotEqual(
            result.returncode, 0,
            "purge rungs require the frozen SPY session calendar; a "
            "missing SPY cache must fail closed, never another calendar")
        self.assertIsNone(evaluation)
        self.assertFalse((tmp / "outputs" / "evaluation.json").exists())
        self.assertIn("Missing local OHLCV file", result.stderr)
        self.assertIn("SPY", result.stderr)


class CampaignEndFinalizationE2ETests(unittest.TestCase):
    """F-1 + F-2#5: real execution -> durable result.json -> finalization.

    setUpClass performs ONE production execution through the REAL
    adapter (``ExperimentAdapter.run_experiment`` with the fixed
    command registry, i.e. the byte-identical
    ``python -m autonomous_agent.experiments.run_experiment`` entry
    point inside an isolated workspace).  Every test then works on
    scratch copies of the durable artifact, its own synthetic ledger /
    config fixture, and an isolated output destination — Campaign 4's
    historical record is never appended to or recomputed in place.
    """

    CAMPAIGN_ID = "campaign-fixture-finalize"
    EXP_ID = "exp-f1-finalization"

    @classmethod
    def setUpClass(cls) -> None:
        cls.class_tmp = Path(tempfile.mkdtemp(prefix="f1_finalization_"))
        cls.fixture = cls.class_tmp / "ws"
        cls.fixture.mkdir(parents=True)
        # thin below-cell: one available member + one execution-recorded
        # unavailable member, satisfying the mixed-family requirement
        _build_fixture(cls.fixture, thin_below_cell=True)
        cls.adapter = ExperimentAdapter(
            root=cls.fixture,
            candidates_root=cls.fixture / "autonomous_agent" / "candidates",
            state_root=cls.fixture / "autonomous_agent" / "state")
        cls.adapter.baseline_state_path.parent.mkdir(parents=True,
                                                    exist_ok=True)
        write_json_atomic(cls.adapter.baseline_state_path, {
            "status": "REPRODUCED",
            "pipeline_fingerprint": cls.adapter.pipeline_fingerprint(),
            "result": ExperimentResult(
                experiment_id="baseline-reproduction",
                status="REPRODUCED").to_dict(),
        })
        config_text = _render_config("regime_split_analysis",
                                     {"arm": "B", "n_boot": 1000})
        spec = ExperimentSpec(
            experiment_id=cls.EXP_ID,
            parent_version="V2.0.61",
            hypothesis=("Fixture hypothesis for the campaign-end "
                        "finalization E2E: regime family measurements "
                        "must be produced by real execution and persist "
                        "through the adapter's durable result.json."),
            proposed_change={
                "summary": ("Install the compiler-rendered v1.1.0 "
                            "regime-split family config (fixture only)."),
                "files": [{"path": ("autonomous_agent/experiments/"
                                     "experiment_config.json"),
                           "content": config_text}]},
            files_allowed_to_change=("autonomous_agent/experiments",),
            evaluation_protocol={"acceptance_criteria":
                                 {"primary_metric_min_delta": -1.0}},
            random_seed=42, resource_limits={}, timeout=900.0)
        cls.result = cls.adapter.run_experiment(spec)
        # F-6: the executed spec is the authoritative identity source;
        # the scenario fixtures persist it beside result.json exactly as
        # the adapter does for real candidates.
        cls.spec_dict = spec.to_dict()
        cls.spec_sha256 = hardening.spec_fingerprint(cls.spec_dict)
        cls.result_path = (cls.fixture / "autonomous_agent" / "candidates"
                           / cls.EXP_ID / "result.json")
        if not cls.result_path.is_file():
            raise AssertionError(
                "the adapter did not write a durable result.json: "
                f"status={cls.result.status} error={cls.result.error}")
        cls.result_json = json.loads(
            cls.result_path.read_text(encoding="utf-8"))
        metrics = cls.result_json.get("metrics") or {}
        if "family_measurements" not in metrics:
            raise AssertionError(
                "the adapter run did not persist family measurements: "
                f"status={cls.result_json.get('status')} "
                f"error={cls.result_json.get('error')}")
        cls.block = fr.load_member_block(cls.result_path)
        cls.W = int(cls.block["week_index"]["W"])

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.class_tmp, ignore_errors=True)

    # -- scratch-scenario helpers ------------------------------------------

    def _scenario(self, *, block_mode="keep", config_seed=20261016,
                  flip_rows_sha256=None, flip_w_override=None) -> dict:
        """Isolated candidates/ledger/config/output set for one test."""
        scratch = Path(tempfile.mkdtemp(prefix="f1_scenario_"))
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        result_json = json.loads(json.dumps(self.result_json))
        if block_mode == "strip":
            # pooled-only artifact: durable result without its block
            (result_json.get("metrics") or {}).pop("family_measurements",
                                                   None)
        elif block_mode == "drop_member":
            block = result_json["metrics"]["family_measurements"]
            block["members"] = block["members"][:1]
        candidate_dir = scratch / "candidates" / self.EXP_ID
        candidate_dir.mkdir(parents=True)
        if block_mode != "absent":
            (candidate_dir / "result.json").write_bytes(
                json.dumps(result_json, sort_keys=True).encode("utf-8"))
            (candidate_dir / "spec.json").write_bytes(
                json.dumps(self.spec_dict, sort_keys=True).encode("utf-8"))
        state = scratch / "state"
        config_data = _write_campaign_config(
            state, campaign_id=self.CAMPAIGN_ID, W=self.W,
            seed=config_seed, flip_rows_sha256=flip_rows_sha256,
            flip_w_override=flip_w_override)
        ledger = state / "proposal_ledger.jsonl"
        _write_ledger(ledger, campaign_id=self.CAMPAIGN_ID,
                      proposal_id="prop-fixture-1",
                      experiment_id=self.EXP_ID,
                      primitive_id="regime_split_analysis",
                      spec_sha256=self.spec_sha256)
        return {"out": scratch / "out" / "campaign_end_multiplicity.jsonl",
                "config": state / "campaign_config.json",
                "config_data": config_data, "ledger": ledger,
                "candidates": scratch / "candidates"}

    @staticmethod
    def _finalize(scenario: dict, **kwargs) -> dict:
        return cef.finalize_campaign_end(
            CampaignEndFinalizationE2ETests.CAMPAIGN_ID,
            out_path=scenario["out"], config_path=scenario["config"],
            ledger_path=scenario["ledger"],
            candidates_root=scenario["candidates"], **kwargs)

    # -- F-2 #5: the durable result.json path through the real adapter ----

    def test_adapter_execution_persists_the_block_durably(self) -> None:
        self.assertIn(self.result.status, ("ACCEPTED", "REJECTED"))
        self.assertEqual(self.result_json["experiment_id"], self.EXP_ID)
        persisted = self.result_json["metrics"]["family_measurements"]
        self.assertTrue(persisted["member_set_complete"])
        self.assertEqual(
            sorted(m["member_key"] for m in persisted["members"]),
            ["above_sma200", "below_sma200"])
        self.assertEqual(persisted["identity"]["n_boot"], 1000)
        self.assertEqual(len(persisted["identity"]["config_sha256"]), 64)
        # the durable artifact is exactly what the consumption module
        # reads; measurements were persisted by execution, not by tests
        self.assertEqual(fr.load_member_block(self.result_path), self.block)
        workspace = (self.fixture / "autonomous_agent" / "candidates"
                     / self.EXP_ID / "workspace")
        if self.result.status != "ACCEPTED":
            # rejected candidates are destroyed; the durable block is not
            self.assertFalse(workspace.exists())
        self.assertTrue(self.result_path.is_file())

    # -- section 3: the full finalization sequence on fixtures -------------

    def test_finalization_consumes_persisted_records_end_to_end(self) -> None:
        scenario = self._scenario()
        outcome = self._finalize(scenario)
        self.assertTrue(outcome["written"])
        record = outcome["record"]
        self.assertEqual(record["record_type"], "campaign_end_multiplicity")
        self.assertEqual(record["campaign_id"], self.CAMPAIGN_ID)
        self.assertEqual(record["p_value_method"],
                         "week_level_signflip_holm")
        self.assertEqual(
            record["ledger_sha256"],
            hashlib.sha256(scenario["ledger"].read_bytes()).hexdigest())
        self.assertEqual(sorted(record["families"]), ["regime"])
        family = record["families"]["regime"]
        self.assertEqual(family["m"], 2)
        self.assertTrue(family["feasibility"]["feasible"])
        rows = {m["member_id"]: m for m in family["members"]}
        self.assertEqual(set(rows), {f"{self.EXP_ID}:above_sma200",
                                     f"{self.EXP_ID}:below_sma200"})
        above_row = rows[f"{self.EXP_ID}:above_sma200"]
        below_row = rows[f"{self.EXP_ID}:below_sma200"]
        # 4. correct frozen family / member / experiment association
        for row in (above_row, below_row):
            self.assertEqual(row["family"], "regime")
            self.assertEqual(row["experiment_id"], self.EXP_ID)
        # 6. unavailable member: C-2 Option A, never a successful test
        self.assertEqual(below_row["status"], fr.STATUS_UNAVAILABLE)
        self.assertEqual(below_row["formal_status"],
                         fr.FORMAL_UNAVAILABLE)
        self.assertIsNone(below_row["unadjusted_p"])
        self.assertIn("C-2", below_row["reason"])
        self.assertNotEqual(below_row["formal_status"], fr.FORMAL_REFUTED)
        # 5. available member: p-value independently re-derived from the
        # PERSISTED record and the campaign's recorded flip draw
        self.assertEqual(above_row["status"], fr.STATUS_AVAILABLE)
        _, S, _ = signflip.load_campaign_flip_draw(scenario["config_data"],
                                                   W=self.W)
        member = next(m for m in self.block["members"]
                      if m["member_key"] == "above_sma200")
        payload = member["signflip"]
        expected_p = _independent_p(payload["delta_hat"], payload["g"],
                                    S, payload["n_pos"], payload["n_neg"])
        self.assertAlmostEqual(above_row["unadjusted_p"], expected_p,
                               places=12)
        # 7. independent Holm over the COMPLETE family (C-2 counts the
        # unavailable member toward m at effective p = 1.0)
        adjusted, rejected = _independent_holm([expected_p, 1.0])
        self.assertAlmostEqual(above_row["adjusted_p"], adjusted[0],
                               places=9)
        self.assertEqual(above_row["formal_status"] == fr.FORMAL_REFUTED,
                         rejected[0])
        self.assertAlmostEqual(below_row["adjusted_p"], adjusted[1],
                               places=9)
        # the consumption link was actually exercised (not recreated)
        self.assertEqual(outcome["inventory"]["persisted"],
                         [{"experiment_id": self.EXP_ID,
                           "family": "regime",
                           "primitive": "regime_split_analysis",
                           "result_json": str(
                               scenario["candidates"] / self.EXP_ID
                               / "result.json")}])
        self.assertEqual(outcome["inventory"]["unavailable"], [])
        # append-only: exactly one row, and a rerun recomputes identically
        written = fr.read_records(scenario["out"])
        self.assertEqual([r["campaign_id"] for r in written],
                         [self.CAMPAIGN_ID])
        rerun = self._finalize(scenario)
        self.assertFalse(rerun["written"])
        self.assertEqual(len(fr.read_records(scenario["out"])), 1)
        # Campaign 4's historical record is untouched (module-level
        # guards re-assert this at suite teardown with the same pin)
        historical = (REPO / "autonomous_agent" / "state"
                      / "campaign_end_multiplicity.jsonl")
        self.assertEqual(
            hashlib.sha256(historical.read_bytes()).hexdigest(),
            "7547704337738e829ce71bddd524b7458cdc62f38ee3642443597eedd5abe9d3")

    # -- 8: missing / invalid required data blocks finalization ------------

    def test_pooled_only_result_json_blocks_finalization(self) -> None:
        scenario = self._scenario(block_mode="strip")
        with self.assertRaises(fr.MemberRecordError) as caught:
            self._finalize(scenario)
        self.assertIn("no family_measurements block",
                      str(caught.exception))
        self.assertFalse(scenario["out"].exists(),
                         "no record may exist after a pooled-only fallback")
        self.assertEqual(fr.read_records(scenario["out"]), [])

    def test_incomplete_member_set_blocks_finalization(self) -> None:
        scenario = self._scenario(block_mode="drop_member")
        with self.assertRaises(fr.MemberRecordError) as caught:
            self._finalize(scenario)
        self.assertIn("does not match the frozen ladder",
                      str(caught.exception))
        self.assertFalse(scenario["out"].exists())

    def test_adjudicated_without_durable_result_blocks_finalization(self) -> None:
        scenario = self._scenario(block_mode="absent")
        with self.assertRaises(cef.FinalizationError) as caught:
            self._finalize(scenario)
        self.assertIn("durable result.json is missing",
                      str(caught.exception))
        self.assertFalse(scenario["out"].exists())

    def test_tampered_flip_draw_and_week_index_block_finalization(self) -> None:
        # recorded rows hash matching no regenerated draw (re-record tamper)
        scenario = self._scenario(flip_rows_sha256="0" * 64)
        with self.assertRaises(signflip.FlipProvenanceMissing) as caught:
            self._finalize(scenario)
        self.assertIn("hash-match", str(caught.exception))
        self.assertFalse(scenario["out"].exists())
        # recorded week index disagreeing with the persisted block
        scenario2 = self._scenario(flip_w_override=self.W + 1)
        with self.assertRaises(signflip.FlipProvenanceMissing) as caught2:
            self._finalize(scenario2)
        self.assertIn("does not match the current frame",
                      str(caught2.exception))
        self.assertFalse(scenario2["out"].exists())


class ConfigurationIdentityProvenanceTests(unittest.TestCase):
    """F-6: the persisted identity must be tied to its source of truth.

    Isolated synthetic fixtures only — no experiment execution, no
    campaign, no persistent state.  Five required cases: correct
    authoritative fingerprint; changed configuration with the old
    fingerprint; mismatched specification fingerprint; missing/malformed
    authoritative identity; an internally self-consistent record whose
    identity disagrees with the authoritative specification chain.
    """

    def _consume(self, block, experiment_id="exp-f6", authority=None, W=8):
        if authority is None:
            authority = {experiment_id:
                         _synth_authority(experiment_id)[experiment_id]}
        return fr.family_members_from_records(
            [(block, experiment_id)],
            campaign_config=_campaign_config(W),
            identity_authority=authority)

    @staticmethod
    def _block():
        return FamilyRecordNegativeTests._valid_block()

    # 1. a correct authoritative fingerprint is accepted -----------------
    def test_correct_authoritative_fingerprint_is_accepted(self) -> None:
        families = self._consume(self._block())
        self.assertEqual(sorted(families), ["complexity"])
        self.assertEqual(len(families["complexity"]), 1)
        self.assertEqual(families["complexity"][0].status,
                         fr.STATUS_AVAILABLE)

    # 2. a changed configuration with the old fingerprint is refused -----
    def test_changed_configuration_with_the_old_fingerprint_refused(
            self) -> None:
        block = self._block()          # carries the ORIGINAL config hash
        changed = {**_SYNTH_CONFIG, "n_boot": 1001}
        spec = _synth_spec(changed)    # source of truth now installs new cfg
        authority = {"exp-f6": fr.authoritative_identity(
            spec, experiment_id="exp-f6",
            ledger_spec_sha256=hardening.spec_fingerprint(spec))}
        with self.assertRaises(fr.MemberRecordError) as caught:
            self._consume(block, authority=authority)
        self.assertIn("installs a configuration hashing to",
                      str(caught.exception))

    # 3. a mismatched specification fingerprint is refused ---------------
    def test_mismatched_specification_fingerprint_refused(self) -> None:
        # (a) loader level: recorded ledger sha disagrees with the spec
        with self.assertRaises(fr.MemberRecordError) as caught:
            fr.authoritative_identity(
                _synth_spec(), experiment_id="exp-f6",
                ledger_spec_sha256="b" * 64)
        self.assertIn("disagrees with its authoritative ledger record",
                      str(caught.exception))
        # (b) verification level: pre-built authority with a different
        # recorded ledger value is refused before any member is consumed
        forged = {**_synth_authority("exp-f6")["exp-f6"],
                  "ledger_spec_sha256": "e" * 64}
        with self.assertRaises(fr.MemberRecordError) as caught2:
            self._consume(self._block(),
                          authority={"exp-f6": forged})
        self.assertIn("disagrees with the authoritative ledger record",
                      str(caught2.exception))

    # 4. missing or malformed authoritative identity fails closed --------
    def test_missing_or_malformed_authoritative_identity_fails_closed(
            self) -> None:
        # (a) no authority entry for the experiment at all
        with self.assertRaises(fr.MemberRecordError) as caught:
            self._consume(self._block(), authority={})
        self.assertIn("no authoritative configuration/specification identity",
                      str(caught.exception))
        # (b) malformed hash inside an otherwise present authority
        malformed = {**_synth_authority("exp-f6")["exp-f6"],
                     "config_sha256": "not-a-sha256"}
        with self.assertRaises(fr.MemberRecordError) as caught2:
            self._consume(self._block(),
                          authority={"exp-f6": malformed})
        self.assertIn("missing or malformed", str(caught2.exception))
        # (c) the source of truth itself is absent — no hash invented
        missing = Path(tempfile.mkdtemp(prefix="f6_nospec_"))
        self.addCleanup(shutil.rmtree, missing, ignore_errors=True)
        with self.assertRaises(fr.MemberRecordError) as caught3:
            fr.load_authoritative_identity(
                "exp-f6", spec_path=missing / "spec.json",
                ledger_spec_sha256="a" * 64)
        self.assertIn("source of truth", str(caught3.exception))
        # (d) authority map passed but explicitly None (fail closed)
        with self.assertRaises(fr.MemberRecordError):
            fr.family_members_from_records(
                [(self._block(), "exp-f6")],
                campaign_config=_campaign_config(8),
                identity_authority=None)

    # 5. internally self-consistent record disagreeing with authority ----
    def test_self_consistent_record_disagreeing_with_authority_refused(
            self) -> None:
        # Members and block agree with each other, the linear form is
        # intact, and the forged hash is a *valid* sha256 — only the
        # authoritative chain exposes the disagreement.
        block = self._block()
        forged_config = {**_SYNTH_CONFIG, "seeds": [7, 8, 9]}
        forged = {**_SYNTH_IDENTITY,
                  "seeds": [7, 8, 9],
                  "config_sha256": fr.config_identity_sha256(forged_config)}
        block["identity"] = forged
        for member in block["members"]:
            member["identity"] = dict(forged)
        self.assertNotEqual(forged["config_sha256"],
                            _SYNTH_IDENTITY["config_sha256"])
        with self.assertRaises(fr.MemberRecordError) as caught:
            self._consume(block)
        self.assertIn("internally self-consistent record disagrees",
                      str(caught.exception))

    # provenance check is wire-order: schema/applicable/ladder first -----
    def test_provenance_argument_is_required_by_the_public_api(self) -> None:
        with self.assertRaises(TypeError):
            fr.family_members_from_records(
                [(self._block(), "exp-f6")],
                campaign_config=_campaign_config(8))


if __name__ == "__main__":
    unittest.main()
