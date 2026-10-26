# Point-in-Time Raw-Source Lineage Inventory (Campaign 4 prerequisite)

Date: 2026-10-09. **Read-only.** No file was modified, regenerated, or
overwritten; the sealed holdout (`study_files/outputs/study_v1/prospective/`)
was not accessed and does not exist (invariant confirmed). This inventory is
part 1 of the H-5 prerequisite for the `point_in_time_data_audit` primitive
described in `HARNESS_V1_1_0_IMPLEMENTATION_PLAN_2026_10_09.md`.

**Scope discipline:** this is an integrity + structural-availability
inventory, *not* the audit itself. It does not prove any feature is clean; it
establishes whether trustworthy timestamps and lineage records exist so the
audit can be implemented.

## 1. Raw-source files and hashes

| Artifact | Path | SHA-256 (verified this day) |
|---|---|---|
| OHLCV cache (153 CSVs) | `study_files/outputs/v2/_ohlcv/*.csv` | **153/153 match** `run_manifest.json → source_data_sha256` (0 mismatched, 0 missing) |
| Roster/universe source | `study_files/outputs/v2/demand_zone_v2_dataset.csv` | `669ca1f5b21339b8cc26f6eb5cbeb22003ebafcd86b0d7e945f0db3d6517d71b` — matches manifest `roster_source_sha256` and `INPUT_REQUIREMENTS.md` pin |
| Frozen event table (champion dataset) | `study_files/outputs/study_v1/development/event_table.csv` | `232de7db65c92bec249be801e593acdaa822ecd0b13eb0cd32b7eeaced85a4d0` — matches manifest `artifact_sha256` **and** `CHAMPION.json.dataset_sha256` |
| OOF predictions | `study_files/outputs/study_v1/development/oof_predictions.csv` | pinned by manifest (archive closeout re-verified it earlier: `011530761a…`) |
| Lineage dataset archive | `demand_zone_ml_dataset_v10.zip` | `cd41444d406ea9baa3f326f7a4f00b2e0702835944cde4b00889bb3f40241d29` (1 file: `demand_zone_ml_dataset_v10.csv`, 108 MB) |
| v1.0.1 run manifest | `study_files/outputs/study_v1/development/run_manifest.json` | pins `protocol_sha256 486f46f8…`, `code_sha256 29885c5f…` (historical V1.0.1), per-symbol prefix hashes, source max dates |

Sample spot hashes: `AAPL.csv` = `59851df8…458e` (matches manifest entry);
`SPY.csv` = `9e9fe24c…3499`.

## 2. Timestamp fields, event-time definitions, documented provenance

**Raw OHLCV (daily):** column `Date` (+ Open/High/Low/Close/Volume);
parsed by `read_ohlcv()` (`demand_zone_study_v1.py:227-235`) with
`pd.to_datetime`, de-duplicated, sorted. Coverage (manifest
`source_data_coverage` / `source_data_max_date_by_symbol`): first date
2020-08-03, last date **2026-08-03** for all 153 symbols. VIX is stored as
`XVIX.csv` (`^` → `X` filename mapping, `read_ohlcv` line 233).
Provenance rules (`INPUT_REQUIREMENTS.md`): original local archive only;
re-download with `yfinance` or any network tool is forbidden so hashes keep
matching.

**Event table temporal schema (114 cols):** `date` (signal),
`signal_close`, `signal_timestamp`, `feature_asof_date`, `entry_date`,
`exit_date`, `entry_open`, `exit_open`, `hold1_ret`, `label`, `label_valid`.

**Event-time semantics (documented in backend code):**
- Features are as-of the signal date (`feature_asof_date` column; columns
  list at `demand_zone_study_v1.py:744`).
- Entry = **next session open** (`bars.Open.iloc[idx+1]`, line 404);
  exit = session after (`idx+2`, line 414); `exit_date > date` asserted
  (line 697).
- Label = `int(hold1_ret >= 0.02)` where `hold1_ret = exit_open/entry_open − 1`
  (lines 408-418) — the frozen "1-session hold ≥ +2%" target.
- Purge: `train.exit_date < fold start` enforced (line 933); folds 2023 /
  2024 / 2025; replay cutoff `historical_replay_signal_date_cutoff_exclusive`
  (line 54). Archive closeout independently confirms signal dates
  2023-01-03 → 2025-12-31, strictly before 2026-01-01.
- Manifest records `source_data_prefix_sha256` per symbol (hash of data
  through a cutoff) and `source_data_max_date_by_symbol` — sufficient to
  detect any post-hoc mutation of the raw cache.

