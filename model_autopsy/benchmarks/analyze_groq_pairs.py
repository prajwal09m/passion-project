"""Read-only trace extraction for the five Groq paired pilots (pilots 1-5).

The ledgers under `phase_d_groq_20b_pilot*.json` record rounds, finish
reasons, summary validity and backend counters, but not the ordered
evidence. Their `sandbox_db` paths still exist, so the actual investigations
(actions, events, hypotheses, summary payloads) are available for
evidence-based comparison instead of inferring behaviour from summary prose.

This script touches NOTHING: opens the pilot JSON read-only, opens each
sandbox SQLite database read-only (`mode=ro`), and writes one new analysis
artifact. It makes no provider calls.

Usage:
    py analyze_groq_pairs.py            # writes phase_d_groq_pair_trace_analysis.json
"""
from __future__ import annotations

import glob
import json
import re
import sqlite3
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
OUT = BENCH_DIR / "phase_d_groq_pair_trace_analysis.json"

DIAGNOSTIC_FAMILIES = {
    "classification_metrics": "oof_performance",
    "calibration_and_error_analysis": "calibration_errors",
    "feature_target_suspiciousness": "feature_target_scan",
    "dataset_validation": "data_integrity",
    # NOTE: returns date spans/fold sizes only — structural, not a
    # performance/temporal-drift measurement. Labelled accordingly.
    "time_split_validation": "time_split_structure",
    "artifact_summary": "artifact_summary",
    "propose_hypothesis": "hypothesis_proposal",
}

SMALL_NUMERIC_KEYS = {
    "roc_auc", "brier", "precision_at_threshold", "recall_at_threshold",
    "threshold", "n", "n_rows", "n_features", "r", "abs_r", "accuracy",
    "log_loss", "ece", "mean_predicted", "observed_rate", "max_abs_dev",
    "spearman", "pearson",
}


def _balanced_json(text: str) -> dict | None:
    """First balanced {...} in `text` that parses to a dict."""
    start = text.find("{")
    while start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
                    if isinstance(parsed, dict):
                        return parsed
                    break
        start = text.find("{", start + 1)
    return None


def _block_from_event(detail: str | None, payload: dict) -> dict | None:
    """Structured summary attempt: valid payload -> parse raw_block;
    invalid event -> the raw message is preserved in `detail`."""
    raw = payload.get("raw_block")
    if isinstance(raw, str):
        return _balanced_json(raw)
    if detail:
        return _balanced_json(detail)
    return None


def _normalise_basis(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, str):
        return [v for v in re.split(r"[,\s]+", value) if v]
    return []


def _numeric_evidence(obj, depth: int = 0, out: dict | None = None) -> dict:
    """Small, bounded numeric summary of a tool result (no raw dumps)."""
    out = {} if out is None else out
    if depth > 3:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith("_") or k in ("dedup", "_dedup"):
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool) \
                    and k in SMALL_NUMERIC_KEYS:
                out[k] = v
            elif isinstance(v, dict) and len(out) < 24:
                _numeric_evidence(v, depth + 1, out)
    return out


def _summarise_action(a: sqlite3.Row) -> dict:
    result = None
    try:
        result = json.loads(a["result"]) if a["result"] else None
    except (TypeError, json.JSONDecodeError):
        result = None
    evidence = _numeric_evidence(result) if isinstance(result, dict) else {}
    extra = {}
    if isinstance(result, dict):
        if isinstance(result.get("top_correlations"), list):
            extra["top_correlations"] = [
                {"feature": c.get("feature"), "r": c.get("r")}
                for c in result["top_correlations"][:4]
                if isinstance(c, dict)]
        if isinstance(result.get("per_split_auc"), dict):
            extra["per_split_auc"] = result["per_split_auc"]
        if result.get("caveat"):
            extra["caveat"] = str(result["caveat"])[:200]
    try:
        args = json.loads(a["arguments"]) if a["arguments"] else {}
    except (TypeError, json.JSONDecodeError):
        args = {"_raw": str(a["arguments"])[:200]}
    return {"id": a["id"], "seq": a["seq"], "tool": a["tool_name"],
            "status": a["status"], "arguments": args,
            "numeric_evidence": evidence, "detail": extra,
            "error": (a["error"] or None)}


