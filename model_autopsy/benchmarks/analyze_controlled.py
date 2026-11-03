"""Join the blind quality scores with the sealed condition key and summarize.

Run only AFTER the blind scores are frozen. This script does not re-score; it
joins, aggregates, and writes phase_d_groq_controlled_analysis.json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
PRICING = {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000}
COMPONENTS = ["1", "2", "3", "4", "5", "6"]


def _score(entry: dict) -> tuple[int, dict]:
    comp = entry.get("components", entry)
    vals = {k: int(comp.get(k, 0)) for k in COMPONENTS}
    return sum(vals.values()), vals


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True,
                    help="sealed label->pair/condition key path")
    ap.add_argument("--scores", default=str(
        BENCH_DIR / "phase_d_groq_controlled_scores_blind.json"))
    ap.add_argument("--mechanical", default=str(
        BENCH_DIR / "phase_d_groq_controlled_mechanical.json"))
    ap.add_argument("--out", default=str(
        BENCH_DIR / "phase_d_groq_controlled_analysis.json"))
    args = ap.parse_args()

    ledger = json.loads((BENCH_DIR / "phase_d_groq_controlled_ledger.json")
                        .read_text(encoding="utf-8"))
    scores = json.loads(Path(args.scores).read_text(encoding="utf-8"))
    mech = json.loads(Path(args.mechanical).read_text(encoding="utf-8"))
    key = json.loads(Path(args.key).read_text(encoding="utf-8"))
    blind = json.loads((BENCH_DIR /
                        "phase_d_groq_controlled_blind_sheet.json")
                       .read_text(encoding="utf-8"))
    blind_by_label = {b["run"]: b for b in blind["runs"]}

    runs = []
    for p in ledger["pairs"]:
        if p.get("status") != "completed":
            continue
        out = json.loads((BENCH_DIR / p["pair_file"]).read_text(
            encoding="utf-8"))
        for r in out["runs"]:
            label = next(k for k, v in key.items()
                         if v["pair"] == p["pair"]
                         and v["condition"] == r.get("condition"))
            total, comps = _score(scores[label])
            per_req = r.get("per_request") or []
            # The harness double-records a tool-validation 400 (one logical
            # retry, two ledger entries). Unique (tag, try) is the actual HTTP
            # attempt count; ledger_entries keeps the inflated figure visible.
            http_attempts = len({(x.get("tag"), x.get("try")) for x in per_req})
            in_tok = sum(int(x.get("prompt_tokens") or 0) for x in per_req)
            out_tok = sum(int(x.get("completion_tokens") or 0) for x in per_req)
            cost = round(in_tok * PRICING["input"]
                         + out_tok * PRICING["output"], 6)
            turn1 = r.get("turn1") or {}
            turn2 = r.get("turn2") or {}
            backend = r.get("backend") or {}
            actions = backend.get("actions_ran") or []
            bs = blind_by_label[label]
            t2_actions = [a for a in bs["actions"] if a.get("turn") == 2]
            t2_tools = [a["tool"] for a in t2_actions]
            t2_diag = [a for a in t2_actions
                       if a["tool"] != "propose_hypothesis"]
            t2_diag_ran = [a for a in t2_diag if a.get("status") == "ran"]
            runs.append({
                "pair": p["pair"],
                "condition": r.get("condition"),
                "label": label,
                "order": p.get("order"),
                "quality_total": total,
                "components": comps,
                "mechanical": mech.get(label),
                "requests": len(per_req),
                "http_attempts": http_attempts,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "estimated_cost_usd": cost,
                "tool_calls_used": backend.get("tool_calls_used"),
                "max_tool_calls": backend.get("max_tool_calls"),
                "actions_ran": actions,
                "actions_ran_count": backend.get("actions_ran_count"),
                "reused_results": backend.get("reused_results"),
                "turn1_rounds": turn1.get("rounds"),
                "turn2_rounds": turn2.get("rounds"),
                "turn1_calls": turn1.get("tool_calls_in_turn"),
                "turn2_calls": turn2.get("tool_calls_in_turn"),
                "turn2_tools": t2_tools,
                "turn2_diagnostic_calls": len(t2_diag),
                "turn2_diagnostic_ran": len(t2_diag_ran),
                "summary": bs.get("summary"),
                "summary_valid": (r.get("summary") or {}).get("valid"),
                "summary_repair_attempts": r.get("summary_repair_attempts"),
                "summary_valid_after_repair":
                    r.get("summary_valid_after_repair"),
                "aborted": r.get("aborted"),
                "conclusion": (r.get("summary") or {}).get("conclusion"),
                "final_message_head": r.get("final_message_head"),
            })

    def agg(cond: str) -> dict:
        rs = [x for x in runs if x["condition"] == cond]
        return {
            "runs": len(rs),
            "quality_total_mean": round(
                sum(x["quality_total"] for x in rs) / len(rs), 2) if rs else None,
            "quality_total_sum": sum(x["quality_total"] for x in rs),
            "requests": sum(x["requests"] for x in rs),
            "http_attempts": sum(x["http_attempts"] for x in rs),
            "input_tokens": sum(x["input_tokens"] for x in rs),
            "output_tokens": sum(x["output_tokens"] for x in rs),
            "estimated_cost_usd": round(
                sum(x["estimated_cost_usd"] for x in rs), 6),
            "tool_calls_used": sum((x["tool_calls_used"] or 0) for x in rs),
            "summary_valid": sum(1 for x in rs if x["summary_valid"]),
            "summary_valid_after_repair":
                sum(1 for x in rs if x["summary_valid_after_repair"]),
            "turn2_gathered_evidence": sum(
                1 for x in rs if x["turn2_diagnostic_ran"] > 0),
            "turn2_diagnostic_calls_total": sum(
                x["turn2_diagnostic_calls"] for x in rs),
            "turn2_diagnostic_ran_total": sum(
                x["turn2_diagnostic_ran"] for x in rs),
        }

    paired = []
    for p in sorted({x["pair"] for x in runs}):
        f = next(x for x in runs if x["pair"] == p and x["condition"] == "full")
        d = next(x for x in runs if x["pair"] == p and x["condition"] == "delta")
        paired.append({
            "pair": p,
            "order": f["order"],
            "quality_full": f["quality_total"],
            "quality_delta": d["quality_total"],
            "quality_delta_minus_full": d["quality_total"] - f["quality_total"],
            "input_tokens_full": f["input_tokens"],
            "input_tokens_delta": d["input_tokens"],
            "input_delta_pct": (round(100 * (d["input_tokens"]
                                             - f["input_tokens"])
                                      / f["input_tokens"], 1)
                                if f["input_tokens"] else None),
            "cost_full": f["estimated_cost_usd"],
            "cost_delta": d["estimated_cost_usd"],
            "calls_full": f["tool_calls_used"],
            "calls_delta": d["tool_calls_used"],
            "summary_valid_full": f["summary_valid"],
            "summary_valid_delta": d["summary_valid"],
        })

    analysis = {
        "campaign": ledger.get("campaign"),
        "model": ledger.get("model"),
        "design_check_all_pairs": all(
            p.get("design_check", {}).get("ok") for p in ledger["pairs"]),
        "ledger_status": ledger.get("status"),
        "ledger_stop_reason": ledger.get("stop_reason"),
        "ledger_totals": ledger.get("totals"),
        "aggregate": {"full": agg("full"), "delta": agg("delta")},
        "paired": paired,
        "runs": runs,
        "scoring_note": (
            "Quality total is the sum of six blind 0/1 rubric components; "
            "mechanical validity is reported separately and is not included. "
            "n=5 pairs, one model, one artifact: descriptive only."),
    }
    Path(args.out).write_text(json.dumps(analysis, indent=2, default=str),
                              encoding="utf-8")
    print(json.dumps({"written": args.out,
                      "pairs": len(paired),
                      "design_ok": analysis["design_check_all_pairs"],
                      "aggregate": analysis["aggregate"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
