"""Eval v3 Stage 7B: v2-vs-v3 regression on archived music runs.

Offline, read-only: archived scorecards/eval_reports are never rewritten.
v2 outputs must reproduce archived scorecards exactly; v3 outputs are
computed fresh and asserted against the forensic expectations.
"""
import json

from model_autopsy.backend.eval import scorer as V2
from model_autopsy.backend.eval import scorer_v3 as V3

RUNS = ["m16b-music-01", "m17-music-01", "m19-music-01", "m22-live-01"]


def _load(run):
    base = f"model_autopsy/benchmarks/live_runs/{run}/"
    try:
        rep = json.load(open(base + "eval_report.json"))
        arch = json.load(open(base + "scorecard.json"))
    except FileNotFoundError:
        return None, None
    return rep, arch


def _truth():
    return json.load(open("model_autopsy/tests/fixture_eval/"
                          "ground_truth_eval.json"))


def test_v2_reproduces_every_archived_music_scorecard():
    for run in RUNS:
        rep, arch = _load(run)
        if rep is None:
            continue
        out = V2.score("eval_music", rep, _truth())
        assert out["verdict"] == arch["verdict"], run
        assert out["dimensions"]["discovery"] == \
            arch["dimensions"]["discovery"], run
        assert out["overall"] == arch["overall"], run


def test_v3_m22_honest_partial_not_total_failure():
    rep, _ = _load("m22-live-01")
    out = V3.score_v3("eval_music", rep, _truth())
    assert out["rubric_version"] == "v3"
    assert out["dimensions"]["discovery"] == 0.7
    assert out["dimensions"]["evidence"] == 1.0
    assert out["dimensions"]["verification"] == 0.0
    assert out["dimensions"]["confirmation"] == 0.7
    assert out["verdict"] == "honest_partial"
    assert out["overall"] is not None and out["overall"] > 0.5


def test_v3_m19_confirmed_significant_gap_scores_full():
    # M19 confirmed the cold-start title with a significant 0.1695 gap:
    # under the recalibrated v3 band (0.15 + significance) that
    # confirmation is justified -> discovery 1.0, confirmation 1.0.
    rep, _ = _load("m19-music-01")
    if rep is None:
        return
    out = V3.score_v3("eval_music", rep, _truth())
    assert out["dimensions"]["discovery"] == 1.0, out["notes"]
    assert out["dimensions"]["confirmation"] == 1.0, out["notes"]


def test_v3_reports_carry_version_and_unavailable_honestly():
    for run in RUNS:
        rep, _ = _load(run)
        if rep is None:
            continue
        out = V3.score_v3("eval_music", rep, _truth())
        assert out["rubric_version"] == "v3"
        assert "formula" in out
        for k, v in out["dimensions"].items():
            assert v is None or isinstance(v, float), (run, k)
