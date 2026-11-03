"""M15 fourth corpus: null, unidentifiable, combined, confounded.

Missing-data-tolerant generator; sealed truth in
_sealed/truth.json. Correct outcomes: verified null,
inconclusive (insufficient evidence), discovered, discovered.
"""
import csv
import math
import random

OUT = "model_autopsy/tests/fixture_m10d"
SEALED = OUT + "/_sealed"


def _w(path, header, rows):
    with open(f"{OUT}/{path}", "w", newline="") as f:
        csv.writer(f).writerows([header, *rows])


def null_d(rng):
    rows = []
    for i in range(900):
        x = rng.gauss(0, 1)
        y = 1 if x + rng.gauss(0, 0.8) > 0 else 0
        rows.append((round(x, 3), y,
                     round(1 / (1 + math.exp(-x)), 4)))
    _w("d_null.csv", ["x", "label", "score"], rows)


def thin_d(rng):
    rows = []
    for i in range(38):
        x = rng.gauss(0, 1)
        rows.append((round(x, 3), 1 if x > 0 else 0,
                     round(1 / (1 + math.exp(-x)), 4)))
    _w("d_thin.csv", ["x", "label", "score"], rows)


def combined_d(rng):
    rows = []
    for i in range(1100):
        site = rng.choice(["a", "b"])
        z = rng.gauss(0, 1)
        p = 1 / (1 + math.exp(-z))
        label = 1 if rng.random() < p else 0
        score = min(0.99, p + (0.18 if site == "b" else 0))
        rows.append((site, round(z, 3), label, round(score, 4)))
    _w("d_combined.csv", ["site", "feat", "label", "score"], rows)


def confounded_d(rng):
    rows = []
    for i in range(1000):
        zone = rng.choice(["n", "s"])
        size = rng.uniform(20, 90) + (15 if zone == "s" else 0)
        true = 1.5 * size + rng.gauss(0, 12)
        pred = 1.5 * size + rng.gauss(0, 3)
        rows.append((zone, round(size, 1), round(true, 1),
                     round(pred, 1)))
    _w("d_confounded.csv", ["zone", "sqft", "target", "prediction"],
       rows)


def main():
    import json
    import os
    rng = random.Random(20270417)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(SEALED, exist_ok=True)
    null_d(rng)
    thin_d(rng)
    combined_d(rng)
    confounded_d(rng)
    truth = {
        "d_null": {"mechanism": "none (healthy)", "family": "clean",
                   "grade": "correct-null", "key_tool": "none"},
        "d_thin": {"mechanism": "unknown (n too small)",
                   "family": "thin", "grade": "inconclusive",
                   "key_tool": "none"},
        "d_combined": {"mechanism": "site-b over-scoring plus "
                                    "prevalence shift",
                       "family": "subgroup", "grade": "discovered",
                       "key_tool": "classification_metrics"},
        "d_confounded": {"mechanism": "south-zone size mix explains "
                                      "the error gap (confounded)",
                         "family": "subgroup", "grade": "discovered",
                         "key_tool": "regression_metrics"},
    }
    with open(f"{SEALED}/truth.json", "w") as f:
        json.dump(truth, f, indent=1)
    print(f"wrote 4 artifacts + sealed truth ({SEALED}/truth.json)")


if __name__ == "__main__":
    main()
