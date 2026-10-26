"""Development-only tests for the Phase 3 outcome taxonomy and research memory."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from autonomous_agent.proposal_layer import research_memory as rm  # noqa: E402
from autonomous_agent.proposal_layer.research_memory import Outcome, Record, ResearchMemory  # noqa: E402


def rec(at, pid="p1", key="K1", direction="up", **kw):
    return Record(at=at, proposal_id=pid, key=key, direction=direction, **kw)


def test_classify_covers_every_category_with_precedence():
    cases = [
        (rec("t", valid_config=False, passed=True), Outcome.INVALID_CONFIG),
        (rec("t", is_proposal_only=True, key_seen_before=True), Outcome.REDUNDANT),
        (rec("t", interrupted=True, passed=False), Outcome.INTERRUPTED),
        (rec("t", measurement_available=False, passed=True), Outcome.UNAVAILABLE),
        (rec("t", inconclusive=True, passed=True), Outcome.INCONCLUSIVE),
        (rec("t", passed=None), Outcome.INCONCLUSIVE),
        (rec("t", passed=True, is_replication=True, key_seen_before=True), Outcome.REPLICATION),
        (rec("t", passed=True, key_seen_before=True), Outcome.VERIFIED_IMPROVEMENT),
        (rec("t", passed=True, key_seen_before=False), Outcome.NOVEL_HYPOTHESIS),
        (rec("t", passed=False, key_seen_before=True), Outcome.REJECTED),
    ]
    for record, expected in cases:
        assert rm.classify(record) is expected, record


def test_interrupted_is_not_a_model_failure():
    mem = ResearchMemory([rec("2026-10-01", interrupted=True, passed=False)])
    assert rm.classify(mem.records[0]) is Outcome.INTERRUPTED
    # An interrupted run must not push the key's estimate down.
    before = ResearchMemory().rank([("K1", "up")], cutoff="2026-10-02")
    after = mem.rank([("K1", "up")], cutoff="2026-10-02")
    assert after == before


def test_redundant_and_unavailable_do_not_move_ranking():
    base = ResearchMemory([rec("2026-10-01", passed=True, key_seen_before=True)])
    noisy = copy.deepcopy(base)
    noisy.extend([
        rec("2026-10-02", pid="p2", is_proposal_only=True, key_seen_before=True, passed=False),
        rec("2026-10-03", pid="p3", measurement_available=False, passed=False),
    ])
    cut = "2026-10-10"
    assert noisy.rank([("K1", "up")], cut) == base.rank([("K1", "up")], cut)


def test_rejected_records_are_retained_and_counted():
    mem = ResearchMemory([rec("2026-10-01", passed=False, key_seen_before=True),
                          rec("2026-10-02", passed=True, key_seen_before=True)])
    counts = mem.counts()
    assert counts["rejected"] == 1 and counts["verified_improvement"] == 1
    assert sum(counts.values()) == len(mem.records)


def test_as_of_is_strictly_before_cutoff():
    mem = ResearchMemory([rec("2026-10-01"), rec("2026-10-05"), rec("2026-10-05")])
    assert [r.at for r in mem.as_of("2026-10-05")] == ["2026-10-01"]


def test_temporal_replay_future_records_do_not_change_earlier_ranking():
    history = [
        rec("2026-10-01", pid="a", key="K1", passed=True, key_seen_before=True),
        rec("2026-10-02", pid="b", key="K2", passed=False, key_seen_before=True),
        rec("2026-10-03", pid="c", key="K1", passed=True, key_seen_before=True),
    ]
    keys = [("K1", "up"), ("K2", "up"), ("K3", "up")]
    cutoff = "2026-10-04"
    mem = ResearchMemory(list(history))
    earlier = mem.rank(keys, cutoff)

    # Add future outcomes of every kind, including flips of observed results.
    future = [
        rec("2026-10-04", pid="d", key="K1", passed=False, key_seen_before=True),
        rec("2026-10-06", pid="e", key="K2", passed=True, key_seen_before=True),
        rec("2026-10-07", pid="f", key="K3", passed=True, key_seen_before=True),
    ]
    mem.extend(future)
    assert mem.rank(keys, cutoff) == earlier


def test_future_outcome_flip_leaves_earlier_scores_identical():
    base = [rec("2026-10-01", passed=True, key_seen_before=True),
            rec("2026-10-02", pid="b", passed=True, key_seen_before=True)]
    flipped_future = [rec("2026-10-03", pid="c", passed=False, key_seen_before=True)]
    a = ResearchMemory(list(base)).rank([("K1", "up")], "2026-10-02")
    b = ResearchMemory(list(base) + flipped_future).rank([("K1", "up")], "2026-10-02")
    assert a == b


def test_cold_start_key_gets_prior_not_extreme_score():
    mem = ResearchMemory([rec("2026-10-01", key="K1", passed=True, key_seen_before=True)])
    ((key, score),) = mem.rank([("NEW", "up")], "2026-10-02")
    assert key == "NEW" and 0.0 < score < 1.0
