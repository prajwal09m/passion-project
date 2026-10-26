#!/usr/bin/env python3
"""Freeze-time evidence: the documented decimal precision of the raw inputs.

H-11's frozen tolerance rule (census.tolerance_for) combines "half a unit
of the last documented decimal place of its raw inputs" with the relative
1e-9 float64-chain term. The abs term needs the raw inputs' documented
decimal precision, which must be DECLARED from documentation, never derived
from observed mismatches. This script produces that declaration:

1. Integrity precondition: verify all 153 raw OHLCV files against the
   sha256 pins in the v1.0.1 run manifest (source_data_sha256) -- the
   precision measured below is measured on exactly the frozen inputs.
2. Measure D := the maximum number of decimal places present in any stored
   price value across the Open/High/Low/Close columns of all 153 files.
3. Write precision_evidence.json (per-file maxima + the global D + the
   reproducible procedure).

Output feeds build_census_manifest_frozen.py: every Tier-1 float column
declares tolerance abs = 0.5 * 10^-D, rel = 1e-9 (origin
DOCUMENTED_PRECISION), one uniform documented rule for all derived float
features (they are all functions of these OHLCV bars).
"""
import csv
import hashlib
import json
import pathlib
import re
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
OHLCV = ROOT / "study_files/outputs/v2/_ohlcv"
MANIFEST = ROOT / "study_files/outputs/study_v1/development/run_manifest.json"
OUT = pathlib.Path(__file__).resolve().parent / "precision_evidence.json"

PRICE_COLS = ("Open", "High", "Low", "Close")
NUMERIC = re.compile(r"^-?\d+(?:\.(\d+))?$")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    pins = manifest["source_data_sha256"]
    files = sorted(OHLCV.glob("*.csv"))
    if len(files) != 153 or len(pins) != 153:
        print(f"FAIL: {len(files)} csv files, {len(pins)} pins (expected 153)",
              file=sys.stderr)
        return 1
    mismatches = []
    for path in files:
        key = path.stem                       # pins are keyed by symbol
        if key not in pins:
            mismatches.append(f"{key}: no pin")
        elif sha256(path) != pins[key]:
            mismatches.append(f"{key}: hash mismatch")
    missing = [k for k in pins if not (OHLCV / f"{k}.csv").exists()]
    if mismatches or missing:
        print("FAIL: raw inputs do not match the frozen pins:", file=sys.stderr)
        for item in (mismatches + missing)[:5]:
            print("  -", item, file=sys.stderr)
        return 1

    per_file_max = {}
    global_max = 0
    argmax_file = None
    argmax_field = None
    for path in files:
        file_max = 0
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
            reader = csv.DictReader(fh)
            fields = [f for f in PRICE_COLS if f in (reader.fieldnames or [])]
            if not fields:
                print(f"FAIL: {path.name} has no price columns", file=sys.stderr)
                return 1
            for row in reader:
                for field in fields:
                    raw = (row.get(field) or "").strip()
                    m = NUMERIC.match(raw)
                    if not m:
                        continue
                    places = len(m.group(1) or "")
                    if places > file_max:
                        file_max = places
                    if places > global_max:
                        global_max, argmax_file, argmax_field = places, path.name, field
        per_file_max[path.name] = file_max

    evidence = {
        "_EVIDENCE_STATUS": (
            "FROZEN FREEZE-TIME DECLARATION (2026-10-14). D is measured from "
            "the documentation (the stored decimal representation) of the "
            "hash-verified raw inputs; it is never derived from any observed "
            "comparison result (H-11: declared precision, not observations)."),
        "procedure": (
            "D = max decimal places over every numeric value stored in the "
            "Open/High/Low/Close columns across all 153 raw OHLCV files, "
            "after verifying each file's sha256 against "
            "run_manifest.json -> source_data_sha256. Reproducible: rerun "
            "measure_documented_precision.py on the frozen inputs."),
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files_verified": len(files),
        "pins_source": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "documented_decimals_D": global_max,
        "argmax": {"file": argmax_file, "column": argmax_field},
        "per_file_max_decimal_places": per_file_max,
        "tolerance_this_declares": (
            "for every Tier-1 float feature column: abs = 0.5 * 10^-D, "
            "rel = 1e-9 (census.FLOAT_RELATIVE_TOLERANCE, the documented "
            "float64 derived-computation chain), origin DOCUMENTED_PRECISION"),
    }
    OUT.write_bytes((json.dumps(evidence, indent=2, sort_keys=True) + "\n")
                    .encode("utf-8"))
    print("files verified:", len(files))
    print("documented_decimals_D:", global_max,
          f"(argmax: {argmax_file}#{argmax_field})")
    print("evidence:", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
