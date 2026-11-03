"""One-command model autopsy: predictions CSV in, investigation report out.

Does everything the dashboard's New Investigation flow does, without clicks:
  1. Uploads your files (predictions CSV + optional training script / notes).
  2. Creates the investigation and loads artifact context.
  3. Runs the standard diagnostic battery (summary, metrics, calibration,
     validation, feature suspiciousness) against your score column.
  4. Generates the final report and prints where to view it.

Usage:
  py model_autopsy/auto_investigate.py --predictions preds.csv
      [--script train.py] [--title "My model"] [--question "What is wrong?"]
      [--score-column score] [--server http://127.0.0.1:8000]

The only work left for you: produce the predictions CSV (score + label
columns). If the model lives at a URL, hand the link to your assistant
and it will run the model and call this script for you.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import urllib.request
import uuid

TOOL_NAMES = [
    "artifact_summary",
    "classification_metrics",
    "calibration_and_error_analysis",
    "dataset_validation",
    "feature_target_suspiciousness",
]


def _req(server: str, method: str, path: str,
         body: bytes | None = None, ctype: str | None = None) -> dict:
    r = urllib.request.Request(server + path, data=body, method=method)
    if ctype:
        r.add_header("Content-Type", ctype)
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.load(resp)


def _post_json(server: str, path: str, payload: dict) -> dict:
    return _req(server, "POST", path, json.dumps(payload).encode(),
                "application/json")


def _upload(server: str, paths: list[str]) -> dict:
    boundary = uuid.uuid4().hex
    body = bytearray()
    for p in paths:
        name = os.path.basename(p)
        ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
        with open(p, "rb") as f:
            data = f.read()
        if not data:
            raise SystemExit(f"refusing to upload empty file: {p}")
        body += f'--{boundary}\r\n'.encode()
        body += (f'Content-Disposition: form-data; name="files"; '
                 f'filename="{name}"\r\n').encode()
        body += f'Content-Type: {ctype}\r\n\r\n'.encode()
        body += data + b'\r\n'
    body += f'--{boundary}--\r\n'.encode()
    return _req(server, "POST", "/api/uploads", bytes(body),
                f"multipart/form-data; boundary={boundary}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--predictions", required=True,
                    help="CSV with score + label columns")
    ap.add_argument("--script", default=None,
                    help="optional training/eval script (read-only provenance)")
    ap.add_argument("--title", default="Model investigation - auto")
    ap.add_argument("--question", default="Broad investigation: examine the "
                    "uploaded material and surface competing, falsifiable "
                    "failure hypotheses.")
    ap.add_argument("--score-column", default="score")
    ap.add_argument("--server", default="http://127.0.0.1:8000")
    args = ap.parse_args()

    files = [args.predictions] + ([args.script] if args.script else [])
    for p in files:
        if not os.path.isfile(p):
            raise SystemExit(f"not found: {p}")

    print(f"uploading {len(files)} file(s)...")
    up = _upload(args.server, files)
    pred = next(f["path"] for f in up["files"]
                if f["name"] == os.path.basename(args.predictions))
    print(f"  batch {up['batch']}:")
    for f in up["files"]:
        print(f"    {f['name']} ({f['bytes']} bytes, {f['kind']})")

    print("creating investigation...")
    inv = _post_json(args.server, "/api/investigations", {
        "mode": "ml", "title": args.title, "question": args.question,
        "predictions_path": pred,
    })
    iid = inv["id"]
    print(f"  id {iid}")

    print("loading context...")
    _post_json(args.server, f"/api/investigations/{iid}/context", {})

    print("running diagnostics...")
    for tool in TOOL_NAMES:
        targs: dict = {"predictions_path": pred}
        if tool in ("artifact_summary", "classification_metrics",
                    "calibration_and_error_analysis"):
            targs["score_column"] = args.score_column
        elif tool == "dataset_validation":
            targs["score_columns"] = [args.score_column]
        elif tool == "feature_target_suspiciousness":
            targs = {"feature_csv": pred, "label_csv": pred}
        try:
            r = _post_json(args.server,
                           f"/api/investigations/{iid}/tool",
                           {"tool_name": tool, "arguments": targs})
            res = r.get("result", {})
            aucs = f" auc={res['roc_auc']:.4f}" if "roc_auc" in res else ""
            print(f"  {tool}: ok{aucs}")
        except Exception as e:  # noqa: BLE001 - report, don't crash the batch
            print(f"  {tool}: FAILED ({e})")

    print("generating report...")
    rep = _post_json(args.server, f"/api/investigations/{iid}/report", {})
    r = rep["report"]
    print(f"  confirmed={len(r['confirmed'])} likely={len(r['likely'])} "
          f"rejected={len(r['rejected'])} unresolved={len(r['unresolved'])} "
          f"evidence={len(r['evidence_performed'])}")
    print(f"\nDone. View it: History -> {inv['title']} (id {iid[:8]}...)")


if __name__ == "__main__":
    sys.exit(main())
