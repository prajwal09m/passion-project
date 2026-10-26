# RESTORATION REPORT — V1.0.1 Research Inputs (MAIN TASK 1)

**Date:** 2026-10-02
**Scope:** Local-only recovery and byte-level verification of the exact historical
inputs required by frozen protocol `DZAI-MARKET-STRUCTURE-ABLATION-V1`, and one
real baseline reproduction run. No data was regenerated, downloaded, or
synthesized. No pinned file was altered. The frozen protocol was not modified.
The stock-model files (`study_files/outputs/study_v1/models/*.joblib`) were not
modified.

**Outcome:** All three inputs required for reproduction were **FOUND and
RESTORED byte-exactly**. Baseline reproduction result is recorded in section 6.

---

## 1. Method

### 1.1 Search coverage

| Location | How searched | Result |
|---|---|---|
| Working tree (all dirs) | `find` by name/pattern for `run_manifest*.json`, `demand_zone_v2_dataset*`, `XVIX.csv`, `*_ohlcv*`, `*v5/v13/hold1*dataset*` | Only `run_manifest_sanitized.json` copies (rejected, see §4) |
| Git branches / tags / reflog | `git branch -a`, `git tag -l`, `git reflog --all`, `git for-each-ref` | 1 branch pair (`study/...` + `main`), no tags; reflog shows only known commits + resets |
| Git history (all reachable objects) | `git rev-list --all --objects` + path greps | `data (v1)/` dataset (rejected §4), `Other/` legacy CSVs, archive artifacts |
| Git unreachable objects | `git fsck --unreachable`; **full content hash scan of every object in the object database (54,495 objects, ≈4.0 GB decompressed, loose + packed)** | **Recovered all 153 OHLCV CSVs, the V2 dataset, and the unsanitized run manifest** (§2) |
| Orphaned temp pack | Parsed `.git/objects/pack/tmp_pack_Ds7zuW` (87 MB, unindexed) + `.git/objects/b8/tmp_obj_*` | Truncated pack: 288/3,930 objects parsed before EOF; no pin hits beyond duplicates of found objects |
| Parent directories (`/c/Prajwal MIT` tree) | `find` recursive, name-targeted | Nothing |
| Other user folders / drives | `/c/$Recycle.Bin`, `/c/Users`, `/c/Downloads`, `/c/Documents`, `/c/Kairos`, `/c/Kamal`, `/c/Hindi`; drive letters D:–G: (absent) | Nothing (only C: exists) |
| Archives | Inspected `demand_zone_ml_dataset_v10.zip`, `outputs/v7–v10/*.zip` entry lists | Each contains exactly one V7–V10 dataset CSV (rejected §4) |
| Recovery folders | `study_files/.freebuff/recovery_tools/`, `application_files/.freebuff/recovery_tools/` | Audit script + pyc decompiler tooling; no data artifacts |

### 1.2 Verification method (why “similar” files were not accepted)

* Every known-good SHA-256 was taken from the immutable pin record:
  `study_files/research/demand-zone-ai-study/run_manifest_sanitized.json`
  (`source_data_sha256` = 153 per-symbol OHLCV hashes, `artifact_sha256`,
  `model_artifacts_sha256`, `roster_source_sha256`, `universe_sha256`) plus the
  hard-coded pins in `study_files/backend/tests/test_demand_zone_study_v1.py`
  and `autonomous_agent/experiment_adapter.py`.
* Candidates were hashed **byte-for-byte**. Because Git normalizes line endings
  on commit, each candidate was additionally hashed under LF→CRLF and CRLF→LF
  transforms before rejection. Methodology validated on a known case: the
  committed `event_table.csv` blob hashes to `964a0e8c…` raw but to the pin
  `232de7db…` after LF→CRLF, matching the archived file byte-for-byte.
* Acceptance required an **exact hash match**; schema, row counts, ticker
  counts, date ranges and per-symbol max dates were verified as secondary
  evidence (§2). No “close enough” file was accepted anywhere.

---

## 2. Required artifacts — restored and verified

### 2.1 V1.0.1 `run_manifest.json` — **FOUND, EXACT**

