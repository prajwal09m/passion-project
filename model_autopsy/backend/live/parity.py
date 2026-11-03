"""M14 Phase 4.3: live/offline parity harness (offline replay).

Replays a saved live trace's tool calls against the current
offline engine on the same artifact and compares outcomes.
Distinguishes model reasoning failures (same tools, different
conclusions) from infrastructure failures (tool outcomes differ
or were unavailable live).
"""
from __future__ import annotations

import json
from pathlib import Path


def replay(run_dir: str, session, inv) -> dict:
    d = Path(run_dir)
    try:
        actions = json.loads((d / "actions.json").read_text())
    except OSError as exc:
        return {"ok": False, "reason": f"no saved actions: {exc}"}
    from .. import engine as ENG
    rows = []
    for a in actions if isinstance(actions, list) else []:
        tool = a.get("tool_name") or a.get("tool")
        args = a.get("arguments") or {}
        if not tool or a.get("status") != "ran":
            rows.append({"tool": tool, "live": a.get("status"),
                         "replay": "skipped (not ran live)",
                         "match": None})
            continue
        try:
            out = ENG.run_tool(session, inv, tool, dict(args),
                               source_meta=True)
            live_res = a.get("result") or {}
            new_res = out.get("result") or {}
            match = (live_res.keys() == new_res.keys()) if (
                live_res and new_res) else out.get("ok")
            rows.append({"tool": tool, "live": "ran",
                         "replay": "ran" if out.get("ok")
                         else out.get("error"),
                         "match": bool(match),
                         "class": "model-or-infra-same"
                         if match else "infrastructure-divergence"})
        except Exception as exc:
            rows.append({"tool": tool, "live": "ran",
                         "replay": f"{type(exc).__name__}",
                         "match": False,
                         "class": "infrastructure-divergence"})
    same = sum(1 for r in rows if r.get("match") is True)
    return {"ok": True, "rows": rows,
            "parity": same / len(rows) if rows else None,
            "note": "match compares outcome keys, not conclusions; "
                    "conclusion gaps are model reasoning failures, "
                    "tool gaps are infrastructure failures"}
