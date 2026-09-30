# Demand Zone AI: AI Autonomy and Research Foundation Study

This directory indexes a **curated public research release** on a dedicated review branch. The main paper is [Demand_Zone_AI_Autonomy_Study.docx](../../Demand_Zone_AI_Autonomy_Study.docx). It asks: *To what extent can a general-purpose AI autonomously develop a machine-learning system for short-term financial market prediction, and can the resulting system provide a promising foundation for further research?*

This is not a mirror of the entire application repository. The release includes the final manuscript, companion records, frozen protocol, audit report and utility, historical development reports/metadata, and source code used or cited in the study. The exact locally edited generator at [`Python/generate_ml_dataset.py`](../../Python/generate_ml_dataset.py) is included at its original path; it is the pre-existing local version used in the study, not a change introduced for this release. The locally edited audit utility is also included at its original path. See [`bundle_manifest.json`](bundle_manifest.json) for the SHA-256 and size inventory of the curated release (the manifest omits its own self-hash). As of 2026-09-30 the release also includes the retained v1.0.1 artifacts - the eight fitted model binaries, the event table, and the OOF prediction table - authorized for publication by the project owner; the eight model hashes cross-check against `model_artifacts_sha256` in [`run_manifest_sanitized.json`](run_manifest_sanitized.json).

The sanitized archive manifest is [`run_manifest_sanitized.json`](run_manifest_sanitized.json). It preserves v1.0.1 manifest fields and hashes but replaces machine-specific absolute directory paths with repository-relative descriptions. The original local manifest is intentionally not included because it contains machine-specific paths and refers to omitted raw data/model files.

## Evidence and reproduction boundary

The retained v1.0.1 archive is a historical development artifact. The v1.0.2 JSON is a frozen future protocol, **not an executed experiment**. The paper's archive audit was previously performed in the local project workspace against retained files. The corresponding row-level market-derived data are intentionally not included in this public release. The read-only audit utility can now take the event table, OOF table, and model binaries from this branch; it still requires separately held or licensed OHLCV inputs, which remain outside this release.

The source records report that 153 source CSV hashes, two primary table hashes, eight model hashes, OOF/event/label alignment, and saved-score point metrics were checked locally. This public source-only release does not independently repeat those checks. Feature parity was not achieved; all 480 aligned AAL rows differed for each of `rsi14`, `atr_pct`, and `zone_width_pct`; seven archived bootstrap interval bounds remain unreproduced. See the manuscript's evidence matrix and [archive closeout](../../outputs/study_v1_archive_audit_closeout.md).

## Deliberately omitted pending rights review

Market-data redistribution rights were never confirmed, so this bundle omits the raw market data on which the retained artifacts were built:

- all 153 Yahoo-derived OHLCV CSV files;
- the V2, V3 and V5 row-level datasets.

The v1.0.1 event table, OOF prediction/score table, and fitted model binaries were initially withheld under the same concern; on 2026-09-30 the project owner reviewed and authorized their publication, and they are now included under [`outputs/study_v1/`](../../outputs/study_v1/) with hashes recorded in [`bundle_manifest.json`](bundle_manifest.json). They are derived artifacts (features, labels, scores, and fitted parameters) rather than redistributed raw market records, but their ticker-date rows remain market-derived data.

The public bundle now permits a reader to recompute the archived point metrics from the included OOF scores and to verify every retained artifact hash, but not to regenerate the events or features from raw prices: the raw OHLCV source data remain omitted, and the historical source code that generated the v1.0.1 features was never recovered (feature parity failed). Source code, historical reports/metadata, the sanitized manifest with hash references, and the audit closeout preserve the research trail. Project materials describe the source data as Yahoo-derived historical snapshots, not point-in-time vendor vintages; review provider and exchange terms and obtain any necessary permissions before redistributing or using omitted data.

## Deliberate exclusions beyond data

The branch excludes the rest of the trading application and unrelated local working tree: Freebuff databases/logs/caches, unrelated scanners and models, unrelated datasets, recovered-but-unreviewed bytecode and replay scratch, superseded unbounded refresh artifacts, and earlier manuscript DOCX files that used the wrong research question. The older Markdown research draft is retained only as historical source material; it is explicitly not the final research question or conclusion.
