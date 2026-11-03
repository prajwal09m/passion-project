"""M14 third held-out corpus (offline, deterministic).

Six scenarios with structures unlike corpus A/B (new names:
county, sensor, machine). Includes interaction, robustness,
novel-saturation, combined, clean, thin cases. Sealed truth lives
in _sealed/truth.json; investigator sees briefs + artifacts only.
"""
import csv
import math
import random

OUT = "model_autopsy/tests/fixture_m10c"
SEALED = OUT + "/_sealed"


def _w(path, header, rows):
    with open(f"{OUT}/{path}", "w", newline="") as f:
        csv.writer(f).writerows([header, *rows])


def interaction(rng):
    rows = []
    for i in range(1000):
        county = rng.choice(["north", "south", "east"])
        load = rng.uniform(0, 10)
        temp = rng.uniform(-5, 35)
        # failure only when high load AND high temp in south
        bad = county == "south" and load > 6 and temp > 25
        target = 3 * load + 0.5 * temp + rng.gauss(0, 1)
        pred = target - (8 if bad else 0) + rng.gauss(0, 0.3)
        rows.append((county, round(load, 2), round(temp, 2),
                     round(target, 2), round(pred, 2)))
    _w("c_interaction.csv",
       ["county", "load", "temp", "target", "prediction"], rows)


def robustness(rng):
    rows = []
    for i in range(800):
        machine = rng.choice(["m1", "m2"])
        v = rng.uniform(10, 100)
        target = 2 * v + rng.gauss(0, 2)
        # m2 sensor reports kPa instead of Pa/1000 (scale fault)
        pred = 2 * (v * 10 if machine == "m2" else v)
        rows.append((machine, round(v, 2), round(target, 2),
                     round(pred, 2)))
    _w("c_robustness.csv", ["machine", "reading", "target",
                            "prediction"], rows)


def saturation(rng):
    rows = []
    for i in range(900):
        s = rng.uniform(0, 120)
        p = 1 / (1 + math.exp(-0.08 * (s - 50)))
        # sensor saturates above 100: scores cap, labels keep rising
        score = min(1 / (1 + math.exp(-0.08 * (s - 50))), 0.86)
        rows.append((round(s, 2), 1 if rng.random() < p else 0,
                     round(score, 4)))
    _w("c_saturation.csv", ["sensor", "label", "score"], rows)


def combined(rng):
    rows = []
    for i in range(1000):
        county = rng.choice(["west", "east"])
        z = rng.gauss(0, 1)
        base = 1 / (1 + math.exp(-z))
        label = 1 if rng.random() < base else 0
        score = min(0.99, base + (0.2 if county == "east" else 0))
        rows.append((county, round(z, 3), label, round(score, 4)))
    _w("c_combined.csv", ["county", "feat", "label", "score"], rows)


def steady(rng):
    rows = []
    for i in range(800):
        x = rng.gauss(0, 1)
        y = 1 if x + rng.gauss(0, 0.8) > 0 else 0
        rows.append((round(x, 3), y,
                     round(1 / (1 + math.exp(-x)), 4)))
    _w("c_steady.csv", ["x", "label", "score"], rows)


def thin(rng):
    rows = []
    for i in range(40):
        x = rng.gauss(0, 1)
        rows.append((round(x, 3), 1 if x > 0 else 0,
                     round(1 / (1 + math.exp(-x)), 4)))
    _w("c_thin.csv", ["x", "label", "score"], rows)


def main():
    import json
    import os
    rng = random.Random(20270301)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(SEALED, exist_ok=True)
    interaction(rng)
    robustness(rng)
    saturation(rng)
    combined(rng)
    steady(rng)
    thin(rng)
    truth = {
        "c_interaction": {
            "mechanism": "south-county high-load high-temp interaction",
            "family": "interaction", "grade": "discovered",
            "key_tool": "regression_metrics",
            "novel": True},
        "c_robustness": {
            "mechanism": "m2 unit scale fault (10x)",
            "family": "robustness", "grade": "discovered",
            "key_tool": "regression_metrics",
            "novel": False},
        "c_saturation": {
            "mechanism": "sensor saturation above 100",
            "family": "calibration", "grade": "discovered",
            "key_tool": "calibration_and_error_analysis",
            "novel": True},
        "c_combined": {
            "mechanism": "east-county over-scoring plus base-rate shift",
            "family": "subgroup", "grade": "discovered",
            "key_tool": "classification_metrics",
            "novel": False},
        "c_steady": {"mechanism": "none (healthy)",
                     "family": "clean", "grade": "correct-null",
                     "key_tool": "none", "novel": False},
        "c_thin": {"mechanism": "unknown (n too small)",
                   "family": "thin", "grade": "inconclusive",
                   "key_tool": "none", "novel": False},
    }
    with open(f"{SEALED}/truth.json", "w") as f:
        json.dump(truth, f, indent=1)
    print(f"wrote 6 artifacts + sealed truth ({SEALED}/truth.json)")


if __name__ == "__main__":
    main()
