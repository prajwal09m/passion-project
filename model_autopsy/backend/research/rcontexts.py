"""Token-efficient research contexts (Milestone 3, Part 10).

Extends Full/Delta packaging: understanding + hypothesis-state +
experiment-result summaries with evidence references only; full outputs
stay in durable records. Deduplicates repeated evidence; retrieval is
relevance-ranked. Offline measurement counts characters (proxy) and
records provider-billed tokens when a live trace supplies usage.
"""
from __future__ import annotations

import json


def summarize(report_or_state: dict) -> dict:
    hyps = report_or_state.get("hypotheses") or []
    exps = report_or_state.get("experiments") or []
    return {
        "understanding": str(report_or_state.get(
            "understanding", ""))[:800],
        "hypothesis_states": [
            {"id": h.get("id", "")[:8],
             "status": h.get("status"),
             "title": str(h.get("title", ""))[:120]}
            for h in hyps],
        "experiment_results": [
            {"id": e.get("experiment_id", "")[:8],
             "tool": e.get("tool"),
             "summary": str(e.get("summary", ""))[:160]}
            for e in exps],
        "evidence_refs_only": True,
        "note": "full outputs remain in durable records by id; "
                "summaries carry references, not blobs",
    }


def dedup(entries: list[dict]) -> list[dict]:
    seen, out = set(), []
    for e in entries:
        key = (e.get("tool"), str(e.get("summary", ""))[:80])
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


def measure(full_chars: int, summary_chars: int,
            billed: dict | None = None) -> dict:
    red = round(100 * (full_chars - summary_chars) / full_chars, 1) \
        if full_chars else 0.0
    return {"full_chars": full_chars, "summary_chars": summary_chars,
            "reduction_pct": red,
            "provider_billed_tokens": billed,
            "optimization_target": "minimize tokens while holding "
                                   "investigation quality and coverage",
            "honesty": "char proxy only; billed savings need live usage; "
                       "no universal %% claim from one project"}
