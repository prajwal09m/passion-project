# Demand Zone AI — Autonomy Study

A retrospective case study of AI-assisted development of a machine-learning system for short-horizon equity prediction: how a rule-based demand-zone detector evolved through multiple model versions into an ablation study, what its metrics do and do not show, and where the evidence ends.

**Main paper:** [`study_files/Demand_Zone_AI_Autonomy_Study.docx`](study_files/Demand_Zone_AI_Autonomy_Study.docx) · Companion draft: [`study_files/DEMAND_ZONE_AI_RESEARCH_DRAFT.md`](study_files/DEMAND_ZONE_AI_RESEARCH_DRAFT.md)

## What is in this repository

Everything lives under [`study_files/`](study_files/) — a curated public release indexed by [`study_files/research/demand-zone-ai-study/README.md`](study_files/research/demand-zone-ai-study/README.md).

| Path | Contents |
|---|---|
| `study_files/Demand_Zone_AI_Autonomy_Study.docx` | The research paper |
| `study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json` | Frozen v1.0.2 protocol (not yet executed) |
| `study_files/outputs/study_v1/models/` | **8 fitted model binaries** (`LightGBM_A–D.joblib`, `LogisticRegression_A–D.joblib`) |
| `study_files/outputs/study_v1/development/` | Retained `event_table.csv` (61,045 candidate events) and `oof_predictions.csv` (41,221 out-of-fold score rows) |
| `study_files/Python/`, `study_files/backend/` | Pipeline, dataset, and training source code, plus the 22-test suite for the v1.0.2 reconstruction |
| `study_files/outputs/study_v1_archive_audit_closeout.md` | Read-only archive audit: 153 source-CSV hashes, 2 table hashes, 8 model hashes verified |
| `study_files/research/demand-zone-ai-study/` | `bundle_manifest.json` (SHA-256 inventory of this release) and `run_manifest_sanitized.json` (v1.0.1 run manifest, machine paths removed) |
| `study_files/models/`, `study_files/outputs/` | Development-history metadata (v2–v7) and reports |

## Headline results (archived v1.0.1, retrospective)

The frozen protocol compares fixed Logistic Regression and LightGBM across four nested feature arms (A: baseline 20 features → D: 99 with order blocks) on identical point-in-time demand-zone retest events, with chronological 2023–2025 validation folds.

| Contrast (pooled OOF Δ AUC) | Recalculated from saved scores | Archived 95% interval |
|---|---:|---:|
| LightGBM A − Logistic Regression A | **+0.081757** | [0.065751, 0.099027] |
| LightGBM C − LightGBM B | **+0.005688** | [0.002179, 0.009191] |

The archived bootstrap interval bounds are report values, not independently reproduced. See the manuscript and [`study_files/outputs/study_v1_archive_audit_closeout.md`](study_files/outputs/study_v1_archive_audit_closeout.md) for the full evidence boundary.

## Verify it yourself

**1. Artifact integrity** — every file in the release is hashed in `bundle_manifest.json`:

```bash
cd study_files
python research/demand-zone-ai-study/create_bundle_manifest.py  # regenerate and diff
```

The eight model hashes also cross-check against `model_artifacts_sha256` in [`study_files/research/demand-zone-ai-study/run_manifest_sanitized.json`](study_files/research/demand-zone-ai-study/run_manifest_sanitized.json).

**2. Recompute the paper's AUC contrasts** from the published out-of-fold predictions:

```python
import pandas as pd
from sklearn.metrics import roc_auc_score

df = pd.read_csv("study_files/outputs/study_v1/development/oof_predictions.csv")
a  = roc_auc_score(df["label"], df["LightGBM_A"])
lr = roc_auc_score(df["label"], df["LogisticRegression_A"])
c  = roc_auc_score(df["label"], df["LightGBM_C"])
b  = roc_auc_score(df["label"], df["LightGBM_B"])
print("LightGBM A − Logistic A:", round(a - lr, 6))   # +0.081757
print("LightGBM C − LightGBM B:", round(c - b, 6))    # +0.005688
```

**3. Load a trained model** (requires `lightgbm`, `scikit-learn`, `joblib`):

```python
import joblib
model = joblib.load("study_files/outputs/study_v1/models/LightGBM_C.joblib")
```

## Environment

Original v1.0.1 runtime: Python 3.13.1, numpy 2.3.3, pandas 2.3.3, scikit-learn 1.9.0, lightgbm 4.7.0, joblib 1.5.3.

```bash
pip install -r study_files/requirements.txt
```

## What is intentionally not included

- The 153 raw OHLCV source CSVs (Yahoo-derived; redistribution rights unconfirmed — see the [release README](study_files/research/demand-zone-ai-study/README.md))
- The V2/V3/V5 row-level datasets
- The unsanitized original run manifest (contained machine-specific paths)
- The original v1.0.1 training source (never recovered; feature parity with the reconstruction failed)

## Status and integrity boundary

- The v1.0.2 protocol is **frozen but not executed**; all reported results are retrospective v1.0.1 archive values on dates already used in development.
- There are **zero prospective predictions and zero prospective outcomes** in this project.
- Historical source recovery is closed as unavailable under the approved Plan B closeout.
- This is an educational research project, **not investment advice**. AUC differences do not establish profitability or future performance.