| Field | Value |
|---|---|
| Found | Yes |
| Exact match | Yes (provably the original) |
| SHA256 (restored bytes, CRLF as originally written on Windows) | `dab3ee5f6b07078f44d1c6bb2a76163e02619c301bc83b67bb49e9f2dab469c9` |
| Source location | Git object `d27b3eb563a6b1f7…` (unreachable loose object in `.git/objects`) |
| Restored to | `study_files/outputs/study_v1/development/run_manifest.json` |
| Status | **RESTORED — VERIFIED** |

Verification evidence:
* Internal pins all correct: `protocol_version=1.0.1`,
  `protocol_sha256=486f46f8…ec07`, `code_sha256=29885c5f…2424b`,
  `test_suite_sha256=e3f16447…ce456`, `roster_source_sha256=669ca1f5…d71b`,
  `universe_sha256=2cc7e1ea…8616`, `universe_size=149`,
  `source_data_sha256` = 153 entries.
* Diff vs the published sanitized copy: **exactly 3 fields**
  (`artifact_directory`, `data_directory` — real machine paths
  `C:\Prajwal MIT\Passion\outputs\…` replaced by placeholders — and
  `public_release_note`). This establishes identity with the V1.0.1 original
  beyond reasonable doubt.
* `artifact_sha256` entries (`event_table.csv=232de7db…`, `oof_predictions.csv=01153076…`)
  match the files already present in `study_files/outputs/study_v1/development/`.

### 2.2 V2 roster dataset (`demand_zone_v2_dataset.csv`) — **FOUND, EXACT**

| Field | Value |
|---|---|
| Found | Yes |
| Exact match | Yes |
| SHA256 (restored bytes) | `669ca1f5b21339b8cc26f6eb5cbeb22003ebafcd86b0d7e945f0db3d6517d71b` (= `roster_source_sha256` pin) |
| Source location | Git object `ac06e52781e6a30d…` (unreachable loose object; LF-normalized in the object DB, LF→CRLF restores the pinned bytes) |
| Restored to | `study_files/outputs/v2/demand_zone_v2_dataset.csv` (285,593,416 bytes) |
| Status | **RESTORED — VERIFIED** |

Verification evidence: 44,854 rows (matches `v2_report.md`), **149 distinct
tickers** (exact universe), dates **2021-08-03 → 2026-06-24** (matches the
documented dataset span), 444 columns beginning
`ticker,date,entry_price,is_sub_10,daily_return,5d_return,20d_return,ema_20,…`,
 and the file hash equals the pin exactly.

### 2.3 OHLCV cache — 153 CSVs incl. `XVIX.csv` — **FOUND, ALL EXACT**

| Field | Value |
|---|---|
| Found | Yes — 153/153 |
| Exact match | Yes — 153/153 hash-equal to `source_data_sha256` |
| Source location | Git object database (unreachable loose objects); per-symbol blobs |
| Restored to | `study_files/outputs/v2/_ohlcv/{SYMBOL}.csv` (149 roster symbols + SPY, QQQ, IWM, XVIX) |
| Status | **RESTORED — VERIFIED** |

Verification evidence: every file’s SHA-256 equals its manifest pin
(`XVIX.csv = 92c65e10…d780f7`, `SPY.csv = 9e9fe24c…e943499`, etc.);
schema `date,open,high,low,close,volume` on all 153; `XVIX.csv` has 1,508 rows;
SPY spans 2020-08-03 → 2026-08-03; **per-symbol max dates match the manifest’s
`source_data_max_date_by_symbol` for all 153 symbols (0 mismatches)**.

### 2.4 V1.0.1 source implementation — **NOT FOUND** (attribution only)

| Field | Value |
|---|---|
| Found | No |
| Expected SHA256 | `29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b` (`code_sha256`) |
| Searched | Working tree, full git object DB content-hash scan (54,495 objects), unreachable objects, orphan pack, recovery folders, archives, all local drives |
| Status | **NOT FOUND — attribution blocker remains open** |

