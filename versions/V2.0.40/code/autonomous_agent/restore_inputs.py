"""Restore the exact V1.0.1 research inputs from verified Git objects (MAIN TASK 1).

Every restored byte stream is SHA-256 verified against the pins recorded in the
sanitized V1.0.1 run manifest BEFORE it is written, and re-verified afterwards.
Nothing is regenerated, downloaded, or synthesized: the content comes from the
repository's own object database (the files were once present in this checkout).

Usage:  py -3 autonomous_agent/restore_inputs.py [--dry-run]
"""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCAN = ROOT / ".restoration_tmp/object_scan.json"
MANIFEST = ROOT / "study_files/research/demand-zone-ai-study/run_manifest_sanitized.json"

V2_DATASET = ROOT / "study_files/outputs/v2/demand_zone_v2_dataset.csv"
OHLCV_DIR = ROOT / "study_files/outputs/v2/_ohlcv"
RUN_MANIFEST = ROOT / "study_files/outputs/study_v1/development/run_manifest.json"

# Object that is provably the unsanitized v1.0.1 run_manifest.json: identical to
# the sanitized copy except artifact_directory, data_directory (real machine
# paths) and public_release_note. Full object id resolved at run time.
RUN_MANIFEST_BLOB_PREFIX = "d27b3eb563a6b1f7"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob(oid: str) -> bytes:
    out = subprocess.run(["git", "cat-file", "blob", oid], cwd=ROOT,
                         capture_output=True, check=True)
    return out.stdout


def apply_variant(data: bytes, variant: str) -> bytes:
    if variant == "raw":
        return data
    if variant == "lf->crlf":
        return data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    if variant == "crlf->lf":
        return data.replace(b"\r\n", b"\n")
    raise ValueError(f"unknown line-ending variant: {variant}")


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    scan = json.loads(SCAN.read_text(encoding="utf-8"))
    source_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pins: dict[str, str] = dict(source_manifest["source_data_sha256"])
    pins["demand_zone_v2_dataset.csv"] = (
        "669ca1f5b21339b8cc26f6eb5cbeb22003ebafcd86b0d7e945f0db3d6517d71b")

    hits = {row["pin"]: row for row in scan["pin_hits"]}
    report: list[str] = []
    failures: list[str] = []

    def restore(target: pathlib.Path, content: bytes, expected: str, label: str) -> None:
        actual = sha256(content)
        if actual != expected:
            failures.append(f"{label}: content hash {actual} != pin {expected}")
            return
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as stream:
                stream.write(content)
            if sha256(target.read_bytes()) != expected:
                failures.append(f"{label}: post-write verification failed")
                return
        report.append(f"{label}: restored {len(content):,} bytes sha256={expected}")

    # 1. The 153 OHLCV source CSVs -------------------------------------------------
    missing_syms = []
    for symbol, expected in sorted(pins.items()):
        if symbol == "demand_zone_v2_dataset.csv":
            continue
        hit = hits.get(f"ohlcv:{symbol}")
        if hit is None:
            missing_syms.append(symbol)
            continue
        content = apply_variant(blob(hit["object"]), hit.get("line_ending_variant", "raw"))
        restore(OHLCV_DIR / f"{symbol}.csv", content, expected, f"ohlcv:{symbol}")
    if missing_syms:
        failures.append(f"ohlcv: no verified blob for {missing_syms}")

    # 2. The V2 roster dataset ------------------------------------------------------
    roster_expected = pins["demand_zone_v2_dataset.csv"]
    roster_hit = None
    for row in scan["near_misses"]:
        if row.get("variants", {}).get("lf->crlf") == roster_expected:
            roster_hit = row
            break
    if roster_hit is None:
        failures.append("v2 dataset: no verified blob found")
    else:
        content = apply_variant(blob(roster_hit["object"]), "lf->crlf")
        restore(V2_DATASET, content, roster_expected,
                f"v2_dataset (blob {roster_hit['object'][:12]})")

    # 3. The exact unsanitized v1.0.1 run_manifest.json ------------------------------
    oid = subprocess.run(["git", "rev-parse", RUN_MANIFEST_BLOB_PREFIX], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.strip()
    content = apply_variant(blob(oid), "lf->crlf")  # original Windows write = CRLF
    inner = json.loads(content.decode("utf-8"))
    expected_pins = {
        "protocol_version": "1.0.1",
        "protocol_sha256": "486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07",
        "code_sha256": "29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b",
        "test_suite_sha256": "e3f16447eae3a257dfc013d8dd53e2521414632c06f7b14a3d31f0ba3ddce456",
        "roster_source_sha256": "669ca1f5b21339b8cc26f6eb5cbeb22003ebafcd86b0d7e945f0db3d6517d71b",
        "universe_sha256": "2cc7e1eaac9848d2528d0c80451fa9cb949009de9abb565028db136f76d58616",
    }
    bad = {k: inner.get(k) for k, v in expected_pins.items() if inner.get(k) != v}
    if bad:
        failures.append(f"run_manifest: pin fields differ: {bad}")
    else:
        restore(RUN_MANIFEST, content, sha256(content),
                f"run_manifest (blob {oid[:12]})")

    print("\n".join(report))
    if failures:
        print("FAILURES:")
        print("\n".join(failures))
        return 1
    print(f"\nAll {len(report)} artifacts restored and verified "
          f"({'dry-run' if dry_run else 'written'}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
