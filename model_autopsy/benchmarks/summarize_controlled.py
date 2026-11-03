"""Assemble the controlled-experiment report tables from the joined analysis.

Reads the frozen blind scores, mechanical table, blind sheet, pair ledgers,
and the joined analysis. Writes phase_d_groq_controlled_report_data.json.
No provider calls; no re-scoring.
"""
from __future__ import annotations

import json
from pathlib import Path

BENCH = Path(__file__).resolve().parent
EVIDENCE_TOOLS = {"classification_metrics", "calibration_and_error_analysis",
                  "feature_target_suspiciousness", "dataset_validation"}


def main() -> int:
    a = json.loads((BENCH / "phase_d_groq_controlled_analysis.json")
                   .read_text(encoding="utf-8"))
    b = json.loads((BENCH / "phase_d_groq_controlled_blind_sheet.json")
                   .read_text(encoding="utf-8"))
    mech = json.loads((BENCH / "phase_d_groq_controlled_mechanical.json")
                      .read_text(encoding="utf-8"))
    blind = {r["run"]: r for r in b["runs"]}
    ledger = json.loads((BENCH / "phase_d_groq_controlled_ledger.json")
                        .read_text(encoding="utf-8"))

    pairs = []
    for p in a["paired"]:
        runs = [r for r in a["runs"] if r["pair"] == p["pair"]]
        f = next(r for r in runs if r["condition"] == "full")
        d = next(r for r in runs if r["condition"] == "delta")
        led = next(x for x in ledger["pairs"] if x["pair"] == p["pair"])
        pairs.append({
            "pair": p["pair"],
            "order": p["order"],
            "provider_http_attempts_ledger": led["provider_http_attempts"],
            "chat_http_attempts_actual": f["http_attempts"] + d["http_attempts"],
            "input_tokens": f["input_tokens"] + d["input_tokens"],
            "output_tokens": f["output_tokens"] + d["output_tokens"],
            "estimated_cost_usd": led["estimated_cost_usd"],
            "full": {
                "quality": f["quality_total"],
                "valid": f["summary_valid"],
                "calls": f["tool_calls_used"],
                "actions_ran": f["actions_ran_count"],
                "input_tokens": f["input_tokens"],
                "output_tokens": f["output_tokens"],
                "cost": f["estimated_cost_usd"],
            },
            "delta": {
                "quality": d["quality_total"],
                "valid": d["summary_valid"],
                "calls": d["tool_calls_used"],
                "actions_ran": d["actions_ran_count"],
                "input_tokens": d["input_tokens"],
                "output_tokens": d["output_tokens"],
                "cost": d["estimated_cost_usd"],
            },
        })

    rubric = []
    evidence = []
    for r in a["runs"]:
        bs = blind[r["label"]]
        acts = bs["actions"]
        ev = sorted({x["tool"] for x in acts
                     if x["status"] == "ran" and x["tool"] in EVIDENCE_TOOLS})
        rubric.append({
            "pair": r["pair"], "condition": r["condition"], "label": r["label"],
            **{f"c{i}": r["components"][str(i)] for i in range(1, 7)},
            "total": r["quality_total"],
            "summary_valid": r["summary_valid"],
            "mechanical_valid": (mech[r["label"]]
                                 ["summary_valid_after_repair"]),
        })
        evidence.append({
            "pair": r["pair"], "condition": r["condition"],
            "distinct_evidence_tools": ev,
            "turn2_tools": r["turn2_tools"],
            "turn2_diagnostic_calls": r["turn2_diagnostic_calls"],
            "turn2_diagnostic_ran": r["turn2_diagnostic_ran"],
        })

    out = {
        "campaign": a["campaign"],
        "ledger_status": a["ledger_status"],
        "ledger_stop_reason": a["ledger_stop_reason"],
        "design_check_all_pairs": a["design_check_all_pairs"],
        "pairs": pairs,
        "rubric": rubric,
        "evidence": evidence,
        "aggregate": a["aggregate"],
        "ledger_totals": a["ledger_totals"],
        "notes": {
            "avg_quality_all_runs_full": a["aggregate"]["full"]
            ["quality_total_mean"],
            "avg_quality_all_runs_delta": a["aggregate"]["delta"]
            ["quality_total_mean"],
            "avg_quality_valid_summaries_only_full": round(
                sum(r["quality_total"] for r in a["runs"]
                    if r["condition"] == "full" and r["summary_valid"])
                / max(1, sum(1 for r in a["runs"]
                             if r["condition"] == "full"
                             and r["summary_valid"])), 2),
            "avg_quality_valid_summaries_only_delta": round(
                sum(r["quality_total"] for r in a["runs"]
                    if r["condition"] == "delta" and r["summary_valid"])
                / max(1, sum(1 for r in a["runs"]
                             if r["condition"] == "delta"
                             and r["summary_valid"])), 2),
            "paired_quality_differences_all":
                [p["quality_delta_minus_full"] for p in a["paired"]],
            "paired_quality_differences_both_valid": [
                p["quality_delta_minus_full"] for p in a["paired"]
                if p["summary_valid_full"] and p["summary_valid_delta"]],
            "pair2_full_tool_validation_400_retry": True,
            "ledger_attempts_include_duplicate_400_entry": True,
        },
    }
    path = BENCH / "phase_d_groq_controlled_report_data.json"
    path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"written": str(path), "pairs": len(pairs)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