Evidence trail found (but not the source itself): a manifest blob
(`43e8acd4f0926c4d…`) from directory
`outputs/study_v1_recovered_bytecode_unreviewed_20260928` proves the preserved
**bytecode** was executed on 2026-09-28 and regenerated the byte-identical
artifacts (`event_table.csv=232de7db…`, `oof_predictions.csv=01153076…`). A
runner script blob (“Temporary Python 3.13 runner for the preserved, unreviewed
study bytecode. This is not source recovery.”) survives in the object database.
Per the research record, decompiled/unreviewed bytecode is **not** accepted as
source recovery; the documented v1.0.2 reconstruction
(`study_files/backend/demand_zone_study_v1.py`) is the reviewed implementation
used for reproduction. If you can provide the original
`demand_zone_study_v1.py` (V1.0.1) file, place it at
`study_files/research/demand-zone-ai-study/recovered_source/` and it must hash
to `29885c5f…2424b`; that would close the attribution gap.

### 2.5 V5 / V13 / hold1 lineage datasets — **NOT FOUND** (not required)

Expected: `study_files/outputs/v5/demand_zone_v5_dataset.csv`,
`study_files/outputs/v13/demand_zone_ml_dataset_v13.csv`,
`study_files/outputs/hold1/demand_zone_hold1_dataset_v1.csv`. Only the build
scripts survive in git (`build_v5_dataset.py`, `augment_v12_to_v13.py`,
`build_hold1_targets.py`). These matter **only** for rebuilding V2 from scratch,
which is prohibited (no network rebuilds); the restored V2 dataset makes them
unnecessary. Status: **NOT FOUND — does not block reproduction.**

### 2.6 Prospective/holdout artifacts — **CONFIRMED ABSENT (as required)**

`study_files/outputs/study_v1/prospective/` does not exist; the holdout remains
sealed.

---

## 3. Independent corroboration

* `study_files/outputs/study_v1_archive_audit_closeout.md` recorded
  “153/153 cached source CSVs … match the v1.0.1 run manifest hashes”; the
  restored cache now re-verifies exactly that claim.
* Study test suite after restoration: **22/22 pass** (the two previous
  missing-input errors are resolved *by restoring the inputs — no test was
  relaxed*).
* Agent test suite: **32/32 pass** (unchanged).

---

## 4. Rejected candidates and why

| Candidate | Location | Reason for rejection |
|---|---|---|
| `data (v1)/*_data.csv` (164 files) | Git commit `0d4a947` (“Reorganize project and add compressed datasets”) | 0/152 hash matches against `source_data_sha256`; naming `*_data.csv`; VIX-era symbols (`VIX_data.csv`, sector SPDRs) instead of `XVIX.csv` — a different, earlier data vintage |
| `run_manifest` blob `187a4d53…` (105,135 B) | Git object DB | A *refresh* run (`outputs/study_v1_refresh_20260928`): `protocol_sha256=abf14204…` ≠ pin, `code_sha256=2bbf7374…` ≠ pin, artifact hashes `24b1bb7a…/8db67e42…` ≠ pins — a different run, not V1.0.1 |
| `run_manifest` blob `43e8acd4…` (90,132 B) | Git object DB | The *recovered-bytecode* run manifest (`protocol_version=1.0.2`, `code_sha256=b39ece5b…`) — not the V1.0.1 manifest. **Retained as reproduction evidence** (its `artifact_sha256` equals the pins) |
| `run_manifest` blob `e064f0cc…` (92,150 B) | Git object DB | Sanitized-copy draft; differs from the published sanitized copy only in `public_release_note` wording — a derivative, not the original |
| `run_manifest_sanitized.json` | `study_files/research/…` (tracked) | Published sanitized derivative (placeholder paths); kept as pin reference only, explicitly forbidden as the input artifact |
| `demand_zone_ml_dataset_v10.zip`, `outputs/v7–v10/*.zip` | Working tree | Each contains only its V7–V10 dataset CSV; prohibited substitutes (different targets/cohorts) |
| `Other/demand_zone_ml_dataset.csv` | Git history | Legacy broad V1 dataset, different schema/vintage |
| 1,255 other OHLCV-format CSV blobs | Git object DB | Correct schema but **no hash matches** (V1-era and other vintages); near-miss data is not accepted |
| 14 ticker-dataset CSV blobs (301 MB / 286 MB / 115 MB / 114 MB / 14.7 MB etc.) | Git object DB | V3–V10-era datasets; hash ≠ `roster_source_sha256`; different column sets (e.g. `entry_price,is_sub_10,…` variants, model-score columns) |
| `tmp_pack_Ds7zuW` remainder | `.git/objects/pack/` | Truncated pack (parse stops at EOF byte 87,162,880 of 3,930 declared objects); parsed portion contains only duplicates of already-found objects |
| 8 fitted models + `event_table.csv` + `oof_predictions.csv` copies in git history | Git commit `a108cdb` | Accepted as **archive artifacts** (they match their pins — see §2), not used as substitutes for any input |