def analyse_run(conn: sqlite3.Connection, run: dict) -> dict:
    inv = conn.execute(
        "select * from investigations where title=?",
        (run["investigation_name"],)).fetchone()
    if inv is None:
        return {"condition": run["condition"], "missing_investigation": True}
    actions = conn.execute(
        "select * from actions where investigation_id=? order by seq",
        (inv["id"],)).fetchall()
    hyps = conn.execute(
        "select id, text, status from hypotheses where investigation_id=?",
        (inv["id"],)).fetchall()
    summary_events = conn.execute(
        "select seq, detail, payload from events where investigation_id=? "
        "and kind='summary' order by seq", (inv["id"],)).fetchall()

    t1_calls = run["turn1"].get("tool_calls_in_turn") or 0
    turn1_actions = actions[:t1_calls]
    turn2_actions = actions[t1_calls:]
    action_ids = {a["id"] for a in actions}
    hyp_ids = {h["id"] for h in hyps}

    attempts = []
    for ev in summary_events:
        try:
            payload = json.loads(ev["payload"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        parsed = _block_from_event(ev["detail"], payload)
        basis_ids: list[str] = []
        hyp_refs: list[str] = []
        if isinstance(parsed, dict):
            for rec in (parsed.get("status_recommendations") or []):
                if isinstance(rec, dict):
                    if rec.get("hypothesis_id"):
                        hyp_refs.append(str(rec["hypothesis_id"]))
                    basis_ids.extend(_normalise_basis(rec.get("basis")))
        attempts.append({
            "event_seq": ev["seq"],
            "valid": bool(payload.get("valid")),
            "errors": payload.get("errors") or [],
            "conclusion": (parsed or {}).get("conclusion"),
            "status_recommendations": (parsed or {}).get(
                "status_recommendations"),
            "uncertainties": (parsed or {}).get("uncertainties"),
            "recommended_next": (parsed or {}).get("recommended_next"),
            "hypothesis_refs": hyp_refs,
            "hypothesis_refs_known": [h for h in hyp_refs if h in hyp_ids],
            "basis_ids": basis_ids,
            "basis_ids_valid": [b for b in basis_ids if b in action_ids],
            "basis_ids_unknown": [b for b in basis_ids if b not in action_ids],
            "basis_is_list": bool(parsed and all(
                isinstance(rec.get("basis"), list)
                for rec in (parsed.get("status_recommendations") or [])
                if isinstance(rec, dict))),
        })

    final = attempts[-1] if attempts else {}
    families = sorted({DIAGNOSTIC_FAMILIES.get(a["tool_name"], a["tool_name"])
                       for a in actions})
    t2_rounds = run["turn2"].get("rounds") or 0
    t2_calls = run["turn2"].get("tool_calls_in_turn") or 0
    # Synthesis round = last round of turn 2 when the turn ended in `stop`;
    # extra rounds before it = rounds - 1. In this sample every such extra
    # round executed a hypothesis-proposal call, NOT a new diagnostic — the
    # field is named for rounds, not evidence.
    t2_finish = run["turn2"].get("finish_reasons") or []
    t2_ended_with_stop = bool(t2_finish) and t2_finish[-1] == "stop"
    return {
        "condition": run["condition"],
        "investigation_id": inv["id"],
        "tool_calls_used": inv["tool_call_count"],
        "max_tool_calls": inv["max_tool_calls"],
        "turn1": {"rounds": run["turn1"].get("rounds"),
                  "finish_reasons": run["turn1"].get("finish_reasons"),
                  "summary_block_seen": run["turn1"].get("summary_block_seen"),
                  "actions": [_summarise_action(a) for a in turn1_actions]},
        "turn2": {"rounds": t2_rounds,
                  "finish_reasons": t2_finish,
                  "ended_with_stop": t2_ended_with_stop,
                  "extra_rounds_before_synthesis":
                      max(0, t2_rounds - 1) if t2_ended_with_stop else None,
                  "actions_after_turn1": [_summarise_action(a)
                                          for a in turn2_actions],
                  "tool_calls": t2_calls},
        "all_actions": [_summarise_action(a) for a in actions],
        "diagnostic_families": families,
        "diagnostic_family_count": len([f for f in families
                                        if f != "hypothesis_proposal"]),
        "evidence_bearing_tools": sorted({
            a["tool_name"] for a in actions
            if a["tool_name"] in ("classification_metrics",
                                  "feature_target_suspiciousness",
                                  "calibration_and_error_analysis",
                                  "dataset_validation")}),
        "hypotheses": [{"id": h["id"], "status": h["status"],
                        "text": h["text"]} for h in hyps],
        "summary_attempts": attempts,
        "final_summary": final,
        "ledger_summary": run.get("summary"),
        "summary_repair_attempts": run.get("summary_repair_attempts"),
        "summary_valid_after_repair": run.get("summary_valid_after_repair"),
        "summary_repair_errors": run.get("summary_repair_errors") or [],
        "chained_context_chars": run.get("chained_context_chars"),
        "tokens": {r["tag"]: (r.get("prompt_tokens"),
                              r.get("completion_tokens"))
                   for r in (run.get("per_request") or [])},
        "condition_totals": run.get("condition_totals"),
    }


def main() -> None:
    out = {"source_files": [], "pairs": [], "notes": [
        "Read-only extraction; no provider calls.",
        "Sandbox databases are the same ones the pilots wrote.",
        "Basis-ID validity is measured against Action rows in the SAME "
        "investigation; the production validator does not check basis ids.",
    ]}
    for path in sorted(glob.glob(str(BENCH_DIR / "phase_d_groq_20b_pilot*.json"))):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        db = data.get("sandbox_db")
        entry = {"file": Path(path).name,
                 "generated_utc": data.get("generated_utc"),
                 "model": data.get("model"),
                 "sandbox_db": db,
                 "totals": data.get("totals"),
                 "runs": []}
        conn = None
        if db and Path(db).exists():
            conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
        for run in data.get("runs", []):
            if conn is None or not run.get("investigation_name"):
                entry["runs"].append({"condition": run.get("condition"),
                                      "unavailable": "sandbox db missing"})
                continue
            entry["runs"].append(analyse_run(conn, run))
        if conn is not None:
            conn.close()
        out["pairs"].append(entry)
        out["source_files"].append(Path(path).name)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    print(f"wrote {OUT}")

    # concise console matrix
    for pair in out["pairs"]:
        print("\n==", pair["file"], pair["generated_utc"])
        for r in pair["runs"]:
            if r.get("unavailable") or r.get("missing_investigation"):
                print("  ", r.get("condition"), "UNAVAILABLE"); continue
            fs = r["final_summary"]
            print(f"  {r['condition']:5s} t1r={r['turn1']['rounds']} "
                  f"t2r={r['turn2']['rounds']} "
                  f"t2pre={r['turn2']['extra_rounds_before_synthesis']} "
                  f"fam={r['diagnostic_family_count']} "
                  f"calls={r['tool_calls_used']} "
                  f"valid={fs.get('valid')} "
                  f"attempts={len(r['summary_attempts'])} "
                  f"basis={len(fs.get('basis_ids_valid') or [])}/"
                  f"{len(fs.get('basis_ids') or [])} "
                  f"chained={r['chained_context_chars']}")


if __name__ == "__main__":
    main()
