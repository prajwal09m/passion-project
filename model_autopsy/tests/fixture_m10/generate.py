"""M10 unseen-project corpus generator (offline, deterministic).

Eight projects with mechanisms NOT represented in the M9 scenarios.
Run once; artifacts are frozen. Sealed truth goes to _sealed/
(which the investigator never reads); only plain-language briefs
travel with the artifacts.

Mechanisms:
- m10_ward_gap: classification, one ward degraded (subgroup).
- m10_proxy_signal: tabular classification, a non-score input column
  near-duplicates the label (input leakage through a proxy).
- m10_threshold_skew: classification, scores systematically high
  (miscalibration in the operating range).
- m10_stale_lag: forecasting, predictions lag the target (stale
  inputs); errors persist with autocorrelated residuals.
- m10_district_scale: regression, one district's inputs on a
  different scale (segment-concentrated error, clean splits).
- m10_combo: forecasting, mild drift PLUS a weak district gap
  (two simultaneous mechanisms; partial credit expected).
- m10_steady: clean control (correct-null expected).
- m10_sparse: tiny pilot (inconclusive required).
"""
import csv
import math
import random

OUT = "model_autopsy/tests/fixture_m10"
SEALED = OUT + "/_sealed"


def _w(path, header, rows):
    with open(f"{OUT}/{path}", "w", newline="") as f:
        csv.writer(f).writerows([header, *rows])


def ward_gap(rng):
    rows = []
    for i in range(1500):
        ward = rng.choice(["north", "south", "east"])
        x = rng.gauss(0, 1)
        logit = 1.2 * x + (0.0 if ward != "east" else -1.6)
        p = 1 / (1 + math.exp(-logit))
        label = 1 if rng.random() < p else 0
        score = 1 / (1 + math.exp(-1.2 * x))  # blind to the ward gap
        rows.append((ward, round(x, 3), label, round(score, 4)))
    _w("m10_ward_gap.csv", ["ward", "x", "label", "score"], rows)


def proxy_signal(rng):
    rows = []
    for i in range(1500):
        x1, x2 = rng.gauss(0, 1), rng.gauss(0, 1)
        label = 1 if 0.8 * x1 - 0.5 * x2 + rng.gauss(0, 0.6) > 0 else 0
        proxy = label + rng.gauss(0, 0.05)  # near-duplicate of label
        score = 1 / (1 + math.exp(-(0.8 * x1 - 0.5 * x2)))
        rows.append((round(x1, 3), round(x2, 3), round(proxy, 3), label,
                     round(score, 4)))
    _w("m10_proxy_signal.csv", ["x1", "x2", "derived_flag", "label",
                                "score"], rows)


def threshold_skew(rng):
    rows = []
    for i in range(1500):
        x = rng.gauss(0, 1)
        p = 1 / (1 + math.exp(-x))
        label = 1 if rng.random() < p else 0
        score = min(0.99, p + 0.18)  # systematically high
        rows.append((round(x, 3), label, round(score, 4)))
    _w("m10_threshold_skew.csv", ["x", "label", "score"], rows)


def stale_lag(rng):
    rows = []
    val = 50.0
    for i in range(300):
        day = f"2024-{i // 28 + 1:02d}-{(i % 28) + 1:02d}"
        val += rng.gauss(0.15, 1.2)
        lag = 3
        pred_idx = max(0, i - lag)
        rows.append((day, round(val, 2), None, "train" if i < 150 else
                     "test"))
        rows[-1] = (day, round(val, 2), round(
            val - 0.15 * lag + rng.gauss(0, 0.4), 2),
            "train" if i < 150 else "test")
    _w("m10_stale_lag.csv", ["date", "target", "prediction", "split"],
       rows)


def district_scale(rng):
    rows = []
    for i in range(1200):
        d = rng.choice(["a", "b", "c"])
        size = rng.uniform(40, 140)
        # district c logged in different units; model unaware
        true = 2.0 * size + rng.gauss(0, 30)
        pred = 2.0 * (size * (0.1 if d == "c" else 1.0)) + rng.gauss(0, 5)
        rows.append((d, round(size, 1), round(true, 1), round(pred, 1)))
    _w("m10_district_scale.csv", ["district", "size", "target",
                                  "prediction"], rows)


def combo(rng):
    rows = []
    for i in range(300):
        day = f"2024-{i // 28 + 1:02d}-{(i % 28) + 1:02d}"
        drift = 0.0 if i < 200 else (i - 200) * 0.25
        district = "x" if i % 3 else "z"
        gap = -6.0 if district == "z" else 0.0
        target = 100 + drift + rng.gauss(0, 1.5)
        pred = 100 + gap + rng.gauss(0, 1.0)
        rows.append((day, district, round(target, 2), round(pred, 2),
                     "train" if i < 150 else "test"))
    _w("m10_combo.csv", ["date", "district", "target", "prediction",
                         "split"], rows)


def steady(rng):
    rows = []
    for i in range(1200):
        x = rng.gauss(0, 1)
        target = 3.0 * x + rng.gauss(0, 1.0)
        pred = 3.0 * x + rng.gauss(0, 0.5)
        rows.append((round(x, 3), round(target, 2), round(pred, 2)))
    _w("m10_steady.csv", ["x", "target", "prediction"], rows)


def sparse(rng):
    rows = []
    for i in range(60):
        x = rng.gauss(0, 1)
        label = 1 if x + rng.gauss(0, 1) > 0 else 0
        score = 1 / (1 + math.exp(-x))
        rows.append((round(x, 3), label, round(score, 4)))
    _w("m10_sparse.csv", ["x", "label", "score"], rows)


def main():
    import json
    import os
    rng = random.Random(20261101)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(SEALED, exist_ok=True)
    ward_gap(rng)
    proxy_signal(rng)
    threshold_skew(rng)
    stale_lag(rng)
    district_scale(rng)
    combo(rng)
    steady(rng)
    sparse(rng)
    truth = {
        "m10_ward_gap": {"mechanism": "east-ward subgroup degradation",
                         "family": "subgroup", "grade": "discovered",
                         "key_tool": "classification_metrics"},
        "m10_proxy_signal": {"mechanism": "non-score input near-duplicate",
                             "family": "leakage", "grade": "discovered",
                             "key_tool": "feature_target_suspiciousness"},
        "m10_threshold_skew": {"mechanism": "systematic over-scoring",
                               "family": "calibration",
                               "grade": "discovered",
                               "key_tool": "calibration_and_error_analysis"},
        "m10_stale_lag": {"mechanism": "lagged (stale) predictions",
                          "family": "misspecification",
                          "grade": "partial",
                          "key_tool": "residual_time_analysis"},
        "m10_district_scale": {"mechanism": "district-c unit inconsistency",
                               "family": "subgroup", "grade": "discovered",
                               "key_tool": "regression_metrics"},
        "m10_combo": {"mechanism": "drift plus weak district gap",
                      "family": "drift", "grade": "partial",
                      "key_tool": "temporal_changepoint_scan"},
        "m10_steady": {"mechanism": "none (healthy)",
                       "family": "clean", "grade": "correct-null",
                       "key_tool": "none"},
        "m10_sparse": {"mechanism": "unknown (n too small)",
                       "family": "thin", "grade": "inconclusive",
                       "key_tool": "none"},
    }
    with open(f"{SEALED}/truth.json", "w") as f:
        json.dump(truth, f, indent=1)
    print(f"wrote 8 artifacts + sealed truth ({SEALED}/truth.json)")


if __name__ == "__main__":
    main()
