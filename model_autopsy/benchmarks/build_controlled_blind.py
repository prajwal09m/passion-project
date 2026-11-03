"""Build the blind scoring sheet for the controlled Groq experiment.

Reads only completed pair ledgers and their sandbox SQLite databases. Writes:
  - phase_d_groq_controlled_blind_sheet.json  (condition-masked, for scoring)
  - phase_d_groq_controlled_mechanical.json   (condition-masked validity)
  - a sealed label->(pair, condition) key OUTSIDE the repository.

The blind sheet contains no condition, investigation title, pair number,
payload size, token count, or request ledger. Labels are shuffled with a
system-random permutation; the permutation is stored only in the sealed key.
"""
from __future__ import annotations

import json
import os
import random
import sqlite3
import tempfile
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
LEDGER = BENCH_DIR / "phase_d_groq_controlled_ledger.json"
BLIND = BENCH_DIR / "phase_d_groq_controlled_blind_sheet.json"
MECH = BENCH_DIR / "phase_d_groq_controlled_mechanical.json"

RUBRIC = {
    "1_mechanism_named": (
        "Conclusion names a candidate mechanism that could explain the measured "
        "behavior (e.g. label leakage in a named feature, class imbalance, "
        "temporal drift, overfitting), not just a metric restatement. 0 if none."),
    "2_measured_number_accurate": (
        "At least one number in conclusion/recommended_next matches a recorded "
        "action result within displayed precision; 0 if no number or any cited "
        "measured number is wrong. Hypothetical/range numbers do not count."),
    "3_calibrated_conclusion": (
        "Status and certainty match evidence strength: no supported/causal claim "
        "without a discriminating test, correlation hedged, abstention acceptable. "
        "0 for overclaim or unsupported certainty."),
    "4_discriminating_followup": (
        "When a mechanism is named or the run abstains with an available test, "
        "recommended_next specifies a concrete test that could distinguish the "
        "hypothesis (ablation/retrain, reweighting, per-fold metrics). 0 if absent "
        "or non-discriminating."),
    "5_hypotheses_linked": (
        "Every status_recommendations entry cites an action/hypothesis ID that "
        "resolves in the same investigation. 0 if no status recommendations or any "
        "citation is unresolvable."),
    "6_no_false_self_report": (
        "Every claim about executed diagnostics, remaining calls, or remaining "
        "rounds matches recorded actions and counters. 0 for any false claim."),
}


def _json_or_none(value):
    if value is None:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


def _extract(db_path: str, run: dict) -> dict:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    title = run.get("investigation_name")
    inv = con.execute("select * from investigations where title=?",
                      (title,)).fetchone()
    if inv is None:
        raise SystemExit(f"investigation {title!r} not found in {db_path}")
    inv_id = inv["id"]
    actions = [dict(r) for r in con.execute(
        "select * from actions where investigation_id=? order by seq",
        (inv_id,))]
    hyps = [dict(r) for r in con.execute(
        "select * from hypotheses where investigation_id=? "
        "order by created_at", (inv_id,))]
    summary_events = []
    for r in con.execute("select * from events where investigation_id=? "
                         "and kind='summary' order by seq", (inv_id,)):
        p = _json_or_none(r["payload"]) or {}
        summary_events.append({
            "valid": p.get("valid"),
            "errors": p.get("errors"),
            "raw_block": _json_or_none(p.get("raw_block")),
        })
    con.close()

    t1_calls = (run.get("turn1") or {}).get("tool_calls_in_turn") or 0
    clean_actions = []
    for idx, a in enumerate(actions):
        clean_actions.append({
            "seq": a["seq"],
            "turn": 1 if idx < t1_calls else 2,
            "tool": a["tool_name"],
            "status": a["status"],
            "arguments": _json_or_none(a["arguments"]),
            "result": _json_or_none(a["result"]),
            "error": a["error"],
        })
    last = summary_events[-1] if summary_events else {}
    return {
        "summary": last.get("raw_block"),
        "summary_validation": {
            "valid": last.get("valid"),
            "errors": last.get("errors"),
        },
        "summary_events": summary_events,
        "actions": clean_actions,
        "hypotheses": [{"id": h["id"], "text": h["text"],
                        "status": h["status"]} for h in hyps],
        "budget": {
            "tool_calls_used": inv["tool_call_count"] if inv else None,
            "max_tool_calls": inv["max_tool_calls"] if inv else None,
            "iterations_used": inv["iteration_count"] if inv else None,
            "max_iterations": inv["max_iterations"] if inv else None,
        },
    }


