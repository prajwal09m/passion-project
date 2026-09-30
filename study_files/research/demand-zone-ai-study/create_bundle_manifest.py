#!/usr/bin/env python3
"""Create a SHA-256/size inventory for the curated public study bundle.

Run from the repository root. Writes a sanitized copy of the v1.0.1 manifest
and the bundle inventory. Market data, row-level derived tables, and fitted
model binaries are excluded pending confirmation of redistribution rights.
The inventory does not hash itself; it covers all other release files.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE_DIR = ROOT / "research" / "demand-zone-ai-study"
OUT = BUNDLE_DIR / "bundle_manifest.json"
SOURCE_RUN_MANIFEST = ROOT / "outputs" / "study_v1" / "development" / "run_manifest.json"
SANITIZED_RUN_MANIFEST = BUNDLE_DIR / "run_manifest_sanitized.json"

RELEASE_PATHS = [
    ".freebuff/build_demand_zone_research_paper.py",
    ".freebuff/recovery_tools/audit_saved_v1_0_1_outputs.py",
    "DEMAND_ZONE_AI_RESEARCH_DRAFT.md",
    "Demand_Zone_AI_Autonomy_Study.docx",
    "Demand_Zone_AI_Development_and_Audit_Record.docx",
    "MARKET_STRUCTURE_ABLATION_PROTOCOL.md",
    "MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json",
    "Market_Structure_Experiment_Protocol.docx",
    "Python/augment_v10_to_v11.py",
    "Python/augment_v11_to_v12.py",
    "Python/augment_v12_to_v13.py",
    "Python/augment_with_order_blocks.py",
    "Python/generate_ml_dataset.py",
    "Python/order_block_detector.py",
    "backend/build_hold1_targets.py",
    "backend/build_v2_dataset.py",
    "backend/build_v3_dataset.py",
    "backend/build_v5_dataset.py",
    "backend/demand_zone_study_v1.py",
    "backend/tests/test_demand_zone_study_v1.py",
    "backend/train_hold1.py",
    "backend/train_v2.py",
    "backend/train_v3.py",
    "backend/train_v4.py",
    "backend/train_v5.py",
    "backend/train_v7.py",
    "backend/v2_features.py",
    "backend/v4_features.py",
    "models/v2/hold1_v2_metadata.json",
    "models/v3/v3_metadata.json",
    "models/v4/v4_metadata.json",
    "models/v5/v5_metadata.json",
    "models/v6/v6_metadata.json",
    "models/v7/v7_metadata.json",
    "outputs/study_v1/development/development_report.md",
    "outputs/study_v1_archive_audit_closeout.md",
    "outputs/v2/v2_report.md",
    "research/demand-zone-ai-study/README.md",
    "research/demand-zone-ai-study/create_bundle_manifest.py",
    "research/demand-zone-ai-study/run_manifest_sanitized.json",
]


def sha256_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def write_sanitized_run_manifest() -> None:
    manifest = json.loads(SOURCE_RUN_MANIFEST.read_text(encoding="utf-8"))
    if "data_directory" in manifest:
        manifest["data_directory"] = "outputs/v2/_ohlcv (omitted from public release)"
    if "artifact_directory" in manifest:
        manifest["artifact_directory"] = "outputs/study_v1 (row-level data/models omitted from public release)"
    manifest["public_release_note"] = (
        "Sanitized copy of the local v1.0.1 run manifest: machine-specific absolute paths were "
        "replaced with repository-relative descriptions. Referenced market-data, row-level result, "
        "and model files are not included in this public bundle."
    )
    SANITIZED_RUN_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    write_sanitized_run_manifest()
    paths = sorted(set(RELEASE_PATHS))
    missing = [relative for relative in paths if not (ROOT / relative).is_file()]
    if missing:
        raise SystemExit("Missing expected release files:\n" + "\n".join(missing))

    files = []
    for relative in paths:
        path = ROOT / relative
        files.append({
            "path": relative,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "storage": "git",
        })
    result = {
        "schema_version": 1,
        "description": "Rights-conscious public study release; row-level data and fitted models are omitted.",
        "file_count": len(files),
        "total_bytes": sum(item["bytes"] for item in files),
        "inventory_note": "This inventory intentionally does not hash itself.",
        "files": files,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(files)} release files, {result['total_bytes']} bytes")


if __name__ == "__main__":
    main()