## 3. Feature families (101 feature columns + 13 label/meta columns)

| Family | Columns | Independent recompute possible from raw inputs at event time? |
|---|---|---|
| Price/volume technical (rsi14, atr_pct, ema*, macd*, roc14, returns, realized_vol, volume*, zone_width_pct, …) | 48 | **Yes in principle** — deterministic functions of OHLCV bars ≤ signal date, recomputable from the hash-verified cache with the frozen backend |
| Market benchmarks (spy_*, qqq_*, iwm_*, vix_* incl. `spy_above_sma200`, `spy_dist_sma200`, `vix_percentile_60d`) | 11 | **Yes** — from SPY/QQQ/IWM/XVIX bars ≤ signal date; **spot-verified this day** (see §4) |
| `zone_base_*` (demand-zone base structure) | 8 | Yes in principle — bar-pattern functions of OHLCV ≤ signal date |
| `ob_bull_*` / `ob_bear_*` (order-block structure) | 34 | Yes in principle — bar-pattern functions of OHLCV ≤ signal date |
| Label machinery (`hold1_ret`, entry/exit) | 5 | Yes by definition — computed from bars strictly **after** the signal date (label maturation is intended, not contamination) |

## 4. Findings — verified / unverifiable / not-found

**VERIFIED (temporal structure):** across **all 61,045 event rows**:
- `feature_asof_date ≤ date` violations: **0**
- `date < entry_date ≤ exit_date` and `label == (hold1_ret ≥ 0.02)`
  inconsistencies: **0**
- Column names containing `future` / `forward` / `alpha_`: **0** (the
  backend also asserts against banned feature names, line 128/194).

**VERIFIED (independent recompute, market family):** `spy_above_sma200` and
`spy_dist_sma200` recomputed from raw `SPY.csv` using only the trailing-200
window ending at the signal date: **245/245 sampled rows match** the frozen
event table exactly (every 250th row, EXIT=0).

**VERIFIED (integrity):** 153/153 raw files, roster, and event table all
hash-match their manifest pins (§1) — the inputs the champion was trained on
cannot have drifted since the v1.0.1 run manifest was written.

**UNVERIFIABLE (documented, permanent):** exact value parity of `rsi14`,
`atr_pct`, `zone_width_pct` (and the original feature-generation code path)
with historical V1.0.1 — original source SHA `29885c5f…` was never recovered;
the archive closeout records 480/480 AAL rows differing under the earlier
partial comparison. This is a **provenance limitation, not evidence of
look-ahead**, and it is the reason the audit semantics in the implementation
plan were revised: a value mismatch on these columns yields UNVERIFIABLE
(audit FAIL / no partial pass), never an automatic contamination verdict.

**NOT FOUND (explicitly not a clean bill of health):** these read-only
checks found no structural look-ahead and no hash drift, but:
- only the market-benchmark family was independently recomputed (245
  sampled rows); the 48 technical and 42 zone/order-block columns were
  **not** re-derived in this inventory — doing so is exactly the job of the
  `point_in_time_data_audit` primitive once implemented;
- absence of found contamination is **not** proof of absence of
  contamination, and this report must not be cited as feature-level
  cleanliness evidence.

## 5. Missing prerequisites for the point-in-time audit

1. **Implementation of the audit primitive itself** (harness v1.1.0) — full
   per-family recompute + structural postdate detection; not yet written.
2. **Human approval of the revised audit semantics** (structural
   contamination → stop; value mismatch on parity-unverifiable columns →
   UNVERIFIABLE → audit FAIL; see implementation plan prerequisite
   section). *Item H-5's "critical lineage" question is answered YES for
   temporal lineage; the parity caveat is the residual decision.*
3. **Timezone caveat:** raw `Date` fields are daily and timezone-naive;
   intraday availability cannot be established from this cache. Daily
   as-of structure is fully checkable; any claim requiring intraday
   ordering is out of scope and would need source data that does not
   exist locally.
4. Historical V1.0.1 source recovery remains closed (Plan B); it is
   **not** a prerequisite — the audit verifies temporal availability of the
   frozen inputs, not historical source parity.

## 6. H-5 lineages verdict

**Critical temporal lineage: VERIFIED** — trustworthy dated raw sources
exist, all hash-pinned to the v1.0.1 manifest, with documented event-time
definitions and passing structural invariants. **Campaign 4 is not blocked
by raw-source lineage**, conditional on the human approving the revised
audit semantics above. Value-level cleanliness of every feature family
remains **unevaluated by design** until the audit primitive runs.