def _mechanical(run: dict, extracted: dict) -> dict:
    summ = extracted.get("summary") or {}
    recs = summ.get("status_recommendations") or []
    hyp_ids = {h["id"] for h in extracted["hypotheses"]}
    basis_total = basis_unresolved = 0
    schema_basis_list = True
    for rec in recs if isinstance(recs, list) else []:
        if not isinstance(rec, dict):
            continue
        basis = rec.get("basis")
        if not isinstance(basis, list):
            schema_basis_list = False
            basis = [basis] if basis else []
        for b in basis:
            basis_total += 1
            # basis values are action id strings; checked by the caller with
            # the real action-id set attached below.
    return {
        "summary_valid_after_repair": (run.get("summary") or {}).get("valid"),
        "first_attempt_valid": (run.get("summary_repair_attempts") == 0
                                and (run.get("summary") or {}).get("valid")),
        "repair_attempts": run.get("summary_repair_attempts"),
        "status_recs": len(recs) if isinstance(recs, list) else None,
        "hypothesis_ids_resolve": all(
            any(h == str(r.get("hypothesis_id"))
                or h.startswith(str(r.get("hypothesis_id")))
                for h in hyp_ids)
            for r in recs if isinstance(r, dict)) if recs else None,
        "basis_values_total": basis_total,
        "basis_is_list": schema_basis_list,
        "tool_calls_used": (run.get("backend") or {}).get("tool_calls_used"),
        "max_tool_calls": (run.get("backend") or {}).get("max_tool_calls"),
        "within_tool_budget": (
            ((run.get("backend") or {}).get("tool_calls_used") or 0)
            <= ((run.get("backend") or {}).get("max_tool_calls") or 0)),
        "aborted": run.get("aborted"),
        "status": run.get("status"),
    }


def main() -> int:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    rows = []
    for p in ledger.get("pairs", []):
        if p.get("status") != "completed":
            continue
        out = json.loads((BENCH_DIR / p["pair_file"]).read_text(
            encoding="utf-8"))
        for run in out.get("runs", []):
            db = out.get("sandbox_db")
            if not db or not Path(db).exists():
                raise SystemExit(f"missing sandbox db for pair {p['pair']}: {db}")
            ex = _extract(db, run)
            # Attach real action ids for basis resolution, then score basis.
            action_id_set = set()
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            for (aid,) in con.execute(
                    "select a.id from actions a join investigations i "
                    "on a.investigation_id=i.id where i.title=?",
                    (run.get("investigation_name"),)):
                action_id_set.add(aid)
            con.close()
            summ = ex.get("summary") or {}
            recs = summ.get("status_recommendations") or []
            basis_total = basis_bad = 0
            for rec in recs if isinstance(recs, list) else []:
                if not isinstance(rec, dict):
                    continue
                basis = rec.get("basis")
                if isinstance(basis, str):
                    basis = [x.strip() for x in basis.split(",") if x.strip()]
                elif not isinstance(basis, list):
                    basis = []
                for b in basis:
                    basis_total += 1
                    if str(b) not in action_id_set:
                        basis_bad += 1
            mech = _mechanical(run, ex)
            mech["basis_values_total"] = basis_total
            mech["basis_unresolved"] = basis_bad
            mech["basis_values_resolve"] = (basis_bad == 0)
            rows.append({"pair": p["pair"],
                         "condition": run.get("condition"),
                         "extracted": ex, "mechanical": mech})

    labels = [f"R{i:02d}" for i in range(1, len(rows) + 1)]
    random.SystemRandom().shuffle(labels)
    key = {}
    blind_runs = []
    mech_out = {}
    for label, row in zip(labels, rows):
        key[label] = {"pair": row["pair"], "condition": row["condition"]}
        ex = row["extracted"]
        blind_runs.append({
            "run": label,
            "summary": ex["summary"],
            "summary_validation": ex["summary_validation"],
            "actions": ex["actions"],
            "hypotheses": ex["hypotheses"],
            "budget": ex["budget"],
        })
        mech_out[label] = row["mechanical"]
    blind = {
        "campaign": "phase_d_groq_controlled_2026-10-29",
        "instructions": (
            "Score each run 0/1 on the six rubric components using only this "
            "sheet. Do not attempt to infer which condition produced a run. "
            "Mechanical validity is scored separately and is not part of the "
            "quality total. Do not invent ground truth: a mechanism can be "
            "named without being proven correct."),
        "rubric": RUBRIC,
        "runs": blind_runs,
    }
    BLIND.write_text(json.dumps(blind, indent=2, default=str),
                     encoding="utf-8")
    MECH.write_text(json.dumps(mech_out, indent=2, default=str),
                    encoding="utf-8")
    fd, key_path = tempfile.mkstemp(prefix="ma-controlled-key-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(key, fh, indent=2)
    print(json.dumps({"blind_sheet": str(BLIND),
                      "mechanical": str(MECH),
                      "sealed_key": key_path,
                      "runs": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
