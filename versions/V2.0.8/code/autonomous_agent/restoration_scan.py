"""Exhaustive local search for the exact V1.0.1 research inputs (MAIN TASK 1).

Hashes every Git object reachable AND unreachable (loose, packed, and the
orphaned temporary packs) against the pinned SHA-256 values recorded in the
sanitized V1.0.1 run manifest, and sniffs object contents for near-miss
candidates (run_manifest.json, the V2 roster dataset, OHLCV caches).

Read-only: nothing in the repository is modified. Evidence is written to
.restoration_tmp/object_scan.json.

Usage:  py -3 autonomous_agent/restoration_scan.py
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import struct
import subprocess
import sys
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TMP = ROOT / ".restoration_tmp"
MANIFEST = ROOT / "study_files/research/demand-zone-ai-study/run_manifest_sanitized.json"

PIN_ARTIFACTS = {
    "event_table.csv": "232de7db65c92bec249be801e593acdaa822ecd0b13eb0cd32b7eeaced85a4d0",
    "oof_predictions.csv": "011530761a19016f430232f631a9c3b0199ac17aff297e491d8d50d4b1508829",
}
PIN_MISC = {
    "protocol_v1.0.1": "486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07",
    "code_v1.0.1": "29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b",
    "test_suite_v1.0.1": "e3f16447eae3a257dfc013d8dd53e2521414632c06f7b14a3d31f0ba3ddce456",
    "roster_source_v2_dataset": "669ca1f5b21339b8cc26f6eb5cbeb22003ebafcd86b0d7e945f0db3d6517d71b",
    "universe": "2cc7e1eaac9848d2528d0c80451fa9cb949009de9abb565028db136f76d58616",
}


def load_pins() -> dict[str, str]:
    """sha256 -> label for every known-good artifact hash."""
    pins: dict[str, str] = {}
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for symbol, digest in manifest.get("source_data_sha256", {}).items():
        pins[digest] = f"ohlcv:{symbol}"
    for name, digest in manifest.get("artifact_sha256", {}).items():
        pins[digest] = f"artifact:{name}"
    for name, digest in manifest.get("model_artifacts_sha256", {}).items():
        pins[digest] = f"model:{name}"
    feature_arms = manifest.get("feature_arms_sha256", {})
    if isinstance(feature_arms, dict):
        for name, digest in feature_arms.items():
            pins[digest] = f"feature_arm:{name}"
    elif isinstance(feature_arms, str):
        pins[feature_arms] = "feature_arms"
    for label, digest in PIN_ARTIFACTS.items():
        pins.setdefault(digest, f"artifact:{label}")
    for label, digest in PIN_MISC.items():
        pins.setdefault(digest, label)
    return pins


def sniff(head: bytes) -> dict | None:
    """Classify content as a near-miss candidate worth reporting."""
    text = head[:4096]
    if b'"protocol_id"' in text and b'"artifact_sha256"' in text:
        return {"kind": "run_manifest_json"}
    if b'"protocol_id"' in text:
        return {"kind": "protocol_or_manifest_json"}
    first = text.split(b"\n", 1)[0].lower()
    if b"ticker" in first and (b"date" in first or b"signal" in first):
        return {"kind": "ticker_dataset_csv", "header": first[:300].decode("latin1")}
    if all(tok in first for tok in (b"open", b"high", b"low", b"close")):
        return {"kind": "ohlcv_csv", "header": first[:300].decode("latin1")}
    return None


class Matcher:
    def __init__(self, pins: dict[str, str]) -> None:
        self.pins = pins
        self.hits: list[dict] = []
        self.near: list[dict] = []
        self.count = 0
        self.bytes = 0

    def feed(self, origin: str, oid: str, data: bytes) -> None:
        self.count += 1
        self.bytes += len(data)
        digest = hashlib.sha256(data).hexdigest()
        label = self.pins.get(digest)
        variant = "raw"
        if label is None and b"\n" in data[:4096]:
            # Git may normalize line endings on commit; retry both directions.
            for name, alt in (
                ("lf->crlf", data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")),
                ("crlf->lf", data.replace(b"\r\n", b"\n")),
            ):
                alt_digest = hashlib.sha256(alt).hexdigest()
                if self.pins.get(alt_digest):
                    digest, label, variant = alt_digest, self.pins[alt_digest], name
                    break
        if label:
            self.hits.append({"origin": origin, "object": oid, "sha256": digest,
                              "pin": label, "line_ending_variant": variant})
        head = data[:4096]
        if label is None and len(data) > 200:
            info = sniff(head)
            if info:
                record = {"origin": origin, "object": oid, "sha256": digest,
                          "bytes": len(data), **info}
                if info["kind"] != "ohlcv_csv":
                    record["variants"] = {
                        name: hashlib.sha256(transform).hexdigest()
                        for name, transform in (
                            ("lf->crlf", data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")),
                            ("crlf->lf", data.replace(b"\r\n", b"\n")),
                        )
                    }
                    record["preview"] = data[:600].decode("latin1")
                    self.near.append(record)
                elif len([n for n in self.near if n["kind"] == "ohlcv_csv"]) < 20:
                    self.near.append(record)


def scan_cat_file(matcher: Matcher) -> None:
    """Hash every object the object database knows about (loose + packed)."""
    listing = subprocess.run(
        ["git", "cat-file", "--batch-all-objects", "--batch-check"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    oids = [line.split()[0] for line in listing.splitlines() if line.strip()]
    proc = subprocess.Popen(
        ["git", "cat-file", "--batch"], cwd=ROOT,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    )
    assert proc.stdin and proc.stdout
    for oid in oids:
        proc.stdin.write((oid + "\n").encode())
        proc.stdin.flush()
        header = proc.stdout.readline().decode().split()
        if len(header) < 3 or header[1] == "missing":
            continue
        size = int(header[2])
        data = proc.stdout.read(size)
        proc.stdout.read(1)  # trailing newline
        if header[1] == "blob":
            matcher.feed("object-db", oid, data)
    proc.stdin.close()
    proc.wait()


def _read_varint(buf: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        byte = buf[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            return value, pos


def _read_ofs_offset(buf: bytes, pos: int) -> tuple[int, int]:
    """Decode the OFS_DELTA base offset (different varint than the size)."""
    byte = buf[pos]
    pos += 1
    value = byte & 0x7F
    while byte & 0x80:
        byte = buf[pos]
        pos += 1
        value = ((value + 1) << 7) | (byte & 0x7F)
    return value, pos


def scan_orphan_pack(matcher: Matcher, pack: pathlib.Path) -> dict:
    """Parse an orphaned/unindexed pack file and hash its objects."""
    raw = pack.read_bytes()
    if raw[:4] != b"PACK":
        return {"pack": str(pack), "error": "bad signature"}
    _version, total = struct.unpack(">II", raw[4:12])
    pos = 12
    entries: dict[int, tuple[int, bytes]] = {}  # offset -> (type, decompressed)
    by_sha1: dict[str, bytes] = {}               # git oid -> content (bases for REF_DELTA)
    deltas: list[tuple] = []                     # (offset, type, delta bytes, base)
    parsed = 0
    truncated = None
    while parsed < total:
        start = pos
        try:
            byte = raw[pos]
            pos += 1
            obj_type = (byte >> 4) & 0x7
            size = byte & 0x0F
            shift = 4
            while byte & 0x80:
                byte = raw[pos]
                pos += 1
                size |= (byte & 0x7F) << shift
                shift += 7
            if obj_type == 6:  # OFS_DELTA
                base_off, pos = _read_ofs_offset(raw, pos)
                base_offset = start - base_off
                d = zlib.decompressobj()
                data = d.decompress(raw[pos:])
                pos = len(raw) - len(d.unused_data)
                deltas.append((start, obj_type, data, base_offset))
            elif obj_type == 7:  # REF_DELTA
                base_sha = raw[pos:pos + 20].hex()
                pos += 20
                d = zlib.decompressobj()
                data = d.decompress(raw[pos:])
                pos = len(raw) - len(d.unused_data)
                deltas.append((start, obj_type, data, base_sha))
            else:
                d = zlib.decompressobj()
                data = d.decompress(raw[pos:])
                pos = len(raw) - len(d.unused_data)
                entries[start] = (obj_type, data)
                if obj_type == 3:  # blob -> index by git oid for REF_DELTA bases
                    by_sha1[hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()] = data
            parsed += 1
        except Exception as exc:  # noqa: BLE001 - evidence tooling
            truncated = f"parse stopped at byte {start}: {exc}"
            break

    def apply_delta(base: bytes, delta: bytes) -> bytes:
        pos = 0
        _src_size, pos = _read_varint(delta, pos)
        _dst_size, pos = _read_varint(delta, pos)
        out = bytearray()
        while pos < len(delta):
            ctrl = delta[pos]
            pos += 1
            if ctrl & 0x80:
                off = 0
                size = 0
                for i, mask in enumerate((0x01, 0x02, 0x04, 0x08)):
                    if ctrl & mask:
                        off |= delta[pos] << (8 * i)
                        pos += 1
                for i, mask in enumerate((0x10, 0x20, 0x40)):
                    if ctrl & mask:
                        size |= delta[pos] << (8 * i)
                        pos += 1
                size = size or 0x10000
                out += base[off:off + size]
            else:
                out += delta[pos:pos + ctrl]
                pos += ctrl
        return bytes(out)

    resolved = 0
    for item in deltas:
        offset, _otype, delta, base = item
        if isinstance(base, int):
            hit = entries.get(base)
            base_data = hit[1] if hit else None
        else:
            base_data = by_sha1.get(base)
        if base_data is None:
            continue
        try:
            data = apply_delta(base_data, delta)
        except Exception:  # noqa: BLE001
            continue
        entries[offset] = (3, data)  # treat as blob content for matching
        resolved += 1

    for _otype, data in entries.values():
        matcher.feed(f"orphan-pack:{pack.name}", "-", data)

    kinds: dict[str, int] = {}
    for item in matcher.near:
        kinds[item["kind"]] = kinds.get(item["kind"], 0) + 1

    return {"pack": pack.name, "declared_objects": total, "parsed_objects": parsed,
            "deltas": len(deltas), "deltas_resolved": resolved, "truncated": truncated}


def scan_loose_tmp(matcher: Matcher) -> None:
    for path in (ROOT / ".git/objects").glob("*/*"):
        name = path.name
        if len(name) != 38 or "tmp" in name:
            try:
                data = zlib.decompress(path.read_bytes())
            except Exception:  # noqa: BLE001
                continue
            matcher.feed("loose-tmp", name, data)


def main() -> int:
    TMP.mkdir(exist_ok=True)
    pins = load_pins()
    matcher = Matcher(pins)
    scan_cat_file(matcher)
    pack_reports = []
    for pack in sorted((ROOT / ".git/objects/pack").glob("tmp_pack_*")):
        pack_reports.append(scan_orphan_pack(matcher, pack))
    scan_loose_tmp(matcher)

    kinds: dict[str, int] = {}
    for item in matcher.near:
        kinds[item["kind"]] = kinds.get(item["kind"], 0) + 1
    report = {
        "pins_checked": len(pins),
        "objects_hashed": matcher.count,
        "bytes_hashed": matcher.bytes,
        "pin_hits": matcher.hits,
        "near_miss_kinds": kinds,
        "near_misses": matcher.near,
        "orphan_packs": pack_reports,
    }
    out = TMP / "object_scan.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"objects hashed: {matcher.count} ({matcher.bytes / 1e6:.1f} MB)")
    print(f"PIN HITS: {len(matcher.hits)}")
    for hit in matcher.hits[:40]:
        print("  ", hit["pin"], hit["origin"], hit["object"][:12])
    print(f"near misses: {len(matcher.near)}")
    for near in matcher.near[:15]:
        print("  ", near["kind"], near["bytes"], near.get("header", "")[:80])
    for pr in pack_reports:
        print("orphan pack:", pr)
    print(f"evidence: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
