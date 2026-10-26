"""Read-only: summarize the distinct measured outcomes behind the ledger's decisions."""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from evidence_redundancy_audit import CANDIDATES, STATE, measured_outcome  # noqa: E402


def main() -> None:
    rows = [json.loads(line) for line in (STATE / "proposal_ledger.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()]
    proposals = {r["proposal_id"]: r["proposal"] for r in rows if r["row_type"] == "proposal"}
    adjudicated = [r for r in rows if r["row_type"] == "transition" and r["to"] == "ADJUDICATED"]
    groups: dict[tuple, list] = collections.defaultdict(list)
    empty = 0
    for row in adjudicated:
        exp_id = row["detail"].get("experiment_id")
        result = json.loads((CANDIDATES / str(exp_id) / "result.json").read_text(encoding="utf-8"))
        key = measured_outcome(result)
        if not key:
            empty += 1
        prop = proposals.get(row["proposal_id"], {})
        prim = (prop.get("design", {}).get("primitives") or [{}])[0].get("primitive_id")
        groups[key].append({
            "pid": row["proposal_id"],
            "prim": prim,
            "class": prop.get("proposal_class"),
            "delta": row["detail"].get("primary_delta"),
            "passed": bool(row["detail"].get("decision_criteria_passed")),
            "parent": row["detail"].get("parent_version"),
        })
    print(json.dumps({"empty_outcome_keys": empty, "groups": len(groups)}, indent=2))
    for key, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        prims = collections.Counter(i["prim"] for i in items)
        print(f"n={len(items):2d} passed={sum(i['passed'] for i in items):2d} "
              f"delta={items[0]['delta']} auc_seed42={key[0][1:] if key else None} "
              f"prims={dict(prims)}")


if __name__ == "__main__":
    main()