---

## 5. What was restored where

| Restored file | Bytes | SHA-256 |
|---|---|---|
| `study_files/outputs/study_v1/development/run_manifest.json` | 94,519 | `dab3ee5f6b07078f44d1c6bb2a76163e02619c301bc83b67bb49e9f2dab469c9` |
| `study_files/outputs/v2/demand_zone_v2_dataset.csv` | 285,593,416 | `669ca1f5b21339b8cc26f6eb5cbeb22003ebafcd86b0d7e945f0db3d6517d71b` |
| `study_files/outputs/v2/_ohlcv/*.csv` (153 files) | ≈21 MB total | each = its `source_data_sha256` pin (153/153) |

Restoration tooling (evidence, re-runnable):
* `autonomous_agent/restoration_scan.py` — content-hash scan of every git
  object (incl. orphan pack) against all pins; evidence in
  `.restoration_tmp/object_scan.json`.
* `autonomous_agent/restore_inputs.py` — extracts only hash-verified blobs,
  re-verifies after write; refuses on any mismatch.

---

## 6. Baseline reproduction run — EXECUTED (2026-10-02)

Command: `py -3 -m autonomous_agent.experiment_adapter reproduce --force`
(unmodified pipeline; no model changes, no optimization, no protocol change, no
holdout-rule changes). Executed twice: a first full run, plus a clean re-run
whose record is persisted in
`autonomous_agent/state/baseline_reproduction.json`
(recorded 2026-10-02T21:43:18Z, `original_tree_unchanged: True`).
Inside an isolated workspace copy the run completed all three phases:
1. unit tests (`study_files/backend/tests`) — passed,
2. `demand_zone_study_v1.py audit` — passed on the restored roster + OHLCV cache,
3. `demand_zone_study_v1.py development` — full 2023–2025 walk-forward training
   (8 model fits) completed and produced its own `run_manifest.json`.

Comparison of the produced manifest against the restored V1.0.1 manifest:

| Key | Result |
|---|---|
| `universe_sha256` | **match** (`2cc7e1ea…`) — the 149-symbol universe reproduces exactly |
| `protocol_sha256` provenance | **verified both sides** (archive = v1.0.1 pin `486f46f8…`; run = current frozen v1.0.2 file `6b4e4557…`; legitimately different across protocol versions) |
| `artifact_sha256` | **DRIFT** — produced `event_table.csv`/`oof_predictions.csv` are not byte-identical to the archive |
| `pooled_oof_metrics` | **DRIFT** — model scores/metrics differ |

**Verdict: NOT REPRODUCED (FAILED with drift).** Machine state:
`status: FAILED`, recommendation `STOP_AUTONOMOUS_EXPERIMENTATION`.

### 6.1 Root cause — proven, single point of failure

A column-by-column comparison of the produced vs archived artifacts isolates
the divergence exactly:

* **Identical:** all 61,045 events and 41,221 OOF rows; `ticker`, `date`,
  `event_id`, `label`, `hold1_ret`, `entry_date`, `exit_date`, `fold`,
  `fold_validation_key`; 65 of 114 event-table columns — the event cohort,
  labels, folds, and universe reproduce exactly.
* **Differing:** 49 feature columns — `rsi14`, `atr_pct`, `zone_width_pct`,
  all 14 zone-base features (`zone_base_*`, `zone_volatility_contraction`,
  `zone_departure_atr_multiple`, `zone_compression_score`, …) and all 32
  order-block features (`ob_bull_*`, `ob_bear_*`). Consequently all 8 model
  score columns differ (max |Δ| 0.09–0.87).
* **Ruled out:** environment drift — the run-time stack is byte-for-byte the
  original (`numpy 2.3.3, pandas 2.3.3, scikit-learn 1.9.0, lightgbm 4.7.0,
  joblib 1.5.3`, matching the manifest `runtime` record).

