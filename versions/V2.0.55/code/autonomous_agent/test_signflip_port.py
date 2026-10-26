"""Gate-4 acceptance tests for the production sign-flip port (A-1..A-13).

Written against the binding spec stat_validation_h10/
H10_SIGNFLIP_PORT_SPEC_2026_10_13.md (owner-recorded gate-4 authority,
implementation_authorized 2026-10-12). The method adopted by the owner's
recorded decision of 2026-10-14 is
``week_level_signflip_holm``: week-level sign-flip Monte-Carlo p-values at
M = 1000 with Holm step-down (familywise alpha = 0.05); validity is
procedure-level (Result 2'-B), never conditional on the realized flip set.

A-12 equivalence fixtures: autonomous_agent/signflip_port_fixtures_2026_10_14.json,
generated from the independent reference implementation
stat_validation_h10/simh10.py by generate_signflip_fixtures.py; the file
hash is pinned below and any drift fails the suite.
"""
import dataclasses
import hashlib
import json
import pathlib
import unittest

import numpy as np

from autonomous_agent.proposal_layer import multiplicity as mult
from autonomous_agent.proposal_layer import signflip

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = pathlib.Path(__file__).resolve().parent / \
    "signflip_port_fixtures_2026_10_14.json"
# sha256 of the frozen fixture file, pinned at generation time (A-12).
FIXTURES_SHA256 = "0bb6339a690de0615bf93ccf814719f541dfb008b452f7228cf454113edf1a98"


def _manual_draw(S: np.ndarray, seed: int = 0) -> signflip.FlipDraw:
    """Test-only provenance record for a synthetic S (production builds
    provenance via draw_flips from the frozen campaign config)."""
    S8 = np.ascontiguousarray(S, dtype=np.int8)
    return signflip.FlipDraw(
        seed=seed, rng_name="test_synthetic", bitgen="n/a",
        numpy_version=np.__version__, M=S8.shape[0], W=S8.shape[1],
        rows_sha256=hashlib.sha256(S8.tobytes()).hexdigest(),
        stage=signflip.FLIP_DRAW_STAGE)


