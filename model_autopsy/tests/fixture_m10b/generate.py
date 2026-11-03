"""M13 second held-out corpus (offline, deterministic).

Six scenarios with DIFFERENT structures from fixture_m10 (new
column names, shapes, mechanism combinations). Sealed truth lives
in _sealed/truth.json; the investigator sees briefs + artifacts
only (see backend/m10/scenarios_b.py).
"""
import csv
import math
import random

OUT = "model_autopsy/tests/fixture_m10b"
SEALED = OUT + "/_sealed"


def region_gap(rng):
    rows = []
    for i in range(1200):
        region = rng.choice(["alpha", "beta", "gamma"])
        x = rng.gauss(0, 1)
        logit = 0.9 * x + (0.0 if region != "gamma" else -1.3)
        p = 1 / (1 + math.exp(-logit))
        rows.append((region, round(x, 3), 1 if rng.random() < p else 0,
                     round(1 / (1 + math.exp(-0.9 * x)), 4)))
    _w("b_region_gap.csv", ["region", "feat", "target", "pred"], rows)


def score_inflate(rng):
    rows = []
    for i in range(1000):
        x = rng.gauss(0, 1)
        p = 1 / (1 + math.exp(-x))
        rows.append((round(x, 3), 1 if rng.random() < p else 0,
                     round(min(0.99, p + 0.22), 4)))
    _w("b_score_inflate.csv", ["x", "target", "pred"], rows)


def gradual_drift(rng):
    rows = []
    for i in range(280):
        day = f"2025-{i // 28 + 1:02d}-{(i % 28) + 1:02d}"
        target = 80 + i * 0.12 + rng.gauss(0, 1.2)
        pred = 80 + (i - 4) * 0.12 + rng.gauss(0, 0.5)
        rows.append((day, round(target, 2), round(pred, 2),
                     "train" if i < 140 else "test"))
    _w("b_gradual_drift.csv",
        ["day", "target", "pred", "fold"], rows)


def unit_shift(rng):
    rows = []
    for i in range(900):
        zone = rng.choice(["north", "south"])
        size = rng.uniform(20, 90)
        true = 1.5 * size + rng.gauss(0, 12)
        pred = 1.5 * (size * (0.2 if zone == "south" else 1.0))
        pred += rng.gauss(0, 3)
        rows.append((zone, round(size, 1), round(true, 1),
                     round(pred, 1)))
    _w("b_unit_shift.csv", ["zone", "sqft", "target", "prediction"], rows)


def steady_b(rng):
    rows = []
    for i in range(800):
        x = rng.gauss(0, 1)
        y = 1 if x + rng.gauss(0, 0.8) > 0 else 0
        rows.append((round(x, 3), y,
                     round(1 / (1 + math.exp(-x)), 4)))
    _w("b_steady.csv", ["x", "target", "pred"], rows)


def thin_b(rng):
    rows = []
    for i in range(45):
        x = rng.gauss(0, 1)
        rows.append((round(x, 3), 1 if x > 0 else 0,
                     round(1 / (1 + math.exp(-x)), 4)))
    _w("b_thin.csv", ["x", "target", "pred"], rows)


def _w(path, header, rows):
    with open(f"{OUT}/{path}", "w", newline="") as f:
        csv.writer(f).writerows([header, *rows])


def main():
    import json
    import os
    rng = random.Random(20261202)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(SEALED, exist_ok=True)
    region_gap(rng)
    score_inflate(rng)
    gradual_drift(rng)
    unit_shift(rng)
    steady_b(rng)
    thin_b(rng)
    truth = {
        "b_region_gap": {"mechanism": "gamma-region degradation",
                         "family": "subgroup", "grade": "discovered",
                         "key_tool": "classification_metrics"},
        "b_score_inflate": {"mechanism": "systematic over-scoring",
                            "family": "calibration", "grade": "discovered",
                            "key_tool": "calibration_and_error_analysis"},
        "b_gradual_drift": {"mechanism": "gradual slope drift (lagging "
                                         "predictions)",
                            "family": "drift", "grade": "partial",
                            "key_tool": "residual_time_analysis"},
        "b_unit_shift": {"mechanism": "south-zone unit inconsistency",
                         "family": "subgroup", "grade": "discovered",
                         "key_tool": "regression_metrics"},
        "b_steady": {"mechanism": "none (healthy)",
                     "family": "clean", "grade": "correct-null",
                     "key_tool": "none"},
        "b_thin": {"mechanism": "unknown (n too small)",
                   "family": "thin", "grade": "inconclusive",
                   "key_tool": "none"},
    }
    with open(f"{SEALED}/truth.json", "w") as f:
        json.dump(truth, f, indent=1)
    print(f"wrote 6 artifacts + sealed truth ({SEALED}/truth.json)")


if __name__ == "__main__":
    main()
