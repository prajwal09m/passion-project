"""Generate deterministic synthetic fixtures (seed 7) + ground truth.

Run once: `py -3 generate.py` from this directory. Outputs are committed
fixtures; the validation suite treats them as fixed external data.
Ground truth lives in ground_truth.json, which triage code must never read.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
rng = np.random.default_rng(7)
N = {"clinic": 2000, "houses": 1500, "energy": 730, "customers": 600}


def clinic() -> None:
    n = N["clinic"]
    age = rng.integers(20, 90, n)
    bmi = rng.normal(27, 5, n).round(1)
    bp = rng.normal(120, 15, n).round(0)
    prior = rng.poisson(1.5, n)
    logit = -3 + 0.03 * age + 0.05 * bmi + 0.4 * prior
    p = 1 / (1 + np.exp(-logit))
    label = (rng.random(n) < p).astype(int)
    leak = np.where(rng.random(n) < 0.05, 1 - label, label)  # injected leak
    score = np.clip(0.15 + 0.7 * label + rng.normal(0, 0.12, n), 0.01, 0.99)
    pd.DataFrame({"age": age, "bmi": bmi, "bp": bp, "prior_visits": prior,
                  "leak_flag": leak, "score": score.round(4),
                  "label": label}).to_csv(HERE / "clinic_readmit.csv", index=False)


def houses() -> None:
    n = N["houses"]
    sqft = rng.integers(600, 3500, n)
    beds = rng.integers(1, 6, n)
    seg = np.where(rng.random(n) < 0.4, "urban", "rural")
    price = 50000 + 120 * sqft + 15000 * beds + rng.normal(0, 15000, n)
    pred = price + np.where(seg == "urban", 20000, 0) + rng.normal(0, 5000, n)
    pd.DataFrame({"sqft": sqft, "beds": beds, "segment": seg,
                  "target": price.round(0), "prediction": pred.round(0)}
                 ).to_csv(HERE / "house_prices.csv", index=False)


def energy() -> None:
    n = N["energy"]
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    seasonal = 100 + 30 * np.sin(2 * np.pi * np.arange(n) / 365)
    trend = np.linspace(0, 25, n)  # injected drift
    target = seasonal + trend + rng.normal(0, 5, n)
    pred = seasonal + rng.normal(0, 5, n)  # model misses the drift
    split = np.where(np.arange(n) < 500, "train", "test")
    split[:530] = "train"  # injected 30-day overlap
    horizon = (np.arange(n) % 7) + 1
    pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "target": target.round(2),
                  "prediction": pred.round(2), "split": split,
                  "horizon": horizon}).to_csv(HERE / "energy_demand.csv", index=False)


def customers() -> None:
    n = N["customers"]
    centers = np.array([[0, 0], [8, 8], [0, 10]])
    which = rng.integers(0, 3, n)
    pts = centers[which] + rng.normal(0, 0.9, (n, 2))
    noise = rng.normal(0, 1, (n, 2))
    pd.DataFrame({"x1": pts[:, 0].round(3), "x2": pts[:, 1].round(3),
                  "n1": noise[:, 0].round(3), "n2": noise[:, 1].round(3)}
                 ).to_csv(HERE / "customers.csv", index=False)


def blackbox() -> None:
    df = pd.read_csv(HERE / "clinic_readmit.csv")
    df[["score", "label"]].to_csv(HERE / "blackbox_only.csv", index=False)


def main() -> None:
    clinic(); houses(); energy(); customers(); blackbox()
    truth = {
        "clinic_readmit": {"injected": "leak_flag mirrors label (5% flip)",
                           "leak_column": "leak_flag"},
        "house_prices": {"injected": "+20000 systematic bias on urban segment",
                         "biased_group": "urban", "bias_magnitude": 20000},
        "energy_demand": {"injected": "30-day train/test overlap + upward drift "
                                      "the model misses",
                          "overlap_days": 30},
        "customers": {"injected": "none: 3 well-separated blobs (control)",
                      "min_silhouette": 0.5},
        "blackbox_only": {"injected": "predictions+labels only; leakage "
                                      "confirmation impossible",
                          "possible": ["error_analysis", "calibration"],
                          "impossible": ["leakage_confirmation"]}}
    (HERE / "ground_truth.json").write_text(json.dumps(truth, indent=2))
    for f in ("clinic_readmit.csv", "house_prices.csv", "energy_demand.csv",
              "customers.csv", "blackbox_only.csv"):
        print(f, (HERE / f).stat().st_size, "bytes")


if __name__ == "__main__":
    main()