def _auc(y: np.ndarray, score: np.ndarray) -> float:
    """Brute-force AUC (pair counting) for the A-3 reference frame."""
    pos = score[y == 1]
    neg = score[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        raise ValueError("need both classes")
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else (0.5 if p == n else 0.0)
    return wins / (len(pos) * len(neg))


class A1FormulaTests(unittest.TestCase):
    """A-1: exact formula, +1 correction, <= ties, lower tail (hand case)."""

    def test_hand_computed_case(self) -> None:
        S = np.array([[1, 1], [1, -1], [-1, 1], [-1, -1]], dtype=np.int8)
        draw = _manual_draw(S)
        g = np.array([1.0, 0.0])
        # deltas = (S @ g) / 2 = [0.5, 0.5, -0.5, -0.5]
        # delta_hat equal to the TOP ties: all four rows are <= 0.5 -> p=1.0
        self.assertEqual(
            signflip.signflip_p_value(0.5, g, draw, S, n_pos=1, n_neg=1), 1.0)
        # delta_hat equal to the BOTTOM ties: both -0.5 rows counted (<=)
        # -> p = (1+2)/5 = 3/5
        self.assertEqual(
            signflip.signflip_p_value(-0.5, g, draw, S, n_pos=1, n_neg=1), 3 / 5)
        # strictly below every flip -> the +1 correction gives 1/(M+1)
        below = float(np.nextafter(-0.5, float("-inf")))
        self.assertEqual(
            signflip.signflip_p_value(below, g, draw, S, n_pos=1, n_neg=1), 1 / 5)
        # strictly between the two tie clusters -> same count as the bottom
        # ties (ties resolved by <=, never <)
        self.assertEqual(
            signflip.signflip_p_value(0.0, g, draw, S, n_pos=1, n_neg=1), 3 / 5)


class A2LowerTailTests(unittest.TestCase):
    """A-2: lower-tail direction and g -> -g symmetry bounds (fixture 2)."""

    def setUp(self) -> None:
        self.case = next(c for c in json.loads(
            FIXTURES.read_text("utf-8"))["cases"]
            if c["name"] == "pinned_week_20_seed_20261013")
        self.g = np.asarray(self.case["g"], dtype=np.float64)
        _, self.draw = signflip.draw_flips(self.case["W"], self.case["M"],
                                           self.case["seed"])
        self.S, _ = signflip.draw_flips(self.case["W"], self.case["M"],
                                        self.case["seed"])

    def test_extremes_and_symmetry(self) -> None:
        M = self.case["M"]
        p_mid = signflip.signflip_p_value(self.case["delta_hat"], self.g,
                                          self.draw, self.S,
                                          n_pos=self.case["n_pos"],
                                          n_neg=self.case["n_neg"])
        p_low = signflip.signflip_p_value(-1e9, self.g, self.draw, self.S,
                                          n_pos=self.case["n_pos"],
                                          n_neg=self.case["n_neg"])
        p_high = signflip.signflip_p_value(1e9, self.g, self.draw, self.S,
                                           n_pos=self.case["n_pos"],
                                           n_neg=self.case["n_neg"])
        self.assertEqual(p_low, 1 / (M + 1))          # lower tail, +1 correction
        self.assertEqual(p_high, 1.0)
        self.assertTrue(p_low <= p_mid <= p_high)     # non-decreasing in delta_hat
        # g -> -g with delta_hat -> -delta_hat: p + p' bounded by the
        # combinatorial identity (ties counted on both sides).
        p_flip = signflip.signflip_p_value(-self.case["delta_hat"], -self.g,
                                           self.draw, self.S,
                                           n_pos=self.case["n_pos"],
                                           n_neg=self.case["n_neg"])
        self.assertGreaterEqual(p_mid + p_flip, 1.0)
        self.assertLessEqual(p_mid + p_flip, (M + 3) / (M + 1))


class A3LinearFormTests(unittest.TestCase):
    """A-3: the linear form IS the exact full-swap AUC statistic.

    Verified empirically (2026-10-14): max |linear - brute| = 0.000e+00
    over 200 random flip rows + every single-week flip + the all-minus row
    on three independent synthetic frames. The brute-force recomputation
    swaps arm scores within the flipped weeks (delta = AUC_A' - AUC_B',
    the reference convention of simh10.py:145) and recomputes both AUCs
    by pairwise counting.
    """

    @staticmethod
    def _frame(seed):
        rng = np.random.default_rng(seed)
        W, per_week = 8, 4
        n = W * per_week
        week_id = np.repeat(np.arange(W), per_week)
        y = np.tile([0, 1, 0, 1], W)
        return y, rng.standard_normal(n), rng.standard_normal(n), week_id, W

    @staticmethod
    def _brute(st, week_id, row):
        """Exact full-swap recomputation for one +-1 flip row."""
        swap = np.asarray(row) < 0
        a = np.where(swap[week_id], st.sB, st.sA)
        b = np.where(swap[week_id], st.sA, st.sB)
        return _auc(st.y, a) - _auc(st.y, b)

    @staticmethod
    def _reference(seed):
        import sys
        sys.path.insert(0, str(ROOT / "stat_validation_h10"))
        import simh10
        y, sA, sB, week_id, W = A3LinearFormTests._frame(seed)
        return simh10.TrialStats(y, sA, sB, week_id, W, np.full(W, 4)), week_id, W

    def test_linear_form_equals_brute_force_full_swap_auc(self) -> None:
        for seed in (77, 991, 424242):
            st, week_id, W = self._reference(seed)
            rng = np.random.default_rng(seed + 1000)
            rows = [rng.integers(0, 2, size=W) * 2 - 1 for _ in range(200)]
            rows += [np.where(np.arange(W) == w, -1, 1) for w in range(W)]
            rows += [-np.ones(W, dtype=int)]
            for row in rows:
                linear = float((np.asarray(st.g, dtype=np.float64) @ row)
                               / (2 * st.pair_total))
                self.assertAlmostEqual(
                    linear, self._brute(st, week_id, row), places=9,
                    msg=f"seed={seed} row={row.tolist()}")

    def test_port_matches_reference_object_bit_for_bit(self) -> None:
        for seed in (77, 991):
            st, _week_id, W = self._reference(seed)
            S = np.random.default_rng(seed + 1).integers(
                0, 2, size=(200, W)) * 2 - 1
            port = signflip.linear_deltas(np.asarray(st.g, dtype=np.float64),
                                          S.astype(np.int8),
                                          st.n_pos, st.n_neg)
            ref = np.asarray(st.sign_flip_deltas(S), dtype=np.float64)
            self.assertTrue(np.array_equal(port, ref))

    def test_delta_hat_identity(self) -> None:
        st, week_id, W = self._reference(77)
        # delta_hat is AUC_A - AUC_B (simh10.py:145) and the all-+1 row
        # reproduces it exactly.
        self.assertAlmostEqual(float(st.delta_hat),
                               self._brute(st, week_id, np.ones(W, dtype=int)),
                               places=12)
        all_plus = np.ones((1, W), dtype=np.int8)
        self.assertAlmostEqual(
            float(signflip.linear_deltas(np.asarray(st.g, dtype=np.float64),
                                        all_plus, st.n_pos, st.n_neg)[0]),
            float(st.delta_hat), places=12)


class DrawPropertyTests(unittest.TestCase):
    """A-4 uniform generation; A-5 i.i.d. rows, never curated."""

    def test_a4_rows_are_uniform_signs(self) -> None:
        S, _ = signflip.draw_flips(20, 1000, 20261014)
        self.assertEqual(set(np.unique(S).tolist()), {1, -1})
        col_means = S.mean(axis=0)
        bound = 4.5 / np.sqrt(1000)          # 4.5 sd of a +/-1 sample mean
        self.assertLess(float(np.abs(col_means).max()), bound)
        S_other, _ = signflip.draw_flips(20, 1000, 20261015)
        self.assertFalse(np.array_equal(S, S_other))    # seed-dependent draw

    def test_a5_no_curation_no_reweighting_no_resampling(self) -> None:
        W, M, seed = 15, 300, 42
        S, draw = signflip.draw_flips(W, M, seed)
        raw = np.random.default_rng(seed).integers(0, 2, size=(M, W)) * 2 - 1
        # byte-identical to the raw i.i.d. draw: nothing filtered, capped,
        # deduplicated, or reordered.
        self.assertTrue(np.array_equal(S, raw.astype(np.int8)))
        self.assertEqual(S.shape, (M, W))
        self.assertEqual(draw.M * draw.W, M * W)


class ProvenanceTests(unittest.TestCase):
    """A-6 provenance recorded; A-7 fail-closed refusal; A-8 determinism."""

    def test_a6_provenance_recorded_and_verifiable(self) -> None:
        S, draw = signflip.draw_flips(20, 1000, 20261014)
        self.assertEqual(draw.seed, 20261014)
        self.assertEqual(draw.rng_name, "numpy.random.default_rng")
        self.assertEqual(draw.bitgen, "PCG64")
        self.assertEqual(draw.numpy_version, np.__version__)
        self.assertEqual(draw.stage, "before_outcome_evaluation")
        self.assertEqual(draw.rows_sha256, hashlib.sha256(
            np.ascontiguousarray(S, dtype=np.int8).tobytes()).hexdigest())
        self.assertEqual(len(draw.rows_sha256), 64)

    def test_a7_fail_closed_without_admissible_provenance(self) -> None:
        S, draw = signflip.draw_flips(10, 50, 7)
        g = np.linspace(0.01, 0.1, 10)
        # stage mismatch (a draw not recorded before outcome evaluation)
        bad_stage = dataclasses.replace(draw, stage="after_outcome_inspection")
        with self.assertRaises(signflip.FlipProvenanceMissing):
            signflip.signflip_p_value(0.01, g, bad_stage, S, n_pos=5, n_neg=5)
        # M mismatch
        with self.assertRaises(signflip.FlipProvenanceMissing):
            signflip.signflip_p_value(0.01, g, draw, S[:-1], n_pos=5, n_neg=5)
        # tampered rows -> hash mismatch (any re-draw/regeneration)
        tampered = S.copy()
        tampered[0, 0] = -tampered[0, 0]
        with self.assertRaises(signflip.FlipProvenanceMissing):
            signflip.signflip_p_value(0.01, g, draw, tampered,
                                      n_pos=5, n_neg=5)
        # g length mismatch
        with self.assertRaises(signflip.FlipProvenanceMissing):
            signflip.signflip_p_value(0.01, g[:-1], draw, S,
                                      n_pos=5, n_neg=5)
        # non-record provenance
        with self.assertRaises(signflip.FlipProvenanceMissing):
            signflip.signflip_p_value(0.01, g, None, S, n_pos=5, n_neg=5)

    def test_a8_deterministic_and_recorded_reuse(self) -> None:
        S1, d1 = signflip.draw_flips(20, 1000, 20261014)
        S2, d2 = signflip.draw_flips(20, 1000, 20261014)
        self.assertTrue(np.array_equal(S1, S2))
        self.assertEqual(d1, d2)
        g = np.linspace(0.001, 0.02, 20)
        p1 = signflip.signflip_p_value(0.001, g, d1, S1, n_pos=10, n_neg=10)
        p2 = signflip.signflip_p_value(0.001, g, d2, S2, n_pos=10, n_neg=10)
        self.assertEqual(p1, p2)
        # the frozen config's recorded draw is THE draw: loader reproduces
        # it and refuses anything else.
        config = {"multiplicity_policy": {"flip_draw": d1.to_dict()}}
        seed, S_loaded, d_loaded = signflip.load_campaign_flip_draw(config, W=20)
        self.assertEqual(seed, 20261014)
        self.assertTrue(np.array_equal(S_loaded, S1))
        self.assertEqual(d_loaded, d1)
        tampered = {"multiplicity_policy": {"flip_draw": dict(
            d1.to_dict(), rows_sha256="0" * 64)}}
        with self.assertRaises(signflip.FlipProvenanceMissing):
            signflip.load_campaign_flip_draw(tampered, W=20)
        wrong_stage = {"multiplicity_policy": {"flip_draw": dict(
            d1.to_dict(), stage="after_outcome_evaluation")}}
        with self.assertRaises(signflip.FlipProvenanceMissing):
            signflip.load_campaign_flip_draw(wrong_stage, W=20)
        with self.assertRaises(signflip.FlipProvenanceMissing):
            signflip.load_campaign_flip_draw(
                {"multiplicity_policy": {}}, W=20)
        with self.assertRaises(signflip.FlipProvenanceMissing):
            signflip.load_campaign_flip_draw(config, W=21)   # W mismatch


class A9ResolutionTests(unittest.TestCase):
    """A-9: M pinned; resolution 1/(M+1); feasibility enforces M."""

    def test_resolution_and_feasibility(self) -> None:
        S, draw = signflip.draw_flips(6, 1000, 3)
        g = np.full(6, 0.01)
        p_min = signflip.signflip_p_value(-1e9, g, draw, S, n_pos=10, n_neg=10)
        self.assertEqual(p_min, 1 / 1001)
        # M governs feasibility too: a missing or small M is infeasible,
        # never silently feasible (D2 review Condition 3).
        with self.assertRaises(mult.GranularityInfeasible):
            mult.require_feasible(mult.MIN_N_BOOT, 36, n_flips=500)
        with self.assertRaises(mult.GranularityInfeasible):
            mult.require_feasible(mult.MIN_N_BOOT, 36, n_flips=None)
        mult.require_feasible(mult.MIN_N_BOOT, 36, n_flips=mult.MIN_N_FLIPS)


class A10MultiplicityIntegrationTests(unittest.TestCase):
    """A-10: campaign-end record consumes the approved method + M."""

    def test_campaign_end_record_with_approved_method(self) -> None:
        members = [mult.FamilyMember(
            member_id=f"c-{i}", family="complexity",
            primitive="complexity_reduction_check", experiment_id=f"exp-{i}",
            status=mult.STATUS_AVAILABLE, unadjusted_p=p, ci_upper=-0.5)
            for i, p in enumerate([0.001, 0.4])]
        record = mult.campaign_end_record(
            campaign_id="c4-test", families={"complexity": members},
            n_boot=mult.MIN_N_BOOT, n_flips=mult.MIN_N_FLIPS,
            p_value_method=signflip.APPROVED_METHOD_NAME)
        block = record["families"]["complexity"]
        self.assertEqual(block["feasibility"]["n_flips"], mult.MIN_N_FLIPS)
        self.assertTrue(block["feasibility"]["feasible"])
        self.assertEqual(record["p_value_method"],
                         "week_level_signflip_holm")
        rows = {m["member_id"]: m for m in block["members"]}
        self.assertEqual(rows["c-0"]["unadjusted_p"], 0.001)
        self.assertEqual(rows["c-0"]["formal_status"], mult.FORMAL_REFUTED)
        self.assertNotEqual(rows["c-1"]["formal_status"], mult.FORMAL_REFUTED)
        self.assertIn("procedure-level", record["note"])
        self.assertIn("Monte-Carlo resolution", record["note"])
        # Holm output is the unchanged step-down implementation.
        adjusted, _ = mult.holm_step_down([0.001, 0.4])
        self.assertAlmostEqual(rows["c-0"]["adjusted_p"], adjusted[0])
        self.assertAlmostEqual(rows["c-1"]["adjusted_p"], adjusted[1])


class A11MethodGateTests(unittest.TestCase):
    """A-11: exactly the recorded method passes; nothing else does."""

    def test_gate_bound_to_recorded_decision(self) -> None:
        self.assertEqual(set(mult.approved_p_value_methods()),
                         {signflip.APPROVED_METHOD_NAME})
        self.assertEqual(
            mult.require_approved_method(signflip.APPROVED_METHOD_NAME),
            "week_level_signflip_holm")
        for name in ("signflip", "sign_flip", "week_level_signflip",
                     "week_level_signflip_holm ", "", None):
            with self.assertRaises(mult.PValueMethodUnresolved):
                mult.require_approved_method(name)


class A12EquivalenceFixtureTests(unittest.TestCase):
    """A-12: production port == stored reference values, bit-for-bit."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = FIXTURES.read_bytes()
        cls.payload = json.loads(cls.raw.decode("utf-8"))

    def test_fixture_file_is_the_pinned_one(self) -> None:
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(),
                         FIXTURES_SHA256,
                         "fixture file drift: regenerate ONLY with a "
                         "recorded reason, never to make a test pass")

    def test_every_case_matches_the_reference(self) -> None:
        self.assertEqual(len(self.payload["cases"]), 4)
        for case in self.payload["cases"]:
            with self.subTest(case=case["name"]):
                g = np.asarray(case["g"], dtype=np.float64)
                S, draw = signflip.draw_flips(case["W"], case["M"],
                                               case["seed"])
                self.assertEqual(draw.bitgen, case["bitgen"])
                self.assertEqual(draw.numpy_version, case["numpy_version"])
                self.assertEqual(draw.rows_sha256,
                                 case["rows_sha256_int8_c_order"])
                self.assertEqual([list(map(int, r))
                                  for r in S[:3]], case["reference_rows_head"])
                deltas = signflip.linear_deltas(g, S, case["n_pos"],
                                                case["n_neg"])
                # bit-for-bit against the stored reference deltas
                self.assertTrue(np.array_equal(
                    deltas, np.asarray(case["reference_deltas"],
                                       dtype=np.float64)))
                p = signflip.signflip_p_value(case["delta_hat"], g, draw, S,
                                              n_pos=case["n_pos"],
                                              n_neg=case["n_neg"])
                self.assertEqual(p, case["expected_p"])
                if case["name"] == "tie_heavy":
                    self.assertGreaterEqual(case["ties_at_delta_hat"], 2)


class A13NoSetConditionalClaimsTests(unittest.TestCase):
    """A-5/C-5: no emitted artifact asserts fixed-set conditional exactness."""

    FORBIDDEN = (
        "exactness conditional on",
        "exact conditional on",
        "conditional on the fixed flip set",
        "conditional on the flip set",
        "conditional-on-seed FWER",
        "exact for the realized set",
        "exact for this flip set",
    )

    def test_source_and_config_carry_procedure_level_only(self) -> None:
        targets = [
            ROOT / "autonomous_agent/proposal_layer/multiplicity.py",
            ROOT / "autonomous_agent/proposal_layer/signflip.py",
        ]
        for path in targets:
            text = path.read_text("utf-8").lower()
            for phrase in self.FORBIDDEN:
                self.assertNotIn(phrase, text,
                                 f"{path.name} asserts {phrase!r}")
        for path in targets[:1]:
            text = path.read_text("utf-8")
            self.assertIn("procedure-level", text)
        fields = signflip.disclosure_fields()
        self.assertEqual(fields["validity_scope"],
                         "procedure_level_marginal_over_flip_draw")
        self.assertIn("exchangeability", fields["exchangeability_assumption"])
        # frozen/candidate Campaign 4 config must carry the same scope note
        for cfg_path in (
                ROOT / "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
                       "CAMPAIGN_4_CONFIG_CANDIDATE_2026_10_13.json",
                ROOT / "autonomous_agent/state/campaign_config.json"):
            if not cfg_path.exists():
                continue
            cfg_text = cfg_path.read_text("utf-8")
            if "campaign-4" not in cfg_text:
                continue
            lowered = cfg_text.lower()
            for phrase in self.FORBIDDEN:
                self.assertNotIn(phrase, lowered, cfg_path.name)


if __name__ == "__main__":
    unittest.main()
