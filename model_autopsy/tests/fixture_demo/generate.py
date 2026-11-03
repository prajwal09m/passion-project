"""Flagship demo fixture: unseen ranking project (not in M9/M10).

A catalog ranker whose 'prime' slice is systematically
under-served while scores run slightly hot overall. Neither the
single baseline nor the team has seen this artifact or brief.
"""
import csv
import math
import random

rng = random.Random(20261201)
rows = []
for i in range(900):
    sl = rng.choice(["prime", "standard", "archive"])
    rel = rng.betavariate(2, 2)
    if sl == "prime":
        # Under-served slice: ranking nearly inverted (real defect).
        pred = 1.0 - 0.55 * rel + rng.gauss(0, 0.05)
    else:
        pred = 0.55 * rel + 0.25 + rng.gauss(0, 0.05)
    pred = min(0.99, max(0.01, pred + 0.04))  # slightly hot
    rows.append((sl, round(rel, 3), round(pred, 4)))

with open("model_autopsy/tests/fixture_demo/flagship_rank.csv",
          "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["slice", "relevance", "score"])
    w.writerows(rows)
print(f"wrote {len(rows)} rows")
