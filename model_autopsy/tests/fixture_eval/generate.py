"""Milestone 4 evaluation fixtures (deterministic, seed 23).

Eight UNFAMILIAR projects, distinct from Milestone 3 scenarios in story,
domain, columns, and planted mechanisms. Column/filenames are neutral:
functional names (label/score/target/prediction/date/split/slice) are
the diagnostic interface, never hints; no mechanism words appear in the
investigator environment (enforced by the leakage-audit test).

Layout written by this script:
  investigator/   data CSVs + briefs.json (the ONLY thing the
                  investigator may read)
  ground_truth_eval.json  sealed (tests/scorer only; investigator path
                  resolution can never reach it)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
INV = HERE / "investigator"
rng = np.random.default_rng(23)


def credit() -> None:
    """Tabular classification: conditional subgroup failure + legitimate
    strong-but-below-threshold distractor (tests no-false-leak)."""
    n = 1500
    age = rng.integers(20, 75, n)
    income = rng.normal(55, 18, n).round(1)
    tenure = rng.integers(0, 20, n)
    region = np.where(rng.random(n) < 0.25, "W", np.random.choice(
        ["N", "E", "S"], n))
    delinq = rng.poisson(1.2, n)
    logit = (-1.8 + 0.02 * (age - 40) - 0.03 * (income - 55)
             + 0.9 * delinq + rng.normal(0, 0.4, n))
    label = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    good = 0.12 + 0.72 * label + rng.normal(0, 0.10, n)
    score = np.where(region == "W",
                     0.5 + rng.normal(0, 0.06, n), good)
    score = np.clip(score, 0.01, 0.99)
    pd.DataFrame({"age": age, "income": income, "tenure": tenure,
                  "region": region, "delinq": delinq,
                  "score": score.round(4), "label": label}
                 ).to_csv(INV / "credit_default.csv", index=False)


def rent() -> None:
    """Regression, multi-stage flavor: one district silently falls back
    to a base estimate (stale category code after a schema change)."""
    n = 1200
    area = rng.integers(30, 200, n)
    rooms = rng.integers(1, 6, n)
    district = np.random.choice(["A", "B", "C"], n, p=[0.4, 0.4, 0.2])
    target = 800 + 12 * area + 200 * rooms + rng.normal(0, 120, n)
    pred = target + rng.normal(0, 120, n)
    pred = np.where(district == "C",
                    800 + 12 * area + rng.normal(0, 120, n), pred)
    pd.DataFrame({"area": area, "rooms": rooms, "district": district,
                  "target": target.round(0),
                  "prediction": pred.round(0)}
                 ).to_csv(INV / "rent_estimates.csv", index=False)


def turbine() -> None:
    """Forecasting: mid-series level shift the model misses; splits are
    clean and chronological (tests drift-without-leakage reasoning)."""
    n = 730
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    base = 200 + 40 * np.sin(2 * np.pi * np.arange(n) / 365)
    shift = np.where(np.arange(n) >= 500, 35, 0)  # recalibration step
    target = base + shift + rng.normal(0, 6, n)
    pred = base + rng.normal(0, 6, n)
    split = np.where(np.arange(n) < 500, "train", "test")
    pd.DataFrame({"date": dates.strftime("%Y-%m-%d"),
                  "target": target.round(2),
                  "prediction": pred.round(2), "split": split}
                 ).to_csv(INV / "turbine_output.csv", index=False)


def docs() -> None:
    """Clustering: overlapping structure (no clean separation)."""
    n = 600
    a = rng.normal(0, 2.2, (n // 2, 2))
    b = rng.normal(1.2, 2.2, (n - n // 2, 2))
    pts = np.vstack([a, b])
    pd.DataFrame({"v1": pts[:, 0].round(3), "v2": pts[:, 1].round(3)}
                 ).to_csv(INV / "doc_vectors.csv", index=False)


def music() -> None:
    """Ranking: cold-start slice collapse under a healthy pooled mean."""
    rows = []
    for qi in range(220):
        sl = "new" if qi % 3 == 0 else "est"
        for _ in range(8):
            rel = int(rng.random() < (0.10 if sl == "new" else 0.50))
            score = np.clip(rel * 0.55 + rng.normal(0.35, 0.2),
                            0.01, 0.99)
            rows.append({"query": qi, "slice": sl, "relevance": rel,
                         "score": round(float(score), 4)})
    pd.DataFrame(rows).to_csv(INV / "music_rank.csv", index=False)


def claim() -> None:
    """Multi-stage pipeline: a lagged input makes error grow with that
    input (staleness), while the pooled headline metric looks routine.
    A second concern (threshold choice) is documented as untestable with
    current evidence -> partial-discovery territory."""
    n = 1500
    amount = rng.normal(900, 250, n).round(0)
    velocity = rng.poisson(3, n)
    device_age = rng.integers(0, 60, n)
    target = 100 + 0.4 * amount + 25 * velocity + rng.normal(0, 20, n)
    pred = (target + 4.5 * device_age + rng.normal(0, 20, n))
    pd.DataFrame({"amount": amount, "velocity": velocity,
                  "device_age": device_age,
                  "target": target.round(1),
                  "prediction": pred.round(1)}
                 ).to_csv(INV / "claim_severity.csv", index=False)


def wellness() -> None:
    """Clean control: healthy regression, nothing planted."""
    n = 800
    steps = rng.normal(7000, 2500, n)
    target = 60 + 0.002 * steps + rng.normal(0, 3, n)
    pred = target + rng.normal(0, 3, n)
    pd.DataFrame({"steps": steps.round(0), "target": target.round(1),
                  "prediction": pred.round(1)}
                 ).to_csv(INV / "wellness_index.csv", index=False)


def pilot() -> None:
    """Weak-evidence case: small n, modest hints, NO planted failure.
    Correct outcome: inconclusive / more-evidence-required, not a
    fabricated finding."""
    n = 120
    age = rng.integers(20, 80, n)
    x = rng.normal(0, 1, n)
    label = (rng.random(n) < 1 / (1 + np.exp(-(0.5 * x)))).astype(int)
    score = np.clip(0.3 + 0.35 * label + rng.normal(0, 0.18, n),
                    0.01, 0.99)
    pd.DataFrame({"age": age, "x": x.round(3),
                  "score": score.round(4), "label": label}
                 ).to_csv(INV / "pilot_study.csv", index=False)


BRIEFS = {
    "eval_credit": ("Card-default scores look uneven across regions; "
                    "find what is wrong and show the evidence."),
    "eval_rent": ("Rent estimates for one district look off after a "
                  "schema update; find what is wrong and show evidence."),
    "eval_turbine": ("Output forecasts miss a recent level change; "
                     "find what is wrong and show the evidence."),
    "eval_docs": ("Are these document groups stable and separated?"),
    "eval_music": ("Are top results relevant for every catalog slice?"),
    "eval_claim": ("Severity estimates look systematically off since a "
                   "pipeline change; find what is wrong and show evidence."),
    "eval_wellness": ("Routine check: is the wellness index model healthy?"),
    "eval_pilot": ("Small pilot readout: is there a material issue, or is "
                   "more evidence required?"),
}


def main() -> None:
    INV.mkdir(parents=True, exist_ok=True)
    credit(); rent(); turbine(); docs(); music(); claim(); wellness(); pilot()
    (INV / "briefs.json").write_text(json.dumps(BRIEFS, indent=2))
    truth = {
        "eval_credit": {
            "failure": True,
            "mechanism": "conditional subgroup failure: region W "
                         "predictions near-random while pooled AUC looks fine",
            "expect_verdict": "correct",
            "distractors": ["delinq correlates with label (~0.55) but is a "
                            "legitimate driver, not a leak; claiming leakage "
                            "is a false positive"],
            "forbidden_tokens": ["distractor", "W fails", "near-random W",
                                 "conditional subgroup"]},
        "eval_rent": {
            "failure": True,
            "mechanism": "stale category code: district C silently falls "
                         "back to a base estimate missing the rooms effect",
            "expect_verdict": "correct",
            "distractors": [],
            "forbidden_tokens": ["stale category", "falls back",
                                 "base estimate"]},
        "eval_turbine": {
            "failure": True,
            "mechanism": "missed level shift at day 500; splits are clean "
                         "and chronological (no leakage)",
            "expect_verdict": "correct",
            "distractors": ["overlapping splits would be the wrong "
                            "explanation; claiming leakage is a false "
                            "positive"],
            "forbidden_tokens": ["recalibration", "level shift",
                                 "day 500", "no leakage"]},
        "eval_docs": {
            "failure": True,
            "mechanism": "overlapping structure: no stable separation",
            "expect_verdict": "correct",
            "distractors": [],
            "forbidden_tokens": ["overlapping structure"]},
        "eval_music": {
            "failure": True,
            "mechanism": "cold-start collapse: new-item slice P@K far "
                         "below established items under a healthy pooled mean",
            "expect_verdict": "correct",
            "distractors": [],
            "forbidden_tokens": ["cold-start", "cold start"]},
        "eval_claim": {
            "failure": True,
            "mechanism": "lagged input: error grows with device_age "
                         "(staleness); threshold-choice concern is "
                         "documented but untestable here",
            "expect_verdict": "partial",
            "distractors": ["confirming only the bias without the "
                            "input-dependence is symptom-level (partial)"],
            "forbidden_tokens": ["lagged input", "staleness",
                                 "device_age grows"]},
        "eval_wellness": {
            "failure": False,
            "mechanism": "none: healthy control",
            "expect_verdict": "correct-null",
            "distractors": [],
            "forbidden_tokens": []},
        "eval_pilot": {
            "failure": False,
            "mechanism": "none planted: hints are weak at n=120; correct "
                         "outcome is inconclusive / more-evidence-required",
            "expect_verdict": "inconclusive-handled",
            "distractors": ["any confirmed failure here is a false positive"],
            "forbidden_tokens": []},
    }
    (HERE / "ground_truth_eval.json").write_text(
        json.dumps(truth, indent=2))
    for f in sorted(INV.glob("*.csv")):
        print(f.name, f.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
