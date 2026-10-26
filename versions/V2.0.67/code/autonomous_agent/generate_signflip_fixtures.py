#!/usr/bin/env python3
"""Generate the frozen sign-flip port equivalence fixtures (A-12, 2026-10-14).

Anchors the production port (autonomous_agent/proposal_layer/signflip.py) to
the independently developed reference implementation stat_validation_h10/
simh10.py:

* reference linear deltas -- TrialStats.sign_flip_deltas (simh10.py:286-288):
  flips = (S @ g) / (2 * pair_total), called here on the REAL reference
  method (via a stub carrying g and pair_total);
* reference p-value -- run_methods (simh10.py:450-452):
  S = rng.integers(0, 2, size=(M, W)) * 2 - 1;
  p = (1 + #{flips <= delta_hat}) / (M + 1).

Every stored expected value is computed by the reference formula on the
reference S construction. The generation run also cross-checks the
production port against every stored value and refuses to write on any
mismatch. Deterministic given the recorded seeds and numpy version.

Output: autonomous_agent/signflip_port_fixtures_2026_10_14.json
(the test suite pins the file hash; regenerate only with a recorded reason).
"""
import hashlib
import json
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "stat_validation_h10"))

import numpy as np  # noqa: E402

import simh10  # noqa: E402  (the independent reference implementation)
from autonomous_agent.proposal_layer import signflip  # noqa: E402

OUT = ROOT / "autonomous_agent" / "signflip_port_fixtures_2026_10_14.json"


def reference_deltas(g: np.ndarray, S: np.ndarray, n_pos: int, n_neg: int) -> np.ndarray:
    """The REAL reference implementation, called unbound with a stub."""
    stub = types.SimpleNamespace(g=np.asarray(g, dtype=np.float64),
                                 pair_total=int(n_pos) * int(n_neg))
    return np.asarray(simh10.TrialStats.sign_flip_deltas(stub, S),
                      dtype=np.float64)


def reference_rows(W: int, M: int, seed: int) -> np.ndarray:
    """The reference draw construction, verbatim (simh10.py:450)."""
    return np.random.default_rng(seed).integers(0, 2, size=(M, W)) * 2 - 1


def reference_p(flips: np.ndarray, delta_hat: float, M: int) -> float:
    """The reference p-value formula, verbatim (simh10.py:452)."""
    return (int((flips <= delta_hat).sum()) + 1) / (M + 1)


def build_case(name: str, g_list, n_pos: int, n_neg: int, M: int, seed: int,
               delta_hat: float | None, delta_hat_rule: str) -> dict:
    g = np.asarray(g_list, dtype=np.float64)
    W = g.shape[0]
    S = reference_rows(W, M, seed)
    flips = reference_deltas(g, S, n_pos, n_neg)
    if delta_hat is None:
        # Exact boundary tie: delta_hat equals a REALIZED flip delta (the
        # smallest one), so the <= rule counts at least the rows achieving
        # it; with repeated/zero g entries several rows tie at the minimum.
        delta_hat = float(flips.min())
        tie_count = int((flips == delta_hat).sum())
        assert tie_count >= 1, name
    else:
        tie_count = int((flips == float(delta_hat)).sum())
    expected_p = reference_p(flips, float(delta_hat), M)

    # Production-port cross-check at generation time; refuse to write on drift.
    S_prod, draw = signflip.draw_flips(W, M, seed)
    assert np.array_equal(S_prod, S.astype(np.int8)), name
    port_p = signflip.signflip_p_value(float(delta_hat), g, draw, S_prod,
                                       n_pos=n_pos, n_neg=n_neg)
    port_deltas = signflip.linear_deltas(g, S_prod, n_pos, n_neg)
    assert np.array_equal(port_deltas, flips), f"{name}: delta drift"
    assert port_p == expected_p, f"{name}: p drift {port_p} != {expected_p}"

    return {
        "name": name,
        "W": W, "M": M, "seed": seed, "n_pos": n_pos, "n_neg": n_neg,
        "g": [float(x) for x in g],
        "delta_hat": float(delta_hat),
        "delta_hat_rule": delta_hat_rule,
        "ties_at_delta_hat": tie_count,
        "expected_p": float(expected_p),
        "reference_deltas": [float(x) for x in flips],
        "reference_rows_head": [[int(v) for v in row] for row in S[:3]],
        "rows_sha256_int8_c_order": hashlib.sha256(
            np.ascontiguousarray(S, dtype=np.int8).tobytes()).hexdigest(),
        "bitgen": type(np.random.default_rng(seed).bit_generator).__name__,
        "numpy_version": np.__version__,
    }


def main() -> None:
    g20 = np.random.default_rng(20261001).standard_normal(20) / 100.0
    cases = [
        # (1) boundary-exactness case: delta_hat is exactly a realized flip
        # delta (the minimum), with zero weeks creating further natural ties.
        build_case("boundary_exactness_realized_min",
                   [-0.04, 0.01, 0.02, -0.005, 0.03, 0.0, 0.0, 0.015],
                   n_pos=3, n_neg=5, M=500, seed=20261013,
                   delta_hat=None, delta_hat_rule="realized_min_delta"),
        # (2) pinned 20-week synthetic frames, both recorded seeds, M=1000.
        build_case("pinned_week_20_seed_20261013", [float(x) for x in g20],
                   n_pos=10, n_neg=10, M=1000, seed=20261013,
                   delta_hat=0.4 * float(g20.sum()) / 200.0,
                   delta_hat_rule="predeclared_scale"),
        build_case("pinned_week_20_seed_20261014", [float(x) for x in g20],
                   n_pos=10, n_neg=10, M=1000, seed=20261014,
                   delta_hat=-1.3 * float(g20.sum()) / 200.0,
                   delta_hat_rule="predeclared_scale"),
        # (3) tie-heavy: repeated and zero g entries, delta_hat exactly the
        # realized minimum delta -> multi-way ties resolved by the <= rule.
        build_case("tie_heavy",
                   [0.01, 0.01, 0.0, 0.0, -0.02, -0.02],
                   n_pos=4, n_neg=6, M=400, seed=20261013,
                   delta_hat=None, delta_hat_rule="realized_min_delta"),
    ]
    payload = {
        "_FIXTURE_STATUS": (
            "FROZEN EQUIVALENCE FIXTURES (A-12), generated 2026-10-14 by "
            "generate_signflip_fixtures.py from the independent reference "
            "implementation stat_validation_h10/simh10.py (linear deltas "
            "lines 286-288; p-value lines 450-452) and cross-checked against "
            "the production port at generation time. Never regenerate to "
            "make a test pass: drift is a defect to investigate."),
        "reference": "stat_validation_h10/simh10.py (sign_flip_deltas; run_methods p_b)",
        "formula": "flips = (S @ g) / (2 * n_pos * n_neg); "
                   "p = (1 + #{flips <= delta_hat}) / (M + 1)",
        "draw_construction": "S = np.random.default_rng(seed).integers(0, 2, size=(M, W)) * 2 - 1",
        "cases": cases,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    # write BYTES so the printed hash is the file's hash on every platform
    # (text-mode newline translation would silently change it on Windows).
    data = text.encode("utf-8")
    OUT.write_bytes(data)
    print("fixtures:", OUT.relative_to(ROOT))
    print("sha256:", hashlib.sha256(data).hexdigest())
    for case in cases:
        print(f"  {case['name']}: M={case['M']} p={case['expected_p']:.6f}")


if __name__ == "__main__":
    main()
