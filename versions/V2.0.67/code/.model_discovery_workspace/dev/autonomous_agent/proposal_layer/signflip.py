"""H-10 / D2 production sign-flip port -- method (b), procedure-level validity.

Owner decision: method (b) week-level sign-flip Monte-Carlo p-values at
M = 1000 with Holm step-down (familywise alpha = 0.05), method name
``week_level_signflip_holm``, adopted 2026-10-14 in
``stat_validation_h10/H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md``.

Ported from the independently developed reference implementation
``stat_validation_h10/simh10.py`` under the binding requirements of
``stat_validation_h10/H10_SIGNFLIP_PORT_SPEC_2026_10_13.md`` (C-1, C-2, C-5):

* Reference linear form -- ``TrialStats.sign_flip_deltas`` (simh10.py:286):
  ``flips = (S @ g) / (2 * pair_total)``.
* Reference p-value -- ``run_methods`` (simh10.py:450-452):
  ``S = rng.integers(0, 2, size=(M, W)) * 2 - 1``;
  ``p = (1 + #{flips <= delta_hat}) / (M + 1)`` (lower tail, ``+1``
  correction, ties counted via ``<=``).

COI / ownership statement (spec section 10): this port is **not**
independent confirmation. The D2 conflict-of-interest disclosure applies to
this code (the same agent implemented parts of the system under review);
the independent methodological anchor is the separately developed reference
implementation, and the two are pinned together by frozen equivalence
fixtures (``autonomous_agent/signflip_port_fixtures_2026_10_14.json``)
under ``autonomous_agent/test_signflip_port.py``.

Validity statement (C-5 / Result 2'-B): every p-value produced by this
module is valid at the **procedure level** -- marginal over the recorded,
data-independent random flip draw -- and NEVER conditional on the realized
flip set. Result 2 (fixed-set conditional exactness) is retracted and no
artifact produced here may assert it.

Assumption (disclosed, unestablished): week-level arm-label
exchangeability on the real data. See ``EXCHANGEABILITY_DISCLOSURE``; the
full residual-risk statement lives in the D2 review and the owner decision
record.

Provenance contract (C-1 / C-2): flip rows are drawn i.i.d. uniform on the
full week-level group by a fixed-seed, data-independent procedure recorded
before outcome evaluation; they are never curated, filtered, reweighted,
or redrawn after any inspection of outcomes. The frozen campaign config
carries the recorded draw event (``multiplicity_policy.flip_draw``); use
``load_campaign_flip_draw`` to obtain it and fail closed with
``FlipProvenanceMissing`` when it is absent, malformed, stage-mismatched,
or when the regenerated rows do not hash-match the recorded draw.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

__all__ = [
    "APPROVED_METHOD_NAME",
    "EXCHANGEABILITY_DISCLOSURE",
    "VALIDITY_SCOPE",
    "FLIP_DRAW_STAGE",
    "FlipDraw",
    "FlipProvenanceMissing",
    "draw_flips",
    "linear_deltas",
    "signflip_p_value",
    "load_campaign_flip_draw",
    "disclosure_fields",
]

# The method name recorded in the owner decision of 2026-10-14; the
# multiplicity allowlist (multiplicity.APPROVED_P_VALUE_METHODS) contains
# exactly this string.
APPROVED_METHOD_NAME = "week_level_signflip_holm"

# Disclosures every emitted artifact must carry (spec sections 5, 10).
EXCHANGEABILITY_DISCLOSURE = (
    "assumption: week-level arm-label exchangeability (unestablished)")
VALIDITY_SCOPE = "procedure_level_marginal_over_flip_draw"

# The only admissible draw stage: recorded before any outcome evaluation.
FLIP_DRAW_STAGE = "before_outcome_evaluation"

_ROWS_HASH_NAME = "flip_rows_v1_int8_c_order"


class FlipProvenanceMissing(Exception):
    """Refuse to compute a p-value without admissible recorded draw provenance."""


@dataclass(frozen=True)
class FlipDraw:
    """Recorded, data-independent flip-draw provenance (spec section 5)."""

    seed: int
    rng_name: str
    bitgen: str
    numpy_version: str
    M: int
    W: int
    rows_sha256: str
    stage: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": int(self.seed), "rng_name": self.rng_name,
            "bitgen": self.bitgen, "numpy_version": self.numpy_version,
            "M": int(self.M), "W": int(self.W),
            "rows_sha256": self.rows_sha256, "stage": self.stage,
        }


def _rows_sha256(S: "np.ndarray") -> str:
    rows = np.ascontiguousarray(S, dtype=np.int8)
    return hashlib.sha256(rows.tobytes()).hexdigest()


def draw_flips(W: int, M: int, seed: int) -> tuple["np.ndarray", FlipDraw]:
    """One data-independent i.i.d. uniform draw of {+1,-1}^{(M, W)} (C-1).

    Pure: it touches no outcomes, no data, and no ambient state. Called
    once per frozen recorded draw; the same (W, M, seed) always reproduces
    byte-identical rows, so reuse is deterministic and any *different*
    regeneration is detectable via the recorded ``rows_sha256``.
    """
    W, M, seed = int(W), int(M), int(seed)
    if W <= 0 or M <= 0:
        raise ValueError("W and M must be positive")
    rng = np.random.default_rng(seed)
    S = rng.integers(0, 2, size=(M, W)) * 2 - 1
    S = np.ascontiguousarray(S, dtype=np.int8)
    draw = FlipDraw(
        seed=seed,
        rng_name="numpy.random.default_rng",
        bitgen=type(rng.bit_generator).__name__,
        numpy_version=np.__version__,
        M=M, W=W,
        rows_sha256=_rows_sha256(S),
        stage=FLIP_DRAW_STAGE,
    )
    return S, draw


def linear_deltas(g: "np.ndarray", S: "np.ndarray",
                  n_pos: int, n_neg: int) -> "np.ndarray":
    """Flipped AUC deltas for every row of S: (S @ g) / (2 * n_pos * n_neg).

    Exact linear form of the reference implementation (simh10.py:286-288).
    """
    g = np.asarray(g, dtype=np.float64)
    S = np.asarray(S, dtype=np.float64)
    pair_total = int(n_pos) * int(n_neg)
    if pair_total <= 0:
        raise ValueError("need at least one positive and one negative label")
    if S.ndim != 2 or S.shape[1] != g.shape[0]:
        raise ValueError(f"S shape {S.shape} incompatible with g length {g.shape[0]}")
    return (S @ g) / (2.0 * pair_total)


def signflip_p_value(delta_hat: float, g: "np.ndarray",
                     draw: FlipDraw, S: "np.ndarray",
                     *, n_pos: int, n_neg: int) -> float:
    """Lower-tail sign-flip p-value (reference formula, simh10.py:452).

    p = (1 + #{flips <= delta_hat}) / (M + 1): the ``+1`` correction and
    ``<=`` tie rule are exactly the reference's; the p-value's resolution
    is 1/(M + 1). Fails closed with ``FlipProvenanceMissing`` unless the
    draw's stage is the recorded-before-outcomes stage and the supplied S
    regenerates byte-identical to the draw's recorded rows hash.

    API adjustment vs spec section 5 (spec: "proposed, minimal, may be
    adjusted if recorded"): ``n_pos``/``n_neg`` are explicit keyword-only
    arguments. The reference divides by ``2 * pair_total`` inside the
    flip computation (simh10.py:287), so the port cannot know the scale
    that ``delta_hat`` lives in without them; guessing or ignoring the
    scale would silently change the p-value. Recorded in
    ``H10_SIGNFLIP_PORT_IMPLEMENTATION_REPORT_2026_10_14.md``.
    """
    if not isinstance(draw, FlipDraw):
        raise FlipProvenanceMissing("draw provenance is not a FlipDraw record")
    if draw.stage != FLIP_DRAW_STAGE:
        raise FlipProvenanceMissing(
            f"draw stage {draw.stage!r} != required {FLIP_DRAW_STAGE!r}: "
            "a draw not recorded before outcome evaluation is inadmissible")
    S_arr = np.asarray(S, dtype=np.int8)
    if S_arr.ndim != 2 or S_arr.shape != (int(draw.M), int(draw.W)):
        raise FlipProvenanceMissing(
            f"flip rows shape {S_arr.shape} does not match recorded "
            f"M={draw.M}, W={draw.W}")
    if _rows_sha256(S_arr) != draw.rows_sha256:
        raise FlipProvenanceMissing(
            "flip rows do not hash-match the recorded draw: re-draws and "
            "post-inspection regeneration are refused (C-1/C-2)")
    g_arr = np.asarray(g, dtype=np.float64)
    if g_arr.shape[0] != int(draw.W):
        raise FlipProvenanceMissing(
            f"g length {g_arr.shape[0]} does not match recorded W={draw.W}")
    flips = linear_deltas(g_arr, S_arr, n_pos, n_neg)
    delta_hat = float(delta_hat)
    count_le = int(np.count_nonzero(flips <= delta_hat))
    return (1 + count_le) / (int(draw.M) + 1)


def disclosure_fields() -> dict[str, str]:
    """Disclosure block every emitted artifact must merge in (spec 5/10)."""
    return {
        "validity_scope": VALIDITY_SCOPE,
        "exchangeability_assumption": EXCHANGEABILITY_DISCLOSURE,
        "p_value_method": APPROVED_METHOD_NAME,
    }


def load_campaign_flip_draw(config: Mapping[str, Any],
                            *, W: int,
                            ) -> tuple[int, "np.ndarray", FlipDraw]:
    """Obtain the frozen campaign's recorded flip draw; fail closed (C-2).

    Reads ``config["multiplicity_policy"]["flip_draw"]`` -- the block
    written once at configuration freeze (drawn before any campaign outcome
    existed) -- and returns (seed, S, draw) with the regenerated rows
    verified against the recorded ``rows_sha256``. Any missing, malformed,
    stage-mismatched, or hash-inconsistent record raises
    ``FlipProvenanceMissing``: the port never falls back to ad-hoc seeding.
    """
    mult = config.get("multiplicity_policy") if isinstance(config, Mapping) else None
    block = mult.get("flip_draw") if isinstance(mult, Mapping) else None
    if not isinstance(block, Mapping):
        raise FlipProvenanceMissing(
            "campaign config has no multiplicity_policy.flip_draw record: "
            "the flip draw is part of the procedure and must be frozen "
            "before outcome evaluation (C-2)")
    if block.get("stage") != FLIP_DRAW_STAGE:
        raise FlipProvenanceMissing(
            f"recorded flip_draw stage {block.get('stage')!r} != required "
            f"{FLIP_DRAW_STAGE!r}")
    try:
        seed = int(block["seed"])
        M = int(block["M"])
        recorded_hash = str(block["rows_sha256"])
    except (KeyError, TypeError, ValueError) as error:
        raise FlipProvenanceMissing(
            f"malformed flip_draw record: {error}") from error
    if int(block.get("W", -1)) != int(W) or M <= 0:
        raise FlipProvenanceMissing(
            f"recorded flip_draw W/M (W={block.get('W')}, M={M}) does not "
            f"match the current frame (W={W})")
    S, draw = draw_flips(int(W), M, seed)
    if draw.rows_sha256 != recorded_hash or draw.stage != block.get("stage"):
        raise FlipProvenanceMissing(
            "regenerated flip rows do not hash-match the frozen record: "
            "refusing to evaluate (possible re-draw or seed tampering)")
    return seed, S, draw
