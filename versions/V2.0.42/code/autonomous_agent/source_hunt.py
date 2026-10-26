"""Exhaustive read-only hunt for the exact V1.0.1 study source.

Complements restoration_scan.py (which matched *pinned hashes* only) with:
  * content-marker search (``demand_zone_study``) over every git blob in BOTH
    object stores (workspace .git and the OneDrive checkout's .git),
  * hash match against the *bytecode* pin (the preserved unreviewed V1.0.1
    .pyc, sha256 c7d23b68...) and the test-suite pin,
  * filesystem sweep of user/project locations for source-like candidates,
  * archive sweep (zip/tar/gz/docx...) for embedded candidates,
  * editor history / backup stores.

Every candidate is hashed raw + LF->CRLF + CRLF->LF and compared to the
historical code pin 29885c5f...2424b.  Nothing is modified.

Evidence: .restoration_tmp/source_hunt.json

Usage:  py -3 autonomous_agent/source_hunt.py
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import struct
import subprocess
import sys
import tarfile
import zipfile
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TMP = ROOT / ".restoration_tmp"
OUT = TMP / "source_hunt.json"

CODE_PIN = "29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b"
TEST_PIN = "e3f16447eae3a257dfc013d8dd53e2521414632c06f7b14a3d31f0ba3ddce456"
PYC_PIN = "c7d23b68e66d76f1f851887bc755b84b6bb1c8c424c24cccc8bf94de59d8f585"

PIN_LABELS = {CODE_PIN: "code_v1.0.1", TEST_PIN: "test_suite_v1.0.1", PYC_PIN: "pyc_v1.0.1_preserved"}

MARKER = b"demand_zone_study"
NAME_HINTS = ("demand_zone_study", "demand-zone-study", "study_v1")

FS_ROOTS = [
    pathlib.Path(r"C:\Prajwal MIT"),
    pathlib.Path(r"C:\Users\kamal"),
]
FS_EXTRA_DIRS = [
    pathlib.Path(r"C:\$Recycle.Bin"),
    pathlib.Path(r"C:\Windows\Temp"),
    pathlib.Path(r"C:\ProgramData"),
]
SKIP_DIRS = {
    "node_modules", ".git", "objects", "pycdc-src", "pylingual",
    "$WINDOWS.~BT", "WinSxS", "Packages",
}
CAND_EXT = {".py", ".pyw", ".pyc", ".pyo", ".bak", ".orig", ".old", ".swp", ".tmp", ".txt", ".py~"}
ARCHIVE_EXT = {".zip", ".tar", ".tgz", ".gz", ".7z", ".rar", ".bz2", ".docx", ".xlsx", ".pptx", ".jar"}
MAX_HASH_BYTES = 20 * 1024 * 1024


MAX_VARIANT_BYTES = 5 * 1024 * 1024  # line-ending transforms only for plausible source sizes


def variants(data: bytes) -> dict[str, bytes]:
    if len(data) > MAX_VARIANT_BYTES:
        return {"raw": data}
    return {
        "raw": data,
        "lf->crlf": data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"),
        "crlf->lf": data.replace(b"\r\n", b"\n"),
    }


class Recorder:
    def __init__(self) -> None:
        self.hits: list[dict] = []
        self.candidates: list[dict] = []
        self.marker_hits: list[dict] = []
        self.stats = {"files_hashed": 0, "blobs_hashed": 0, "archive_entries": 0, "errors": 0}

    def check(self, origin: str, name: str, data: bytes, extra: dict | None = None) -> None:
        record_base = {"origin": origin, "name": name, "bytes": len(data)}
        if extra:
            record_base.update(extra)
        try:
            for variant_name, blob in variants(data).items():
                digest = hashlib.sha256(blob).hexdigest()
                label = PIN_LABELS.get(digest)
                if label:
                    self.hits.append({**record_base, "sha256": digest, "pin": label,
                                      "line_ending_variant": variant_name})
                    break
            else:
                digest = hashlib.sha256(data).hexdigest()
                if MARKER in data:
                    kind = "pyc" if data[:4] in (b"\xcb\r\r\n", b"\x6f\r\r\n") or data[:2] in (b"\x16\x0d",) else "text"
                    self.marker_hits.append({**record_base, "sha256": digest, "marker_kind": kind,
                                             "line_ending_variants": {
                                                 vn: hashlib.sha256(vb).hexdigest()
                                                 for vn, vb in variants(data).items()}})
        except Exception as exc:  # noqa: BLE001 - evidence tooling
            self.stats["errors"] += 1
            self.candidates.append({**record_base, "error": repr(exc)})


def is_candidate_name(path: pathlib.Path) -> bool:
    low = path.name.lower()
    return any(h in low for h in NAME_HINTS) or path.suffix.lower() in CAND_EXT


# --------------------------------------------------------------------------
# git objects
# --------------------------------------------------------------------------

def progress(msg: str) -> None:
    print(msg, flush=True)


def scan_git_objects(rec: Recorder, repo: pathlib.Path, label: str) -> None:
    progress(f"[git:{label}] listing objects...")
    try:
        listing = subprocess.run(
            ["git", "cat-file", "--batch-all-objects", "--batch-check"],
            cwd=repo, capture_output=True, text=True, check=True,
        ).stdout
    except Exception as exc:  # noqa: BLE001
        rec.candidates.append({"origin": label, "error": f"cat-file listing failed: {exc}"})
        return
    oids = [line.split()[0] for line in listing.splitlines() if line.strip()]
    proc = subprocess.Popen(
        ["git", "cat-file", "--batch"], cwd=repo,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    )
    assert proc.stdin and proc.stdout
    for i, oid in enumerate(oids):
        proc.stdin.write((oid + "\n").encode())
        proc.stdin.flush()
        header = proc.stdout.readline().decode().split()
        if len(header) < 3 or header[1] == "missing":
            continue
        size = int(header[2])
        data = proc.stdout.read(size)
        proc.stdout.read(1)
        if header[1] == "blob":
            rec.stats["blobs_hashed"] += 1
            rec.check(f"git-objects:{label}", oid, data, {"git_oid": oid})
        if i % 5000 == 0:
            progress(f"[git:{label}] {i}/{len(oids)} objects")
    proc.stdin.close()
    proc.wait()
    progress(f"[git:{label}] done: {rec.stats['blobs_hashed']} blobs so far")


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
    byte = buf[pos]
    pos += 1
    value = byte & 0x7F
    while byte & 0x80:
        byte = buf[pos]
        pos += 1
        value = ((value + 1) << 7) | (byte & 0x7F)
    return value, pos


def scan_orphan_pack(rec: Recorder, pack: pathlib.Path) -> dict:
    raw = pack.read_bytes()
    if raw[:4] != b"PACK":
        return {"pack": str(pack), "error": "bad signature"}
    _version, total = struct.unpack(">II", raw[4:12])
    pos = 12
    entries: dict[int, tuple[int, bytes]] = {}
    by_sha1: dict[str, bytes] = {}
    deltas: list[tuple] = []
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
            if obj_type == 6:
                base_off, pos = _read_ofs_offset(raw, pos)
                d = zlib.decompressobj()
                data = d.decompress(raw[pos:])
                pos = len(raw) - len(d.unused_data)
                deltas.append((start, obj_type, data, start - base_off))
            elif obj_type == 7:
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
                if obj_type == 3:
                    by_sha1[hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()] = data
            parsed += 1
        except Exception as exc:  # noqa: BLE001
            truncated = f"parse stopped at byte {start}: {exc}"
            break

    def apply_delta(base: bytes, delta: bytes) -> bytes:
        p = 0
        _src, p = _read_varint(delta, p)
        _dst, p = _read_varint(delta, p)
        out = bytearray()
        while p < len(delta):
            ctrl = delta[p]
            p += 1
            if ctrl & 0x80:
                off = 0
                size = 0
                for i, mask in enumerate((0x01, 0x02, 0x04, 0x08)):
                    if ctrl & mask:
                        off |= delta[p] << (8 * i)
                        p += 1
                for i, mask in enumerate((0x10, 0x20, 0x40)):
                    if ctrl & mask:
                        size |= delta[p] << (8 * i)
                        p += 1
                size = size or 0x10000
                out += base[off:off + size]
            else:
                out += delta[p:p + ctrl]
                p += ctrl
        return bytes(out)

    resolved = 0
    for offset, _otype, delta, base in deltas:
        base_data = entries.get(base)[1] if isinstance(base, int) and base in entries else (
            by_sha1.get(base) if isinstance(base, str) else None)
        if base_data is None:
            continue
        try:
            entries[offset] = (3, apply_delta(base_data, delta))
            resolved += 1
        except Exception:  # noqa: BLE001
            continue

    for _otype, data in entries.values():
        rec.stats["blobs_hashed"] += 1
        rec.check(f"orphan-pack:{pack.name}", "-", data)

    return {"pack": pack.name, "declared_objects": total, "parsed_objects": parsed,
            "deltas": len(deltas), "deltas_resolved": resolved, "truncated": truncated,
            "file_bytes": len(raw), "unparsed_bytes": max(0, len(raw) - pos)}


# --------------------------------------------------------------------------
# filesystem + archives
# --------------------------------------------------------------------------

def scan_filesystem(rec: Recorder) -> None:
    for root in FS_ROOTS + FS_EXTRA_DIRS:
        if not root.exists():
            continue
        progress(f"[fs] walking {root} ...")
        for dirpath, dirnames, filenames in os.walk(root, onerror=lambda _e: None):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                path = pathlib.Path(dirpath) / fname
                try:
                    st = path.stat()
                except OSError:
                    continue
                name_hit = any(h in fname.lower() for h in NAME_HINTS)
                if not name_hit and path.suffix.lower() not in CAND_EXT:
                    continue
                if st.st_size > MAX_HASH_BYTES and not name_hit:
                    continue
                try:
                    data = path.read_bytes()
                except OSError:
                    continue
                rec.stats["files_hashed"] += 1
                rec.check("filesystem", str(path), data, {"path": str(path), "mtime": int(st.st_mtime)})
        progress(f"[fs] {root} done: {rec.stats['files_hashed']} files hashed")


def scan_archives(rec: Recorder) -> None:
    for root in FS_ROOTS:
        if not root.exists():
            continue
        progress(f"[archives] walking {root} ...")
        for dirpath, dirnames, filenames in os.walk(root, onerror=lambda _e: None):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                path = pathlib.Path(dirpath) / fname
                low = fname.lower()
                if not any(low.endswith(ext) for ext in ARCHIVE_EXT):
                    continue
                if path.stat().st_size > 400 * 1024 * 1024:
                    continue
                try:
                    if zipfile.is_zipfile(path):
                        with zipfile.ZipFile(path) as zf:
                            for info in zf.infolist():
                                if info.is_dir():
                                    continue
                                name_hit = any(h in info.filename.lower() for h in NAME_HINTS)
                                ext_hit = info.filename.lower().endswith((".py", ".pyc", ".pyw"))
                                if not name_hit and not ext_hit:
                                    continue
                                if info.file_size > MAX_HASH_BYTES:
                                    continue
                                data = zf.read(info)
                                rec.stats["archive_entries"] += 1
                                rec.check(f"archive:{path}", info.filename, data,
                                          {"archive": str(path)})
                    elif tarfile.is_tarfile(path):
                        with tarfile.open(path) as tf:
                            for member in tf.getmembers():
                                if not member.isfile():
                                    continue
                                name_hit = any(h in member.name.lower() for h in NAME_HINTS)
                                ext_hit = member.name.lower().endswith((".py", ".pyc", ".pyw"))
                                if not name_hit and not ext_hit:
                                    continue
                                if member.size > MAX_HASH_BYTES:
                                    continue
                                f = tf.extractfile(member)
                                if f is None:
                                    continue
                                data = f.read()
                                rec.stats["archive_entries"] += 1
                                rec.check(f"archive:{path}", member.name, data,
                                          {"archive": str(path)})
                except Exception as exc:  # noqa: BLE001
                    rec.stats["errors"] += 1
                    rec.candidates.append({"origin": "archive", "path": str(path), "error": repr(exc)})


def scan_editor_stores(rec: Recorder) -> None:
    stores = [
        pathlib.Path(r"C:\Users\kamal\AppData\Roaming\Devin\User\History"),
        pathlib.Path(r"C:\Users\kamal\AppData\Roaming\Code\User\History"),
        pathlib.Path(r"C:\Users\kamal\AppData\Roaming\Devin\Backups"),
        pathlib.Path(r"C:\Users\kamal\AppData\Roaming\Code\Backups"),
        pathlib.Path(r"C:\Users\kamal\AppData\Roaming\Notepad++\backup"),
    ]
    for store in stores:
        if not store.exists():
            continue
        for dirpath, _dirnames, filenames in os.walk(store, onerror=lambda _e: None):
            for fname in filenames:
                path = pathlib.Path(dirpath) / fname
                try:
                    if path.stat().st_size > MAX_HASH_BYTES:
                        continue
                    data = path.read_bytes()
                except OSError:
                    continue
                rec.stats["files_hashed"] += 1
                rec.check(f"editor-store:{store.name}", str(path), data, {"path": str(path)})


def main() -> int:
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    TMP.mkdir(exist_ok=True)
    rec = Recorder()
    pack_reports: list[dict] = []

    if phase in ("all", "git"):
        scan_git_objects(rec, ROOT, "workspace")
    if phase in ("all", "onedrive-git"):
        onedrive = pathlib.Path(r"C:\Users\kamal\OneDrive\Documents\GitHub\passion-project")
        if onedrive.exists():
            scan_git_objects(rec, onedrive, "onedrive-checkout")
    if phase in ("all", "packs"):
        for pack in sorted((ROOT / ".git/objects/pack").glob("tmp_pack_*")):
            pack_reports.append(scan_orphan_pack(rec, pack))
    if phase in ("all", "fs"):
        scan_filesystem(rec)
    if phase in ("all", "archives"):
        scan_archives(rec)
    if phase in ("all", "editors"):
        scan_editor_stores(rec)

    report = {
        "code_pin": CODE_PIN,
        "test_pin": TEST_PIN,
        "pyc_pin": PYC_PIN,
        "stats": rec.stats,
        "pin_hits": rec.hits,
        "marker_hit_count": len(rec.marker_hits),
        "marker_hits": rec.marker_hits[:200],
        "errors": rec.candidates,
        "orphan_packs": pack_reports,
        "phase": phase,
    }
    out = OUT if phase == "all" else OUT.with_name(f"source_hunt_{phase}.json")
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"stats: {rec.stats}")
    print(f"PIN HITS: {len(rec.hits)}")
    for hit in rec.hits:
        print("   MATCH", hit["pin"], hit["line_ending_variant"], hit["origin"], hit.get("path", hit.get("name")))
    print(f"marker hits (files containing 'demand_zone_study'): {len(rec.marker_hits)}")
    for m in rec.marker_hits[:40]:
        print("   marker:", m["origin"], m["name"][:110], m["bytes"])
    for pr in pack_reports:
        print("orphan pack:", pr)
    print(f"errors: {len(rec.candidates)}")
    for err in rec.candidates[:10]:
        print("   ", err)
    print(f"evidence: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
