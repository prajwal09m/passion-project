"""Eval v3 Stage 4: canonical `gap` normalization tests (offline, pure)."""
from model_autopsy.backend.eval import normalize as N


def test_gap_only_kept_without_flags():
    out, flags = N.normalize_numbers("t", {"gap": 0.17})
    assert out["gap"] == 0.17 and flags == {}


def test_alias_only_becomes_canonical_gap():
    out, flags = N.normalize_numbers("ranking_slice_diagnostics",
                                     {"max_slice_gap": 0.1695})
    assert out["gap"] == 0.1695
    assert out["max_slice_gap"] == 0.1695  # original preserved
    assert flags == {"alias_from": "max_slice_gap"}


def test_both_equal_no_conflict():
    out, flags = N.normalize_numbers("t", {"gap": 0.1,
                                           "max_slice_gap": 0.1})
    assert out["gap"] == 0.1 and flags == {}


def test_both_conflicting_explicit_gap_wins_with_flag():
    out, flags = N.normalize_numbers("t", {"gap": 0.1695,
                                           "max_slice_gap": 0.2})
    assert out["gap"] == 0.1695
    assert flags.get("gap_conflict") is True
    assert out["max_slice_gap"] == 0.2  # original preserved


def test_neither_present_stays_absent_never_zero():
    out, flags = N.normalize_numbers("t", {"n": 10})
    assert "gap" not in out and flags == {}
    assert N.canonical_gap({"n": 10}) is None


def test_invalid_values_dropped_with_flag():
    for bad in ("x", float("nan"), True, -0.5):
        out, flags = N.normalize_numbers("t", {"gap": bad,
                                               "max_slice_gap": bad})
        assert "gap" not in out, bad
        assert flags.get("gap_invalid") is True, bad


def test_none_means_absent_not_invalid():
    out, flags = N.normalize_numbers("t", {"gap": None,
                                             "max_slice_gap": None})
    assert "gap" not in out and flags == {}


def test_input_never_mutated():
    src = {"max_slice_gap": 0.1695}
    N.normalize_numbers("t", src)
    assert src == {"max_slice_gap": 0.1695}


def test_canonical_gap_single_read_path():
    assert N.canonical_gap({"max_slice_gap": 0.1695}) == 0.1695
    assert N.canonical_gap({"gap": 0.2, "max_slice_gap": 0.1}) == 0.2
