"""Build a self-contained, hash-manifested test fixture tree under ``dev/``.

This copies only explicit development inputs and authoritative records. It
never writes into the source repository, reads no prospective/holdout path,
and does not run a campaign. Tests run from ``dev/`` and therefore consume
these staged files, not implicit paths into the source checkout.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
SOURCE = WORKSPACE.parent
DEV = WORKSPACE / "dev"

# Each path is copied verbatim into its same relative location below dev/.
# This list is deliberately explicit: new fixture inputs require a conscious
# edit rather than an unnoticed dependency on the source checkout.
FIXTURES = [
    # Eligible retained development data and the reviewed study contract; no
    # prospective/holdout data is copied or even enumerated.
    "study_files/outputs/study_v1/development/event_table.csv",
    "study_files/backend/demand_zone_study_v1.py",
    "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json",
    # R-3 owner record and Campaign 1/3/4 immutable evidence used by pin tests.
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/PRIMITIVE_ACTIVATION_GRANT_R3_2026_10_12.md",
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/HARNESS_V1_1_0_IMPLEMENTATION_PLAN_2026_10_09.md",
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/AUTONOMOUS_CAMPAIGN_AUDIT_2026_10_04.md",
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_4_CONFIG_DRAFT_2026_10_09.json",
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/GOVERNANCE_SUITE_FLAKE_EVIDENCE_2026_10_11.md",
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_4_FINAL_ARCHIVE_2026-10-16/SHA256SUMS.txt",
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_3_FINAL_ARCHIVE_2026-10-09/campaign_config.json",
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/C4_MEASUREMENT_WIRING_FINDING_OWNER_DECISION_RECORD_2026_10_16.md",
    "autonomous_agent/state/campaign_config.json",
    "autonomous_agent/state/campaign_config.sha256",
    "autonomous_agent/state/campaign_config.campaign-3-continuous-2026-10-05.json",
    "autonomous_agent/state/loop_state.json",
    "autonomous_agent/state/loop_state.campaign-3-continuous-2026-10-05.final.json",
    "autonomous_agent/state/proposal_ledger.jsonl",
    "autonomous_agent/state/campaign_end_multiplicity.jsonl",
    "autonomous_agent/state/baseline_reproduction.json",
    "autonomous_agent/candidates/exp-proposal-5d52d16b94ca/result.json",
    "autonomous_agent/candidates/exp-proposal-4fdf6dd35236/result.json",
    "autonomous_agent/candidates/exp-calibration-stability-check-a00/spec.json",
    "autonomous_agent/candidates/exp-calibration-stability-check-a00/result.json",
    "autonomous_agent/candidates/exp-feature-arm-nested-ablation-a00/spec.json",
    "autonomous_agent/candidates/exp-feature-arm-nested-ablation-a00/result.json",
    "autonomous_agent/candidates/exp-model-class-matched-comparison-a00/spec.json",
    "autonomous_agent/candidates/exp-model-class-matched-comparison-a00/result.json",
    "autonomous_agent/candidates/exp-calibration-stability-check-a01/spec.json",
    "autonomous_agent/candidates/exp-calibration-stability-check-a01/result.json",
    "autonomous_agent/candidates/exp-feature-arm-nested-ablation-a01/spec.json",
    "autonomous_agent/candidates/exp-feature-arm-nested-ablation-a01/result.json",
    "autonomous_agent/candidates/exp-model-class-matched-comparison-a01/spec.json",
    "autonomous_agent/candidates/exp-model-class-matched-comparison-a01/result.json",
    "autonomous_agent/candidates/exp-feature-arm-nested-ablation-a02/spec.json",
    "autonomous_agent/candidates/exp-feature-arm-nested-ablation-a02/result.json",
    "autonomous_agent/candidates/exp-model-class-matched-comparison-a02/spec.json",
    "autonomous_agent/candidates/exp-model-class-matched-comparison-a02/result.json",
    "versions/V2.0.1/version.json",
    "versions/V2.0.2/version.json",
    "versions/V2.0.3/version.json",
    "versions/V2.0.4/version.json",
    "versions/V2.0.5/version.json",
    "versions/V2.0.6/version.json",
    "versions/V2.0.7/version.json",
    "versions/V2.0.8/version.json",
    # Stat-validation consumers and exact independent reference used by tests.
    "stat_validation_h10/family_records.py",
    "stat_validation_h10/campaign_end_finalization.py",
    "stat_validation_h10/simh10.py",
    "stat_validation_h10/launch_gates.json",
    "stat_validation_h10/H10_DECISION_RECORD_AWAITING_SIGNATURE.md",
    "stat_validation_h10/H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md",
    "stat_validation_h10/H10_D2_REVIEW_SUBMISSION.zip",
    "autonomous_agent/signflip_port_fixtures_2026_10_14.json",
]

# Pins already recorded in governance/predeclaration artifacts. These catch
# source drift before a staged copy can make a stale test appear self-contained.
PINNED = {
    "study_files/outputs/study_v1/development/event_table.csv":
        "232de7db65c92bec249be801e593acdaa822ecd0b13eb0cd32b7eeaced85a4d0",
    "study_files/backend/demand_zone_study_v1.py":
        "cea2440425e1f2f56a95b576481ae2ef603fe1f6a9816078e0a998781e0cef2a",
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/PRIMITIVE_ACTIVATION_GRANT_R3_2026_10_12.md":
        "ab728ba6b463a67075bc071dea73377379ae8a685db7f4d0a5592869699e0ece",
    "autonomous_agent/state/campaign_config.json":
        "d8bff195eb6e3e1e81c201f78b9961f1d0d9738a611498eaca593f394e238862",
    "autonomous_agent/state/proposal_ledger.jsonl":
        "d97da2680245be8a690ab097d1e25b1ac99b7668b74ce064cf8068f6a51f9ba8",
    "autonomous_agent/state/campaign_end_multiplicity.jsonl":
        "7547704337738e829ce71bddd524b7458cdc62f38ee3642443597eedd5abe9d3",
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/C4_MEASUREMENT_WIRING_FINDING_OWNER_DECISION_RECORD_2026_10_16.md":
        "7d837caa9123be50ca0407d167b6c69aed29dc90d86f59968c693dcfc0d54130",
    "stat_validation_h10/family_records.py":
        "a6f0583dca3caf0e83c363026dd4d1ea9eb6e669268a48fca9e9a5da538eaca1",
    "stat_validation_h10/campaign_end_finalization.py":
        "10d89e947bd65a9f944043f210e4288eacba3c8cddd0fac43adf788e4c95b4c1",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    missing = [name for name in FIXTURES if not (SOURCE / name).is_file()]
    if missing:
        raise FileNotFoundError("missing allowlisted fixture sources: " + ", ".join(missing))
    records = []
    for name in FIXTURES:
        source, target = SOURCE / name, DEV / name
        source_hash = sha256(source)
        expected = PINNED.get(name, "")
        if expected and source_hash != expected:
            raise ValueError(f"authoritative source hash drift for {name}: {source_hash} != {expected}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target_hash = sha256(target)
        if target_hash != source_hash:
            raise IOError(f"copy verification failed for {name}")
        records.append({"path": name, "bytes": source.stat().st_size,
                        "sha256": source_hash,
                        "source": "authoritative retained development/provenance artifact"})
    # Fail closed if a holdout appears in the test fixture tree.
    holdout = DEV / "study_files/outputs/study_v1/prospective"
    if holdout.exists():
        raise RuntimeError(f"fixture tree must not contain a prospective/holdout directory: {holdout}")
    manifest = {
        "fixture_layout": "isolated-development-input-snapshot-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_root_label": "workspace-authoritative-checkout",
        "scope": "read-only development/test fixtures only; no campaign execution; no holdout",
        "files": records,
        "holdout_path_absent": True,
    }
    out = DEV / "FIXTURE_PROVENANCE.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"staged and hash-verified {len(records)} allowlisted fixture files; "
          f"{sum(row['bytes'] for row in records):,} bytes total")
    print(f"fixture manifest: {out}")


if __name__ == "__main__":
    main()
