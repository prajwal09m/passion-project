"""Regression tests for the protocol-fingerprint recorded convention.

Covers:
* canonicalization agreement across the three byte-identical implementations
  (schema.canonical_json == freeze canonical_json == validator sha256_json),
* the Campaign 4 era controls (the historical pins DO reproduce),
* the Campaign 5 documented defect state (era-pinned so drift is impossible
  to miss and the pinned value is never silently rewritten),
* verify_config's fail-closed, write-free contract.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest  # noqa: F401  (kept for the tmp_path fixture contract)

WORKSPACE = Path(__file__).resolve().parents[1]

C4_CAPACITY_CONFIG = (
    "stat_validation_h10/freeze_2026_10_15/"
    "CAMPAIGN_4_CONFIG_FROZEN_2026_10_15.json")
C4_CAPACITY_PIN = (
    "49d73f672ae237a993343d30f867dce31867383294635afab120634d0ae49b83")
C4_ARCHIVE_CONFIG = (
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
    "CAMPAIGN_4_FINAL_ARCHIVE_2026-10-16/campaign_config.json")
C4_ARCHIVE_PIN = (
    "b4ced0e00493f7636efc74baee2424146cb1840233d2b48fda1061b8d50d86b4")
C5_LIVE_CONFIG = "autonomous_agent/state/campaign_config.json"
# Era-pinned 2026-10-25 (fingerprint provenance resolution): the live C5
# config bytes pin, its recorded-method recompute, and its (defective)
# protocol pin. Any future byte change to the live config, or any change of
# the canonicalization, fails these assertions LOUDLY instead of passing.
C5_LIVE_FILE_SHA = (
    "29c905aaf25012cdd20bf21270821f81f5a8e24b46b4a51163d2c65e2e9124a5")
C5_LIVE_RECOMPUTE = (
    "b20a4d9b147b17af5055e4531b392fc3f1652381fd3b7e28fffa7a1c0db2cff5")
C5_LIVE_PIN = (
    "553ac77f65b6b8afee852159fe654ea25b0116e490860e3e3153af937ce44327")

import sys
sys.path.insert(0, str(WORKSPACE))
from autonomous_agent import protocol_fingerprint as pf  # noqa: E402
from autonomous_agent.proposal_layer.schema import canonical_json as schema_cj  # noqa: E402
from autonomous_agent.campaign5_authorization import canonical_bytes  # noqa: E402


def _load(rel: str) -> dict:
    return json.loads((WORKSPACE / rel).read_text(encoding="utf-8"))


def test_canonicalization_implementations_agree() -> None:
    """All three shipped canonicalizations must be byte-identical on configs."""
    sample = _load(C4_ARCHIVE_CONFIG)
    a = schema_cj(sample)
    b = pf.canonical_json(sample)
    c = canonical_bytes(sample).decode("utf-8")
    assert a == b == c


def test_recorded_method_matches_convention_definition() -> None:
    """Convention input = config minus the identity keys (sha absent at hash
    time); hashing with the sha key present must not leak into the result."""
    sample = _load(C4_ARCHIVE_CONFIG)
    base = {k: v for k, v in sample.items()
            if k != "protocol_fingerprint"}
    base_no_sha = {k: v for k, v in base.items() if k != "protocol_sha256"}
    expected = hashlib.sha256(schema_cj(base_no_sha).encode("utf-8")).hexdigest()
    assert pf.recorded_method_fingerprint(sample) == expected
    assert pf.recorded_method_fingerprint(base) == expected


def test_c4_capacity_control_reproduces() -> None:
    config = _load(C4_CAPACITY_CONFIG)
    assert config["protocol_fingerprint"] == C4_CAPACITY_PIN
    assert pf.recorded_method_fingerprint(config) == C4_CAPACITY_PIN


def test_c4_archive_control_reproduces() -> None:
    config = _load(C4_ARCHIVE_CONFIG)
    assert config["protocol_fingerprint"] == C4_ARCHIVE_PIN
    assert pf.recorded_method_fingerprint(config) == C4_ARCHIVE_PIN


def test_c5_live_state_is_exactly_the_documented_defect() -> None:
    """Era-pinned: nothing repairs the C5 pin, and content drift fails here."""
    raw = (WORKSPACE / C5_LIVE_CONFIG).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == C5_LIVE_FILE_SHA
    config = _load(C5_LIVE_CONFIG)
    assert config["protocol_fingerprint"] == C5_LIVE_PIN
    assert config["protocol_sha256"] == C5_LIVE_PIN
    recompute = pf.recorded_method_fingerprint(config)
    assert recompute == C5_LIVE_RECOMPUTE
    assert recompute != C5_LIVE_PIN  # the open provenance defect, still open


def test_verify_config_classifies_all_era_records() -> None:
    summary = pf.verify_known_records(WORKSPACE)
    assert summary["status"] == "ok"
    assert summary["unexpected_mismatches"] == []
    statuses = {r["artifact"]: r["status"] for r in summary["results"]}
    assert statuses[C4_CAPACITY_CONFIG] == "reproduced"
    assert statuses[C4_ARCHIVE_CONFIG] == "reproduced"
    assert statuses[C5_LIVE_CONFIG] == "documented_defect_mismatch"


def test_verify_config_never_writes_and_fails_closed(tmp_path: Path) -> None:
    source = WORKSPACE / C5_LIVE_CONFIG
    target = tmp_path / "campaign_config.json"
    original = source.read_bytes()
    target.write_bytes(original)
    # intact copy: verification is read-only (snapshot artifact state around it)
    pre_stamp = (target.stat().st_mtime_ns, target.stat().st_size)
    report_intact = pf.verify_config(target)
    post_stamp = (target.stat().st_mtime_ns, target.stat().st_size)
    assert pre_stamp == post_stamp
    assert report_intact["status"] == "unexpected_mismatch"  # copy: no known era
    # Mutated copy: not a known era -> unexpected mismatch, fail-closed exit path.
    data = json.loads(original.decode("utf-8"))
    data["multiplicity_policy"]["n_boot"] = 1
    target.write_text(json.dumps(data), encoding="utf-8")
    report_mut = pf.verify_config(target)
    # no repair: the mutated file keeps its (bad) content; nothing was written
    assert json.loads(target.read_text(encoding="utf-8"))["multiplicity_policy"]["n_boot"] == 1
    assert report_mut["status"] == "unexpected_mismatch"
    assert report_mut["fingerprint_reproducible"] is False
    # verify remains read-only even on a mismatching artifact
    assert (target.stat().st_mtime_ns, target.stat().st_size) == (
        target.stat().st_mtime_ns, target.stat().st_size)


def test_verify_config_missing_file_is_unavailable(tmp_path: Path) -> None:
    report = pf.verify_config(tmp_path / "does_not_exist.json")
    assert report["status"] == "unavailable"
    # module CLI contract: mismatch exits nonzero (__main__ raises SystemExit)
    assert pf.main(["--root", str(tmp_path), "does_not_exist.json"]) == 1


def test_known_records_pin_table_cannot_drift_silently() -> None:
    """Every KNOWN_RECORDS pin must match the artifact it names."""
    for known in pf.KNOWN_RECORDS:
        config = _load(known["artifact"])
        assert known["pinned"] in (
            config.get("protocol_fingerprint"),
            config.get("protocol_sha256")), known["era"]
