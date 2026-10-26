# Research Input Requirements

This document is the authoritative inventory of artifacts required to reproduce the
existing stock research (v1.0.1 archive and the frozen v1.0.2 protocol) and the
V2–V10 historical lineage. Every row was verified against repository evidence
(source constants, tests, and manifests) — nothing here is guessed.

**Rules for restoring inputs (non-negotiable):**

1. Do not fabricate missing files or generate fake data to make tests pass.
2. Do not modify the scientific protocol (`study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json`).
3. Do not substitute look-alike datasets (see [Anti-requirements](#anti-requirements)).
4. Do not re-download market data with `yfinance` or any network tool. Restored
   data must come from the original local archive so hashes can match.
5. Never execute `Python/run_pipeline.py` or `Python/ml_demand_zone_trainer.py`
   (legacy, leakage-prone; they overwrite outputs).

Canonical paths below are resolved from `study_files/` because
`study_files/backend/demand_zone_study_v1.py` sets `ROOT = Path(__file__).resolve().parents[1]`.

---

## 1. Missing artifact summary

| # | Missing artifact | Expected location | Affects reproducibility | Required for v1.0.x reproduction |
|---|---|---|---|---|
| 1 | v1.0.1 run manifest | `study_files/outputs/study_v1/development/run_manifest.json` | Yes — archive unverifiable | Yes |
| 2 | V2 row-level dataset (roster source) | `study_files/outputs/v2/demand_zone_v2_dataset.csv` | Yes — no universe | Yes |
| 3 | Historical OHLCV cache (153 CSVs) | `study_files/outputs/v2/_ohlcv/` | Yes — no events/features | Yes |
| 4 | Original v1.0.1 study source | unrecovered; drop zone `study_files/research/demand-zone-ai-study/recovered_source/` | Yes — feature parity failed | Yes (exact reproduction) |
| 5 | v1.0.1 preprocessing / feature-parity evidence | same drop zone as #4 (parity check output) | Yes — archived metrics not attributable | Yes (exact reproduction) |
| 6 | V5 row-level dataset | `study_files/outputs/v5/demand_zone_v5_dataset.csv` | Yes for V5–V10 lineage | No |
| 7 | V13 dataset (lineage to rebuild V2) | `study_files/outputs/v13/demand_zone_ml_dataset_v13.csv` | Only if rebuilding V2 | No (restore #2 instead) |
| 8 | hold1 dataset (lineage to rebuild V2) | `study_files/outputs/hold1/demand_zone_hold1_dataset_v1.csv` | Only if rebuilding V2 | No (restore #2 instead) |
| 9 | Sealed prospective/holdout artifacts | `study_files/outputs/study_v1/prospective/` | Must remain **absent** | No (invariant, not an input) |

Two existing tests fail today solely because of #1 and #2; after restoration the
study suite should reach 22/22 passing without any test edits:

- `test_immutable_v1_0_1_archive_artifact_hashes_match_manifest` → needs #1.
- `test_mature_outcomes_accept_canonical_universe_hash` → needs #2
  (`study_files/backend/tests/test_demand_zone_study_v1.py:350` hashes
  `study.ROSTER_SOURCE`).

---

## 2. Artifact details

### 1. v1.0.1 run manifest

- **Expected location:** `study_files/outputs/study_v1/development/run_manifest.json`
- **Why required:** It is the integrity manifest of the immutable v1.0.1 archive.
  The test suite reads it to verify SHA-256 of `event_table.csv`,
  `oof_predictions.csv`, and all 8 fitted models
  (`test_demand_zone_study_v1.py:36-37`, `study.DEVELOPMENT_DIR / "run_manifest.json"`).
  It also records `protocol_sha256`, `code_sha256`, `test_suite_sha256`,
  `roster_source_sha256`, universe hash, source-data hashes, folds, and metrics.
- **Depends on it:** v1.0.1 archive verification; any future champion claim;
  the baseline reproduction comparison in `experiment_adapter.run_reproduction`.
- **Affects reproducibility:** Yes. Without it the archive cannot be verified and
  no baseline can be declared.
- **How the agent verifies presence:** File exists and parses as JSON;
  `protocol_version == "1.0.1"`; `protocol_sha256 == 486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07`;
  `code_sha256 == 29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b`;
  every `artifact_sha256` entry matches the sibling CSV; every
  `model_artifacts_sha256` entry matches `study_files/outputs/study_v1/models/*.joblib`.
  Implemented as `v1_run_manifest` in `experiment_adapter.verify_inputs()`.
- **Reference copy:** `study_files/research/demand-zone-ai-study/run_manifest_sanitized.json`
  exists and carries the same hash fields (machine-specific paths scrubbed,
  data/model files excluded). It is a reference only — the test reads the
  canonical path above. Do not edit the sanitized copy.

### 2. V2 row-level dataset (roster source)

- **Expected location:** `study_files/outputs/v2/demand_zone_v2_dataset.csv`
- **Why required:** This is `ROSTER_SOURCE`
  (`demand_zone_study_v1.py:45`). `load_roster()` reads its `ticker` column and
  asserts exactly **149** distinct tickers; the universe hash and the prospective
  lock depend on it. The frozen v1.0.2 protocol names it as `population.roster_source`
  (only tickers are used; legacy rows/labels/features are not).
- **Depends on it:** v1.0.2 frozen protocol execution; v1.0.1 manifest
  (`roster_source_sha256`); the failing test at
  `test_demand_zone_study_v1.py:350`.
- **Affects reproducibility:** Yes. No roster → no event universe → no study.
- **How the agent verifies presence:** File exists; `ticker` column parses to
  exactly 149 distinct values; SHA-256 equals
  `669ca1f5b21339b8cc26f6eb5cbeb22003ebafcd86b0d7e945f0db3d6517d71b`
  for exact v1.0.1 parity. Implemented as `v2_roster_dataset` in `verify_inputs()`.
- **Reported shape (for identification only):** V2 report describes 44,854 rows,
  149 tickers, signal dates 2021-08-03 → 2026-06-24.

### 3. Historical OHLCV cache (153 CSVs)

- **Expected location:** `study_files/outputs/v2/_ohlcv/` (`DATA_DIR`,
  `demand_zone_study_v1.py:46`)
- **Expected content:** 153 CSV files = 149 roster symbols + `SPY.csv`,
  `QQQ.csv`, `IWM.csv`, `XVIX.csv`. VIX is stored as `XVIX.csv`:
  `read_ohlcv()` maps `^` → `X` in filenames (`demand_zone_study_v1.py:233`),
  so `^VIX` resolves to `XVIX.csv`.
- **Expected columns:** `Date, Open, High, Low, Close, Volume` (column names are
  case-normalized on read). Cached history in the original archive ran through
  2026-08-03.
- **Why required:** Event construction, market/regime features, source-data
  hashes and prefix hashes in the run manifest, and the `audit` command all read
  this cache.
- **Depends on it:** v1.0.2 protocol `data` section; v1.0.1 manifest
  `source_data_sha256` / `source_data_prefix_sha256`; the study `audit` command.
- **Affects reproducibility:** Yes. Without it no event table can be rebuilt.
- **How the agent verifies presence:** Directory exists; ≥153 `*.csv`; the four
  benchmark files above exist; headers of those four contain the required
  columns; when #1 is restored, each file hash matches `source_data_sha256`.
  Implemented as `ohlcv_cache` in `verify_inputs()`.

### 4. Original v1.0.1 study source

- **Expected location:** **unrecovered.** No file in this checkout hashes to the
  manifest's `code_sha256`. Restored source must be dropped at
  `study_files/research/demand-zone-ai-study/recovered_source/` (single file or
  directory) so the agent can hash-match it.
- **Why required:** The v1.0.2 reconstruction
  (`study_files/backend/demand_zone_study_v1.py`) is explicitly **not** an exact
  restoration (its module docstring says so). The archive audit closeout
  (`study_files/outputs/study_v1_archive_audit_closeout.md`) records that feature
  parity **FAILED**: all 480 AAL rows differ on `rsi14`, `atr_pct`,
  `zone_width_pct`, and that the archived bootstrap intervals were not
  reproduced. Archived metrics therefore cannot be attributed or reproduced
  without the original code.
- **Depends on it:** v1.0.1 exact reproduction; champion `validation_status:
  REPRODUCED`.
- **Affects reproducibility:** Yes — this is the documented reason V1.0.1 is
  currently "unreproduced".
- **How the agent verifies presence:** SHA-256 of a file in the drop zone equals
  `29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b`.
  Implemented as `v1_0_1_source` in `verify_inputs()`. Then run the AAL parity
  comparison against `study_files/outputs/study_v1/development/event_table.csv`
  (all rows, columns `rsi14`, `atr_pct`, `zone_width_pct`).

### 5. v1.0.1 preprocessing / feature-parity evidence

- **Expected location:** accompanies #4 (definitions for `rsi14`, `atr_pct`,
  `zone_width_pct` and any imputation/scaling fit used in v1.0.1).
- **Why required:** The parity failure is a **feature-definition** mismatch, not
  just a code-copy problem. The v1.0.2 protocol fits imputation/scaling
  fold-locally (`estimators` pipeline note), so for v1.0.2 execution no separate
  preprocessing artifacts are needed — but v1.0.1 attribution requires the
  original definitions and fits.
- **Depends on it:** v1.0.1 exact reproduction and any claim comparing to
  archived metrics.
- **Affects reproducibility:** Yes for v1.0.1; not for a fresh v1.0.2 run.
- **How the agent verifies presence:** AAL parity check against the archived
  event table passes for the three differing columns (method recorded in
  `study_v1_archive_audit_closeout.md`). Until then `verify_inputs()` reports
  `feature_parity` as not established.

### 6. V5 row-level dataset

- **Expected location:** `study_files/outputs/v5/demand_zone_v5_dataset.csv`
  (`build_v5_dataset.py:27`, consumed by `train_v5.py` and `train_v7.py`)
- **Why required:** It is the row-level dataset for the V5–V10 historical
  lineage (sector-ETF returns, VIX z-scores, zone geometry, gap features,
  magnitude targets). `autonomous_agent/core.py` accepts it as an alternative
  source dataset in readiness checks.
- **Depends on it:** V5, V6(?), V7 training records; nothing in v1.0.x.
- **Affects reproducibility:** Yes for V5–V10 lineage (whose metrics are not
  comparable to v1.0.x anyway). No for the frozen protocol.
- **How the agent verifies presence:** File exists, non-empty, header includes
  `ticker` and `date`-like columns. Implemented as `v5_dataset` in `verify_inputs()`.

### 7–8. V13 and hold1 lineage datasets (only to rebuild V2)

- **Expected locations:** `study_files/outputs/v13/demand_zone_ml_dataset_v13.csv`
  (`build_hold1_targets.py:39`) and
  `study_files/outputs/hold1/demand_zone_hold1_dataset_v1.csv`
  (`build_v2_dataset.py:56`, which also expects 184 v13 features).
- **Why required:** Only if V2 (#2) must be rebuilt from scratch. Both builders
  call `yfinance` (network) — prohibited here — so the practical path is to
  restore #2 directly from the original archive.
- **Affects reproducibility:** Indirect.
- **How the agent verifies presence:** File exists. Implemented as
  `v13_dataset` / `hold1_dataset` in `verify_inputs()` (informational; not
  required for v1.0.x reproduction).

### 9. Sealed prospective/holdout artifacts (invariant: keep absent)

- **Location:** `study_files/outputs/study_v1/prospective/` (`lock.json`,
  `events.jsonl`, `status.json`)
- **Why:** The final holdout is **SEALED**. These artifacts are created only
  under the frozen protocol's reviewed `freeze-prospective --confirm` flow with
  post-lock predictions logged before outcomes mature. The v1.0.1 archive audit
  verified **zero** prospective predictions/outcomes — that is the honest state.
- **Affects reproducibility:** Not for the baseline; required later for
  prospective evidence.
- **How the agent verifies the invariant:** The directory must be **absent**
  (or empty) during all research work; `verify_inputs()` reports
  `sealed_holdout` as compliant only while absent. Any candidate experiment that
  creates or touches it is auto-rejected (`holdout_touched`).

---

## Anti-requirements

| Artifact | Status | Rule |
|---|---|---|
| `demand_zone_ml_dataset_v10.zip` (repo root, 41.7 MB, 57,848 rows × 121 predictors + `hit_target`, gitignored) | Present locally | **Not** the frozen cohort. Must never be substituted for #2/#3 or used to satisfy any hash. |
| `study_files/outputs/study_v1/development/event_table.csv`, `oof_predictions.csv`, 8 `models/*.joblib` | Present (immutable archive) | Read-only evidence. Never regenerate, overwrite, or "fix" in place. |
| `study_files/research/demand-zone-ai-study/run_manifest_sanitized.json` | Present | Reference only; never copied over #1 (paths were scrubbed). |
| Synthetic/fabricated CSVs of any size | — | Prohibited. A fabricated dataset can never satisfy the pinned SHA-256 values. |
| Re-downloaded `yfinance` data | — | Prohibited as a restoration path; point-in-time vintage is unverifiable and hashes will not match. |

## What passes today without any restoration

- 20/22 study tests (the 2 errors are the #1 and #2 gaps above).
- All 15 `autonomous_agent` unit tests (synthetic state only).
- Hash verification of the present archive files (event table, OOF predictions,
  8 models) is possible and is recorded by `experiment_adapter`'s baseline
  report — but **hash presence is not reproduction**.

## After restoration

1. Run `py -3 -m unittest discover -s study_files/backend/tests -v` → expect 22/22.
2. Run `py -3 -m autonomous_agent.experiment_adapter verify-inputs` → every
   required input reports `present: true`.
3. Run `py -3 -m autonomous_agent.experiment_adapter reproduce` → the adapter
   executes the frozen development pipeline in an isolated workspace and
   compares produced hashes/metrics to the restored manifest. Only a
   `REPRODUCED` verdict unblocks autonomous candidate experiments.
