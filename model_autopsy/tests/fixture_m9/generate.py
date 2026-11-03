"""Deterministic generator for the M9 neural image-tag fixture.

Planted structure (sealed truth lives in eval/m9_challenge.py, never
here): night-slice ranking near-random while day is excellent, pooled
AUC misleadingly high, overconfident scores at night, and different
label prevalence per slice (the confounder: prevalence cannot explain
an AUC gap, since AUC is prevalence-independent).
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(20260509)
n = 600
day_label = (rng.random(n) < 0.5).astype(int)
day_score = np.clip(day_label * 0.9 + rng.normal(0, 0.08, n), 0.01, 0.99)
night_label = (rng.random(n) < 0.3).astype(int)
night_score = np.clip(0.55 + night_label * 0.15 + rng.normal(0, 0.25, n),
                       0.01, 0.99)
df = pd.DataFrame({
    "image_id": [f"img_{i:04d}" for i in range(2 * n)],
    "slice": ["day"] * n + ["night"] * n,
    "brightness": np.round(np.concatenate(
        [rng.normal(0.7, 0.1, n), rng.normal(0.25, 0.1, n)]), 3),
    "score": np.round(np.concatenate([day_score, night_score]), 4),
    "label": np.concatenate([day_label, night_label]).astype(int),
})
df.to_csv("model_autopsy/tests/fixture_m9/nn_tags.csv", index=False)
print(df.groupby("slice")["label"].mean().to_dict())
