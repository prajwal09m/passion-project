"""Eval v3 Stage 2/3: scorer v3 dimension tests + v2 preservation pins.

All scorer tests are pure-dict, deterministic, offline.
"""
import json

from model_autopsy.backend.eval import scorer as V2
from model_autopsy.backend.eval import scorer_v3 as V3

TRUTH = {"eval_music": {
    "failure": True,
    "mechanism": "cold-start collapse: new-item slice P@K far below "
                 "established items under a healthy pooled mean"}}

COLD = ("Ranker underperforms on new-item slice due to cold-start feature "
        "sparsity, yielding lower top-K relevance for new catalog content.")
WRONG = "Forecasts miss because the target underwent a level shift at day 5."


def _rep(hyps=(), exps=(), confirmed=(), verification=None,
         inconclusive=(), limitations=()):
    return {"confirmed_findings": [{"hypothesis_id": "h", "title": t}
                                   for t in confirmed],
            "rejected_hypotheses": [],
            "inconclusive": [{"hypothesis_id": "i", "text": t}
                             for t in inconclusive],
            "hypotheses": [{"id": f"h{i}", "text": t, "status": s,
                            "evidence_refs": list(r)}
                           for i, (t, s, r) in enumerate(hyps)],
            "experiments": [{"experiment_id": f"e{i}", "tool": tool,
                             "numbers": dict(nums)}
                            for i, (tool, nums) in enumerate(exps)],
            "verification": [] if verification is None else verification,
            "limitations": list(limitations),
            "executive_summary": "s"}


def _moving(aid, rel="supports"):
    return [{"action_id": aid, "tool": "ranking_slice_diagnostics",
             "relation": rel}]


def test_v3_supported_correct_hypothesis_earns_discovery():
    rep = _rep(hyps=[(COLD, "supported", _moving("e0"))],
               exps=[("ranking_slice_diagnostics",
                      {"max_slice_gap": 0.1695}),
                     ("slice_gap_significance",
                      {"gap": 0.1695, "p_value": 0.0005})],
               inconclusive=["open question"],
               limitations=["unresolved: verification pending"])
    out = V3.score_v3("eval_music", rep, TRUTH)
    assert out["rubric_version"] == "v3"
    assert out["dimensions"]["discovery"] == 0.7, out["notes"]
    assert out["dimensions"]["confirmation"] == 0.7, out["notes"]
    assert out["dimensions"]["verification"] == 0.0


def test_v3_confirmed_correct_hypothesis_scores_full_discovery():
    rep = _rep(confirmed=[COLD],
               exps=[("slice_gap_significance",
                      {"gap": 0.1695, "p_value": 0.0005})])
    out = V3.score_v3("eval_music", rep, TRUTH)
    assert out["dimensions"]["discovery"] == 1.0  # confirmed + v3 gate ok
    assert out["dimensions"]["confirmation"] == 1.0, out["notes"]


def test_v3_wrong_hypothesis_scores_zero_discovery():
    rep = _rep(hyps=[(WRONG, "supported", _moving("e0"))],
               exps=[("forecast_diagnostics", {"drift": [1.0, 2.0]})])
    out = V3.score_v3("eval_music", rep, TRUTH)
    assert out["dimensions"]["discovery"] == 0.0, out["notes"]


def test_v3_duplicates_not_double_counted():
    rep = _rep(hyps=[(COLD, "supported", _moving("e0")),
                     (COLD + " ", "investigating", [])])
    out = V3.score_v3("eval_music", rep, TRUTH)
    assert out["dimensions"]["discovery"] == 0.7


def test_v3_rejected_only_match_scores_zero():
    rep = _rep(hyps=[(COLD, "rejected", _moving("e0", "contradicts"))])
    out = V3.score_v3("eval_music", rep, TRUTH)
    assert out["dimensions"]["discovery"] == 0.0


def test_v3_evidence_requires_discrimination_and_linkage():
    linked = _rep(hyps=[(COLD, "supported",
                         _moving("e0") + _moving("e1", "contradicts"))],
                  exps=[("ranking_slice_diagnostics", {"gap": 0.17}),
                        ("regression_metrics", {"bias": 1.0})])
    assert V3.score_v3("eval_music", linked, TRUTH)["dimensions"][
        "evidence"] == 1.0
    unlinked = _rep(hyps=[(COLD, "supported", [])],
                    exps=[("ranking_slice_diagnostics", {"gap": 0.17})])
    assert V3.score_v3("eval_music", unlinked, TRUTH)["dimensions"][
        "evidence"] == 0.0


def test_v3_verification_states():
    base = dict(executive_summary="s", experiments=[],
                confirmed_findings=[], rejected_hypotheses=[],
                inconclusive=[], hypotheses=[], limitations=[])
    assert V3.score_v3("eval_music", dict(base, verification=[]),
                       TRUTH)["dimensions"]["verification"] == 0.0
    planned = V3.score_v3(
        "eval_music", dict(base, verification=[{"hypothesis_id": "h",
                                               "tool": "t",
                                               "planned": True}]), TRUTH)
    assert planned["dimensions"]["verification"] == 0.2
    executed = V3.score_v3(
        "eval_music", dict(base, verification=[{"hypothesis_id": "h",
                                               "tool": "t",
                                               "action_id": "a",
                                               "result": "corroborated"}]),
        TRUTH)
    assert executed["dimensions"]["verification"] == 1.0


def test_v3_unsupported_confirmation_penalized():
    rep = _rep(confirmed=[COLD],  # numbers gate fails: gap too small
               exps=[("slice_gap_significance",
                      {"gap": 0.01, "p_value": 0.4})])
    out = V3.score_v3("eval_music", rep, TRUTH)
    assert out["dimensions"]["confirmation"] == 0.0, out["notes"]


def test_v3_missing_truth_is_unavailable_not_zero():
    out = V3.score_v3("eval_nope", _rep(), TRUTH)
    assert out["overall"] is None and out["verdict"] == "unscored"


def test_v3_null_project_correct_null():
    out = V3.score_v3("eval_wellness", _rep(),
                      {"eval_wellness": {"failure": False}})
    assert out["dimensions"]["discovery"] == 1.0


def test_v2_preserved_on_archived_m22():
    rep = json.load(open("model_autopsy/benchmarks/live_runs/m22-live-01/"
                         "eval_report.json"))
    truth = json.load(open("model_autopsy/tests/fixture_eval/"
                           "ground_truth_eval.json"))
    arch = json.load(open("model_autopsy/benchmarks/live_runs/m22-live-01/"
                          "scorecard.json"))
    out = V2.score("eval_music", rep, truth)
    assert out["verdict"] == arch["verdict"] == "inconclusive"
    assert out["dimensions"]["discovery"] == \
        arch["dimensions"]["discovery"] == 0.0
    assert out["overall"] == arch["overall"] == 0.6


def test_v2_weights_and_bands_untouched():
    assert V2.WEIGHTS == {"discovery": 0.30, "evidence": 0.25,
                          "reasoning": 0.15, "calibration": 0.15,
                          "efficiency": 0.05, "reproducibility": 0.10}
    assert V2.MECHANISMS["eval_music"]["need"] == {"tool":
                                                   "ranking_diagnostics",
                                                   "min_gap": 0.20}
