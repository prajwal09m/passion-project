"""Live pilot CLI (Milestone 5, §12).

  py -3 -m model_autopsy.backend.live.cli --project eval_turbine [--max-rounds 3]

Runs preflight FIRST; any failure aborts before any request. Exactly
one investigation per invocation; no repeat flags, no multi-project
mode, no comparison mode (further live work needs authorization).
"""
from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="M5 live Meta pilot")
    ap.add_argument("--project", default="eval_turbine")
    ap.add_argument("--max-rounds", type=int, default=3)
    ap.add_argument("--out", default="model_autopsy/benchmarks/live_runs")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--no-skeptic", action="store_true",
                    help="comparison Arm B: disable skeptic-lite")
    args = ap.parse_args(argv)

    from . import driver as D
    from .. import config as _config
    # Explicit initialization: reuse the campaigns' secure .env mechanism
    # (model_autopsy/.env, setdefault semantics, never echoes values)
    # BEFORE preflight reads key availability. No requests are sent here.
    _config.bootstrap_env()
    out = Path(args.out)
    pf = D.preflight(args.project, out)
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
    if not pf["go"]:
        print(f"REFUSED: {pf['reason']}")
        return 2
    try:
        rec = D.run_live_investigation(
            args.project, out, max_rounds=args.max_rounds,
            run_id=args.run_id,
            skeptic_enabled=not args.no_skeptic)
    except RuntimeError as exc:
        print(f"Run failed (preserved where possible): {exc}")
        return 1
    print(f"STATUS: {rec['status']}  run={rec['run_id']}")
    print(f"BUDGET: {rec['budget']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
