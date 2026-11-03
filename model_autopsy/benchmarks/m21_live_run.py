"""M21 authorized live run — exactly one eval_music investigation.

Authorization: rounds=3, experiments=6, attempts=12, cost cap $0.65,
NO token cap. The token-cap removal is a runtime caps value only
(cost cap remains the enforced financial guard); no source file is
modified. Preflight runs first; any refusal aborts before requests.
"""

import sys
from pathlib import Path


def main() -> int:
    from model_autopsy.backend import config as C

    C.bootstrap_env()
    if not C.meta_api_key():
        print("REFUSED: provider key not configured")
        return 2

    from model_autopsy.backend.live import governor as G

    # Authorized deviation from defaults: no token cap. Rounds,
    # experiments, attempts, and the $0.65 cost cap are unchanged and
    # enforced by the governor's pre-request checks.
    G.CAPS["tokens"] = 10 ** 9

    from model_autopsy.backend.live import driver as D

    out = Path("model_autopsy/benchmarks/live_runs")
    pf = D.preflight("eval_music", out)
    print("PREFLIGHT:")
    for key, value in pf["checks"].items():
        if key == "separation_audit":
            print(f"  separation_audit: ok={value.get('ok')} "
                  f"files={value.get('files_scanned')}")
        elif key == "cost_projection":
            print(f"  cost_projection: worst=${value.get('worst_case_usd')} "
                  f"typical=${value.get('typical_cached_usd')} "
                  f"within_cap={value.get('within_cap')}")
        elif "key" in key.lower():
            print(f"  {key}: {'SET' if value else 'MISSING'}")
        else:
            print(f"  {key}: {value}")
    print(f"  effective_caps: rounds=3 experiments=6 attempts=12 "
          f"tokens=UNLIMITED(per authorization) cost_usd=0.65")
    if not pf["go"]:
        print(f"REFUSED: {pf['reason']}")
        return 2
    try:
        rec = D.run_live_investigation(
            "eval_music", out, max_rounds=3, run_id="m21-music-01",
            skeptic_enabled=True)
    except RuntimeError as exc:
        print(f"Run failed (preserved where possible): {exc}")
        return 1
    print(f"STATUS: {rec['status']}  run={rec['run_id']}")
    print(f"BUDGET: {rec['budget']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
