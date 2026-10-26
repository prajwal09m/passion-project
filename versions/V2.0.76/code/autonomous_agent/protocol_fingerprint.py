"""Recompute-verify the campaign protocol fingerprint (recorded convention).

Recorded convention (CAMPAIGN_5_AUTHORIZATION_PREDECLARATION_2026_10_22.md,
"Digest Finalization Convention"; adopted at the Campaign 4 freeze and
production-verified there):

    protocol_fingerprint = SHA-256(canonical_json(config minus the
    ``protocol_fingerprint`` key)), computed before ``protocol_sha256``
    exists; then ``protocol_sha256 = protocol_fingerprint``.

Canonicalization is byte-identical across
``proposal_layer.schema.canonical_json``, the freeze-time canonicalization in
``stat_validation_h10/freeze_2026_10_22/freeze_campaign_5_config.py``, and the
authorization validator's ``sha256_json`` (sorted keys, compact separators,
``ensure_ascii=True``). A regression test pins this agreement.

Era-pinned knowledge (never silently "corrected" by this module):

* Campaign 4 (capacity freeze 2026-10-15): pin ``49d73f67...`` REPRODUCES from
  its frozen artifact content.
* Campaign 4 (final archive, pin basis d8bff195...): pin ``b4ced0e0...``
  REPRODUCES from the archived config content.
* Campaign 5: pin ``553ac77f...`` does NOT reproduce under the recorded method
  (owner decision 2026-10-23, documented-and-proceed; see the
  ``CAMPAIGN_5_POST_CAMPAIGN_AUDIT_2026_10_25.md`` and
  ``CAMPAIGN_5_LAUNCH_RECORD_2026_10_23.md`` section 7). The value stayed the
  signed authorization record's protocol pin; the non-reproducibility remains
  a recorded open defect. THIS MODULE REPORTS the mismatch; it never
  overwrites the expected fingerprint, regenerates a signature, or redefines
  the protocol to make verification pass.

This module performs no writes: verification only, fail-closed by contract.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

_ROOT_GUESS = Path(__file__).resolve().parents[1]

# Era-pinned records: (artifact path relative to the workspace root,
# era label, pinned protocol fingerprint, expected recompute result).
KNOWN_RECORDS: tuple[dict[str, Any], ...] = (
    {
        "era": "campaign-4-capacity-frozen-2026-10-15",
        "artifact":
            "stat_validation_h10/freeze_2026_10_15/"
            "CAMPAIGN_4_CONFIG_FROZEN_2026_10_15.json",
        "pinned": "49d73f672ae237a993343d30f867dce31867383294635afab120634d0ae49b83",
        "reproducible": True,
        "note": "C4 capacity refreeze control; reproduces under the recorded method.",
    },
    {
        "era": "campaign-4-final-archive-pin-basis-d8bff195",
        "artifact":
            "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
            "CAMPAIGN_4_FINAL_ARCHIVE_2026-10-16/campaign_config.json",
        "pinned": "b4ced0e00493f7636efc74baee2424146cb1840233d2b48fda1061b8d50d86b4",
        "reproducible": True,
        "note": "C4 live-config archive control; reproduces under the recorded method.",
    },
    {
        "era": "campaign-5-regime-error-analysis-2026-10-22",
        "artifact": "autonomous_agent/state/campaign_config.json",
        "pinned": "553ac77f65b6b8afee852159fe654ea25b0116e490860e3e3153af937ce44327",
        "reproducible": False,
        "note": ("C5 defect documented-and-proceed (owner decision 2026-10-23): the "
                 "pin is the signed record's protocol pin but has no preimage among "
                 "the recorded local config states under the recorded method."),
    },
)


def canonical_json(obj: Any) -> str:
    """Byte-identical canonicalization to schema.canonical_json for configs."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def recorded_method_fingerprint(config: Mapping[str, Any]) -> str:
    """SHA-256 over canonical_json(config minus the fingerprint/SHA keys).

    The convention hashes the content as it existed BEFORE ``protocol_sha256``
    was added, so both identity keys are excluded when present. Every other
    key -- including freeze-status metadata -- is part of the hashed input.
    """
    hashed = {key: value for key, value in config.items()
              if key not in ("protocol_fingerprint", "protocol_sha256")}
    payload = canonical_json(hashed).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _era_for(path: Path) -> dict[str, Any] | None:
    """Match a KNOWN_RECORDS era by path; accepts relative and absolute paths."""
    posix = path.as_posix()
    for known in KNOWN_RECORDS:
        artifact = known["artifact"]
        if posix == artifact or posix.endswith("/" + artifact):
            return known
    return None


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_config(path: Path) -> dict[str, Any]:
    """Recompute the fingerprint for one config file; report, never repair."""
    path = Path(path)
    report: dict[str, Any] = {"artifact": path.as_posix(), "exists": path.is_file()}
    if not path.is_file():
        report["status"] = "unavailable"
        return report
    raw_bytes = path.read_bytes()
    report["file_sha256"] = hashlib.sha256(raw_bytes).hexdigest()
    config = _load_json(path)
    if not isinstance(config, dict):
        report["status"] = "malformed"
        return report
    recompute = recorded_method_fingerprint(config)
    pinned_fp = config.get("protocol_fingerprint")
    pinned_sha = config.get("protocol_sha256")
    report["recomputed"] = recompute
    report["pinned_fingerprint"] = pinned_fp
    report["pinned_protocol_sha256"] = pinned_sha
    era = _era_for(path)
    report["era"] = era["era"] if era else None
    if era is not None:
        # A KNOWN_RECORDS pin must match what the artifact carries; drift
        # between the table and the artifact itself is reported, not papered over.
        report["era_pin_matches_artifact"] = era["pinned"] in (
            pinned_fp, pinned_sha)
    reproducible = (recompute == pinned_fp)
    report["fingerprint_reproducible"] = reproducible
    if reproducible:
        report["status"] = "reproduced"
    elif era is not None and not era["reproducible"] and report.get("era_pin_matches_artifact"):
        report["status"] = "documented_defect_mismatch"
        report["defect_note"] = era["note"]
    else:
        report["status"] = "unexpected_mismatch"
    return report


def verify_known_records(root: Path = _ROOT_GUESS) -> dict[str, Any]:
    """Verify every era-pinned config; used by tests and by -m invocation."""
    results = []
    for known in KNOWN_RECORDS:
        artifact = (root / known["artifact"])
        entry = verify_config(artifact)
        entry["artifact"] = known["artifact"]
        results.append(entry)
    unexpected = [r for r in results if r["status"] != "reproduced"]
    allowed_defects = [r for r in results
                       if r["status"] == "documented_defect_mismatch"]
    status = "ok" if (not unexpected or
                      set(r["status"] for r in unexpected) <= {"documented_defect_mismatch"}
                      ) else "unexpected_mismatch"
    return {
        "results": results,
        "unexpected_mismatches": [
            r["artifact"] for r in results if r["status"] == "unexpected_mismatch"],
        "documented_defects": [
            r["artifact"] for r in results if r["status"] == "documented_defect_mismatch"],
        "status": status,
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = _ROOT_GUESS
    if argv and argv[0] == "--root":
        root = Path(argv[1])
        argv = argv[2:]
    if argv:
        # Single-artifact mode: verify one config path (relative to root).
        report = verify_config(root / argv[0])
        print(json.dumps(report, sort_keys=True, indent=2))
        if report["status"] in ("reproduced", "documented_defect_mismatch"):
            return 0
        return 1
    summary = verify_known_records(root)
    print(json.dumps(summary, sort_keys=True, indent=2))
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
