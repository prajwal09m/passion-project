"""M15 Phase 2/3/4 tests (offline, deterministic)."""


def test_diagnose_execution_failure():
    from model_autopsy.backend.research import resolve as R
    d = R.diagnose(
        [{"text": "h", "status": "proposed", "evidence_refs": []}],
        [{"tool": "artifact_summary", "status": "failed", "n": 0}])
    assert d["class"] == "experiment-execution-failure"
    nxt = R.next_experiment(d, {}, [])
    assert nxt["action"] == "fix-and-rerun"


def test_diagnose_contradictory_evidence():
    from model_autopsy.backend.research import resolve as R
    hyps = [{"text": "slice gap", "status": "investigating",
             "names_mechanism": True,
             "evidence_refs": [{"relation": "supports"},
                               {"relation": "contradicts"}]}]
    d = R.diagnose(hyps, [{"tool": "x", "status": "ran"}])
    assert d["class"] == "contradictory-evidence"
    assert R.next_experiment(d, {}, [])["action"] == "discriminate"


def test_diagnose_thin_data_blocks():
    from model_autopsy.backend.research import resolve as R
    d = R.diagnose(
        [{"text": "h", "status": "proposed", "evidence_refs": []}],
        [{"tool": "x", "status": "ran", "n": 40}])
    assert d["class"] == "insufficient-observations"
    assert R.next_experiment(d, {}, [])["action"] == "blocked"


def test_diagnose_reproduction_failure():
    from model_autopsy.backend.research import resolve as R
    hyps = [{"text": "h", "status": "investigating",
             "evidence_refs": [{"relation": "supports"}]}]
    d = R.diagnose(hyps, [{"tool": "x", "status": "ran"}],
                   verifications=[{"grade": "not-reproduced"}])
    assert d["class"] == "reproduction-failure"


def test_contract_never_confirms_unresolved():
    from model_autopsy.backend.research import resolve as R
    c = R.contract("q", [], [], [], [], [], [], "open question",
                   {}, {}, "none", "blocked: thin data")
    assert c["status"] == "unresolved"
    assert "never relabeled" in c["note"]


def test_pipeline_diversity_flags_redundancy():
    from model_autopsy.backend.research import pipeline as P
    hyps = [{"text": "error concentrates in the south segment",
             "family": "subgroup"},
            {"text": "error concentrates in south segment values",
             "family": "subgroup"}]
    d = P.diversify(hyps)
    assert d["redundant"] >= 1 and d["needs_counter"] is True
    ch = P.characterize("slice P@K gap 0.17",
                        ["group error ratio 6.0 (concentrated)"])
    assert ch["character"]["concentrated"] is True
    out = P.conclude(
        [{"family": "subgroup", "falsification": "flat probe"}],
        [{"relation": "supports", "candidate": "subgroup"}])
    assert out["lead"]["family"] == "subgroup"
    assert P.conclude([], [])["lead"] is None


def test_intervention_records_assumptions():
    from model_autopsy.backend.research import intervene as I
    import pytest
    with pytest.raises(ValueError):
        I.plan("teleport", "h", "x", [], "v")
    p = I.plan("ablation", "input tracking", "remove feat",
               ["data", "metric"], "isolated copy")
    r = I.record(p, "effect vanished", True)
    assert r["supports"] is True
    assert "synthetic" in r["causal_note"]
    assert "stratified" in I.confounding_check(
        [{"m": 1}], "nope")["required"]


def test_replay_music_rank_detects_slice_gap():
    """Offline replay of the live eval_music failure (no paid calls).

    Live H1 named the true mechanism but pooled AUC contradicted it
    and the loop ended inconclusive. The new slice-aware diagnostic
    must surface the gap offline so the miss is diagnosable.
    """
    from model_autopsy.backend import ml_tools as T
    out = T.ranking_slice_diagnostics(
        "model_autopsy/tests/fixture_eval/investigator/music_rank.csv")
    assert out["max_slice_gap"] is not None
    assert out["max_slice_gap"] >= 0.15
    assert out["pooled_precision_at_k"] > 0.9  # healthy pooled mean
    worst = min(out["per_slice"].items(),
                key=lambda kv: kv[1].get("precision_at_k") or 9)
    assert worst[0] == "new"