This is exactly the defect the project's own archive audit documented
("all 480 scoped AAL rows differ for `rsi14`, `atr_pct`, `zone_width_pct` —
feature parity FAILED"). The reviewed reconstruction computes the zone /
order-block / indicator feature pipeline differently from the V1.0.1
implementation. Byte-exact reproduction is therefore impossible with the
reviewed reconstruction alone.

Corroboration that the inputs are correct: the preserved (unreviewed) V1.0.1
bytecode run of 2026-09-28, on this same machine and library stack, produced
`event_table.csv=232de7db…` and `oof_predictions.csv=01153076…` — the exact
pins — from this exact input set (manifest blob `43e8acd4…`).

---

## 7. Final state — STOP, with one exact remaining gap

State transition achieved:

```
BLOCKED  →  inputs restored & verified  →  reproduction run  →  FAILED (feature-parity drift)
```

### 7.1 The exact remaining missing artifact

| Item | Detail |
|---|---|
| Artifact | The **V1.0.1 study source implementation** — the file that computed `rsi14`, `atr_pct`, `zone_width_pct`, the 14 zone-base features, and the 32 order-block features as archived |
| Expected name | `demand_zone_study_v1.py` (V1.0.1) |
| Expected SHA-256 | `29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b` (`code_sha256` pin) |
| Drop zone | `study_files/research/demand-zone-ai-study/recovered_source/` |
| Also acceptable | Reviewed source recovery from the preserved bytecode that hashes to the same pin; anything else is rejected |

### 7.2 Locations searched (all of them)

Working tree; every Git ref/branch/tag; reflog; **every object in the Git
object database by content hash (54,495 objects, ≈4.0 GB decompressed,
including unreachable loose objects)**; the orphaned 87 MB temp pack; parent
directories; `$Recycle.Bin`; all user folders on C: (D:–G: do not exist); all
archives/zips; all `.freebuff` recovery folders. No object anywhere hashes to
`29885c5f…`.

### 7.3 What I need from you

Provide the original V1.0.1 `demand_zone_study_v1.py` (or a source archive
containing it) at the drop zone above. Everything else is in place:

* all 3 reproduction inputs restored and byte-verified (§2),
* the reproduction pipeline runs end-to-end and records its evidence (§6),
* the moment the source hash matches the pin, `py -3 -m autonomous_agent.experiment_adapter
  reproduce --force` becomes `REPRODUCED` and autonomous experimentation may
  honestly begin.

Per instruction, no gates were weakened, no inputs fabricated, no fake baseline
created, and the original stock-model files remain unchanged. Autonomous
experimentation (MAIN TASK 2+) remains correctly **gated** behind `REPRODUCED`.

### 7.4 Addendum — 2026-10-02 source-delivery verification attempt

A delivery of the V1.0.1 source was announced at
`study_files/research/demand-zone-ai-study/recovered_source/demand_zone_study_v1.py`.
Verification **failed — the file is not present**:

* the stated path does not exist; no `recovered_source/` directory exists in
  this checkout, in the OneDrive checkout
  (`C:\Users\kamal\OneDrive\Documents\GitHub\passion-project`), in user
  folders (Desktop/Downloads/Documents/Temp), or in Git history;
* no file anywhere matches `code_sha256=29885c5f…2424b` under raw, LF→CRLF,
  or CRLF→LF hashing;
* the three `demand_zone_study_v1.py` copies that do exist are all the same
  reconstruction content in different line endings:
  `study_files/backend/demand_zone_study_v1.py` (LF, `cea24404…`),
  `backend/demand_zone_study_v1.py` (CRLF twin, `2b1cce35…`), and the OneDrive
  copy (`2b1cce35…`). None is the historical implementation.

Current-tree verification items: study tests **22/22 OK**, agent tests
**40/40 OK**, original tree untouched. The reproduction was **not** re-run:
with the recovered source absent the pipeline still executes the
reconstruction and would deterministically repeat the recorded §6 drift.

Note for the next delivery attempt: the reproduction command registry runs
`study_files/backend/demand_zone_study_v1.py`, not the drop zone. When a file
hashing to `29885c5f…` is delivered, it must be installed **byte-identically**
over that path (unmodified copy; the reconstruction remains recoverable from
Git) so the reproduction actually executes the historical implementation.
Only then can `reproduce --force` honestly reach `REPRODUCED`.
