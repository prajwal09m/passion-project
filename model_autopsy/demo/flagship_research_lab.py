"""Flagship demonstration (Milestone 3, Part 12) — offline, no paid calls.

Project: 'Premium estimator' (insurance, regression). The investigator
receives ONLY the project brief + artifact path — no hint that a
train/infer scaling mismatch on `bmi` is planted. The same
lab.run_autonomous_investigation engine used for every scenario drives
understand -> recon -> plan -> hypotheses -> diagnostics -> experiments
-> review -> forensic report. Output: printed report + JSON artifact.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from model_autopsy.backend.db import SessionLocal, init_db  # noqa: E402
from model_autopsy.backend import engine  # noqa: E402
from model_autopsy.backend.projects import ProjectSpec  # noqa: E402
from model_autopsy.backend.research import lab  # noqa: E402

SPEC = {
    "project_id": "flagship_premium",
    "name": "Premium estimator",
    "description": ("Predict monthly premiums for new policies from "
                    "applicant age and BMI."),
    "domain": "insurance",
    "objective": ("Premiums look systematically off after a pipeline "
                  "change; find out what is wrong and show the evidence."),
    "task_type": "regression",
    "target_definition": "Numeric monthly premium",
    "evaluation_methodology": "MAE/RMSE, residual-vs-feature analysis",
    "model": {"name": "prem-reg", "framework": "sklearn",
              "availability": "local"},
    "dataset": {"location":
                "model_autopsy/tests/fixture_challenge/pipeline_insurance.csv",
                "n_rows": 1200},
}

OUT = Path(__file__).resolve().parent / "flagship_report.json"


def main() -> int:
    init_db()
    session = SessionLocal()
    try:
        spec = ProjectSpec.from_dict(dict(SPEC))
        inv = engine.create_investigation(
            session, "ml", "Flagship: premium estimator",
            SPEC["objective"], {"max_iterations": 3})
        report = lab.run_autonomous_investigation(
            session, inv, spec,
            artifact_path=SPEC["dataset"]["location"],
            max_experiments=4)
        OUT.write_text(json.dumps(report, indent=2))
        print("=" * 64)
        print("FLAGSHIP DEMO — Premium estimator (insurance, regression)")
        print("=" * 64)
        print("EXECUTIVE:", report["executive_summary"])
        print("\nUNDERSTANDING:",
              report["project_understanding"]["predicting"][:120])
        print("\nCONFIRMED:")
        for f in report["confirmed_findings"]:
            print(f"  + {f['title']} :: {f['mechanism'][:100]}")
        print("REJECTED:")
        for f in report["rejected_hypotheses"]:
            print(f"  - {f['title']}")
        print("\nEXPERIMENTS:")
        for e in report["experiments"]:
            print(f"  [{e['tool']}] {e['summary']}")
        print("\nVERIFICATION:")
        for v in report["verification"]:
            print(f"  {v['hypothesis_id'][:8]} -> {v['verdict']}")
        print("\nLIMITATIONS:")
        for lim in report["limitations"]:
            print(f"  ! {lim}")
        print(f"\nFull JSON: {OUT}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
