# Demand Zone AI: AI Autonomy and Research Foundation Study

This directory indexes a **curated public research release** on a dedicated review branch. The main paper is [Demand_Zone_AI_Autonomy_Study.docx](../../Demand_Zone_AI_Autonomy_Study.docx). It asks: *To what extent can a general-purpose AI autonomously develop a machine-learning system for short-term financial market prediction, and can the resulting system provide a promising foundation for further research?*

This is not a mirror of the entire application repository. The release includes the final manuscript, companion records, frozen protocol, audit report and utility, historical development reports/metadata, and source code used or cited in the study. The exact locally edited generator at [`Python/generate_ml_dataset.py`](../../Python/generate_ml_dataset.py) is included at its original path; it is the pre-existing local version used in the study, not a change introduced for this release. The locally edited audit utility is also included at its original path. See [`bundle_manifest.json`](bundle_manifest.json) for the SHA-256 and size inventory of the curated release (the manifest omits its own self-hash).

The sanitized archive manifest is [`run_manifest_sanitized.json`](run_manifest_sanitized.json). It preserves v1.0.1 manifest fields and hashes but replaces machine-specific absolute directory paths with repository-relative descriptions. The original local manifest is intentionally not included because it contains machine-specific paths and refers to omitted raw data/model files.

## Evidence and reproduction boundary

The retained v1.0.1 archive is a historical development artifact. The v1.0.2 JSON is a frozen future protocol, **not an executed experiment**. The paper's archive audit was previously performed in the local project workspace against retained files. The corresponding row-level market-derived data are intentionally not included in this public release. Consequently, the read-only audit utility cannot be run to completion from this branch alone: it requires separately held or licensed OHLCV inputs, event and OOF tables, and model binaries.

The source records report that 153 source CSV hashes, two primary table hashes, eight model hashes, OOF/event/label alignment, and saved-score point metrics were checked locally. This public source-only release does not independently repeat those checks. Feature parity was not achieved; all 480 aligned AAL rows differed for each of `rsi14`, `atr_pct`, and `zone_width_pct`; seven archived bootstrap interval bounds remain unreproduced. See the manuscript's evidence matrix and [archive closeout](../../outputs/study_v1_archive_audit_closeout.md).

## Deliberately omitted pending rights review

The project owner did not know whether public redistribution was permitted. To avoid publicly redistributing market-data records without confirmed rights, this bundle omits:

- all 153 Yahoo-derived OHLCV CSV files;
- the V2, V3 and V5 row-level datasets;
- the v1.0.1 event table and row-level OOF prediction/score tables;
- fitted model binaries and other serialized models.

The public bundle therefore does **not** permit a reader to independently recompute the archive's row-level checks or score metrics. It includes source code, historical reports/metadata, a sanitized manifest with hash references, and the audit closeout to preserve the research trail without publishing those data artifacts. Project materials describe the source data as Yahoo-derived historical snapshots, not point-in-time vendor vintages; review provider and exchange terms and obtain any necessary permissions before redistributing or using omitted data.

## Deliberate exclusions beyond data

The branch excludes the rest of the trading application and unrelated local working tree: Freebuff databases/logs/caches, unrelated scanners and models, unrelated datasets, recovered-but-unreviewed bytecode and replay scratch, superseded unbounded refresh artifacts, and earlier manuscript DOCX files that used the wrong research question. The older Markdown research draft is retained only as historical source material; it is explicitly not the final research question or conclusion.
