"""Stable forecast fixture for the M7 double-contradiction test.

A well-behaved forecaster: independent Gaussian draw each row around
a constant mean, chronological train/test split with no shared dates.
Both drift probes fire their *contradicts* rules here (see the M7
test for the exact numeric gates).

Generated once, frozen. Do NOT regenerate casually: the M7 test pins
exact linker behavior on these values.
"""
import csv
import random

PATH = "model_autopsy/tests/fixture_eval/investigator/stable_output.csv"

rng = random.Random(20261101)
rows = [("date", "target", "prediction", "split")]
base = 100.0
for i in range(240):
    day = f"2023-{i // 28 + 1:02d}-{(i % 28) + 1:02d}"
    target = base + rng.gauss(0, 1.5)
    prediction = target + rng.gauss(0, 1.0)
    split = "train" if i < 120 else "test"
    rows.append((day, f"{target:.2f}", f"{prediction:.2f}", split))

with open(PATH, "w", newline="") as f:
    csv.writer(f).writerows(rows)
print(f"wrote {len(rows) - 1} rows to {PATH}")
