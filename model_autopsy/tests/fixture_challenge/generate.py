"""Generate 4 extra challenge fixtures (deterministic, seed 11).

ranking_search: pooled NDCG-lookalike fine, slice P@10 gap >= 0.2.
pipeline_insurance: train/infer scaling mismatch (raw vs standardized).
multi_clinic: leak column + subgroup failure interacting.
clean_weather: healthy regression, no injected weakness.
Ground truth sealed in ground_truth_challenge.json (tests only).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
rng = np.random.default_rng(11)


def ranking() -> None:
    rows = []
    for qi in range(200):
        sl = "head" if qi % 2 == 0 else "tail"
        for _ in range(10):
            rel = int(rng.random() < (0.55 if sl == "head" else 0.12))
            score = np.clip(rel * 0.6 + rng.normal(0.35, 0.2), 0.01, 0.99)
            rows.append({"query": qi, "slice": sl, "relevance": rel,
                         "score": round(float(score), 4)})
    pd.DataFrame(rows).to_csv(HERE / "ranking_search.csv", index=False)


def pipeline() -> None:
    n = 1200
    age = rng.integers(20, 80, n)
    bmi = rng.normal(26, 4, n)
    # model trained on STANDARDIZED bmi but served RAW bmi -> bias grows w/ bmi
    z = (bmi - 26) / 4
    target = 200 + 3 * age + 25 * z + rng.normal(0, 8, n)
    pred = 200 + 3 * age + 25 * bmi + rng.normal(0, 8, n)  # raw misuse
    split = np.where(np.arange(n) < 900, "train", "test")
    pd.DataFrame({"age": age, "bmi": np.round(bmi, 2),
                  "target": np.round(target, 1),
                  "prediction": np.round(pred, 1),
                  "split": split}).to_csv(
        HERE / "pipeline_insurance.csv", index=False)


def multi() -> None:
    n = 2000
    age = rng.integers(20, 90, n)
    ward = np.where(rng.random(n) < 0.3, "north", "south")
    logit = -2.5 + 0.03 * age + np.where(ward == "north", 1.2, -0.6)
    label = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    leak = np.where(rng.random(n) < 0.04, 1 - label, label)
    # north gets good scores, south gets near-random (subgroup failure)
    base = np.where(ward == "north",
                    0.15 + 0.7 * label, 0.5 + rng.normal(0, 0.05, n))
    score = np.clip(base + rng.normal(0, 0.08, n), 0.01, 0.99)
    pd.DataFrame({"age": age, "ward": ward, "leak_flag": leak,
                  "score": np.round(score, 4), "label": label}).to_csv(
        HERE / "multi_clinic.csv", index=False)


def clean() -> None:
    n = 1000
    temp = rng.normal(20, 8, n)
    target = 50 + 2 * temp + rng.normal(0, 3, n)
    pred = target + rng.normal(0, 3, n)
    pd.DataFrame({"temp": np.round(temp, 2),
                  "target": np.round(target, 2),
                  "prediction": np.round(pred, 2)}).to_csv(
        HERE / "clean_weather.csv", index=False)


def main() -> None:
    ranking(); pipeline(); multi(); clean()
    truth = {
        "ranking_search": {
            "injected": "tail-slice relevance collapse hidden by pooled mean",
            "slice_gap_min": 0.2},
        "pipeline_insurance": {
            "injected": "train/infer scaling mismatch on bmi "
                        "(standardized vs raw)",
            "expect": "large systematic bias, residual correlates with bmi"},
        "multi_clinic": {
            "injected": "leak_flag mirrors label AND south ward "
                        "predictions near-random (interacting)",
            "leak_column": "leak_flag", "weak_slice": "south"},
        "clean_weather": {
            "injected": "none: healthy regression control",
            "expect": "no breach; null conclusion"},
    }
    (HERE / "ground_truth_challenge.json").write_text(
        json.dumps(truth, indent=2))
    for f in ("ranking_search.csv", "pipeline_insurance.csv",
              "multi_clinic.csv", "clean_weather.csv"):
        print(f, (HERE / f).stat().st_size, "bytes")


if __name__ == "__main__":
    main()
