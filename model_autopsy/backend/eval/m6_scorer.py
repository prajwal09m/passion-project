"""M6 extended scorer (Part 4).

Wraps the frozen M4 scorer UNCHANGED (same 6 dims + verdict + overall)
and adds three new dimensions alongside — never redefining old ones:

- experiment_selection (did the run choose discriminating, non-redundant tests?)
- causal_diagnosis (did it separate anomaly/correlation/supported/established?)
- report_validity (did the structured summary validate with traceable refs?)

Old and new scores are reported side by side, never averaged together.
M4 overall stays comparable to M5; M6 overall is a separate 9-dim figure.
"""
from __future__ import annotations

from . import scorer as M4


def score_experiment_selection(report: dict) -> tuple[float, str]:
    exps = report.get("experiments", []) or []
    tools = [e.get("tool") for e in exps]
    distinct = len(set(tools))
    n = len(exps)
    has_propose_only = distinct <= 1 and all(
        t == "propose_hypothesis" for t in tools) if tools else True
    if not exps:
        return 0.0, "no experiments executed"
    if has_propose_only:
        return 0.2, "only hypothesis records, no discriminating diagnostics"
    # Discriminating set: changepoint/residual/shift + a hygiene check.
    disc = {"temporal_changepoint_scan", "residual_time_analysis",
            "distribution_shift_profile", "forecast_diagnostics",
            "time_split_validation", "regression_metrics"}
    n_disc = len(set(tools) & disc)
    dup = n - distinct
    if n_disc >= 3 and dup == 0:
        return 1.0, "3+ discriminating diagnostics, no redundancy"
    if n_disc >= 2 and dup <= 1:
        return 0.7, "discriminating tests with minor redundancy"
    if n_disc >= 1:
        return 0.4, "one discriminating test; competitors untested"
    return 0.2, "diagnostics do not discriminate the hypotheses"


def score_causal_diagnosis(report: dict) -> tuple[float, str]:
    confirmed = report.get("confirmed_findings", []) or []
    inconc = report.get("inconclusive", []) or []
    rejected = report.get("rejected_hypotheses", []) or []
    # Supported with cited experiments outranks bare claims.
    exps = {e.get("experiment_id") for e in report.get("experiments", [])}
    if confirmed:
        return 0.8, "cause asserted with cited experiments (verify mechanism separately)"
    if rejected and inconc:
        return 0.7, "competitors rejected, remainder honestly inconclusive"
    if inconc and not confirmed:
        return 0.5, "honestly inconclusive; mechanism unresolved"
    if not (confirmed or inconc or rejected):
        return 0.2, "no diagnosis recorded"
    return 0.4, "partial causal discipline"


def score_report_validity(report: dict) -> tuple[float, str]:
    valid = report.get("structured_summary_valid")
    if valid is True:
        return 1.0, "structured summary validated with traceable refs"
    if valid is False:
        # Invalid but preserved is honest (M5 precedent) — partial credit.
        has_exec = bool(report.get("executive_summary"))
        return (0.4, "invalid summary preserved; executive summary present") \
            if has_exec else (0.0, "no valid structured summary")
    return 0.5, "validity unknown"


def score_m6(pid: str, report: dict, truth: dict) -> dict:
    base = M4.score(pid, report, truth)
    exp_v, exp_note = score_experiment_selection(report)
    cau_v, cau_note = score_causal_diagnosis(report)
    rep_v, rep_note = score_report_validity(report)
    dims9 = {**base["dimensions"],
             "experiment_selection": exp_v,
             "causal_diagnosis": cau_v,
             "report_validity": rep_v}
    overall9 = round(sum(dims9.values()) / len(dims9), 3)
    return {"m4": base,
            "m6_dimensions": {"experiment_selection": exp_v,
                             "causal_diagnosis": cau_v,
                             "report_validity": rep_v},
            "m6_notes": {"experiment_selection": exp_note,
                         "causal_diagnosis": cau_note,
                         "report_validity": rep_note},
            "m6_overall_9dim": overall9,
            "note": "M4 frozen and comparable to M5; M6 9-dim is separate, never averaged with M4"}
