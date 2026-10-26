"""Read-only baseline audit of the autonomous engine's historical ledger.

Reads autonomous_agent/state/proposal_ledger.jsonl and writes nothing
under the repository. Output is a JSON summary printed to stdout.
"""
from __future__ import annotations

import collections
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
LEDGER = ROOT / "autonomous_agent/state/proposal_ledger.jsonl"


def main() -> None:
    rows = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
    proposals = {}
    final_status: dict[str, str] = {}
    adjudication: dict[str, dict] = {}
    for row in rows:
        if row["row_type"] == "proposal":
            proposals[row["proposal_id"]] = row["proposal"]
        else:
            final_status[row["proposal_id"]] = row["to"]
            if row["to"] == "ADJUDICATED":
                adjudication[row["proposal_id"]] = row.get("detail") or {}

    summary: dict = {"proposals": len(proposals)}
    summary["final_status"] = dict(collections.Counter(final_status.values()))

    # Candidate mix by direction and class (proposal-level).
    summary["by_direction"] = dict(collections.Counter(p.get("direction") for p in proposals.values()))
    summary["by_class"] = dict(collections.Counter(p.get("proposal_class") for p in proposals.values()))

    # Duplicate structure: how many distinct design signatures / primitives.
    sigs = collections.Counter(p.get("design_signature") for p in proposals.values())
    summary["distinct_design_signatures"] = len(sigs)
    summary["max_repeats_of_one_signature"] = max(sigs.values()) if sigs else 0
    prims = collections.Counter(
        primitive.get("primitive_id")
        for p in proposals.values()
        for primitive in (p.get("design", {}).get("primitives") or [])
    )
    summary["primitive_usage"] = dict(prims.most_common())

    # Adjudicated outcomes: AUC delta and the predeclared-criteria verdict.
    deltas, passes, pass_deltas = [], [], []
    per_direction: dict[str, dict] = collections.defaultdict(lambda: {"adjudicated": 0, "passed": 0, "deltas": []})
    for pid, detail in adjudication.items():
        direction = (proposals.get(pid) or {}).get("direction", "?")
        delta = detail.get("primary_delta")
        passed = bool(detail.get("decision_criteria_passed"))
        per_direction[direction]["adjudicated"] += 1
        if delta is not None:
            deltas.append(float(delta))
            per_direction[direction]["deltas"].append(float(delta))
        if passed:
            per_direction[direction]["passed"] += 1
            passes.append(pid)
            if delta is not None:
                pass_deltas.append(float(delta))
    summary["adjudicated"] = len(adjudication)
    summary["criteria_passed"] = len(passes)
    summary["primary_delta_median"] = round(statistics.median(deltas), 6) if deltas else None
    summary["primary_delta_max"] = round(max(deltas), 6) if deltas else None
    summary["primary_delta_min"] = round(min(deltas), 6) if deltas else None
    summary["passed_delta_values"] = sorted(round(d, 6) for d in pass_deltas)
    summary["per_direction"] = {
        k: {"adjudicated": v["adjudicated"], "passed": v["passed"],
            "median_delta": round(statistics.median(v["deltas"]), 6) if v["deltas"] else None}
        for k, v in per_direction.items()
    }

    # Rejection reasons recorded by the gate.
    summary["refusal_reasons"] = dict(collections.Counter(
        r.get("reason_code") for r in rows
        if r["row_type"] == "transition" and r["to"] == "REFUSED"))

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
