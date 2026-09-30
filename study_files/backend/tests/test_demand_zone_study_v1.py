from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import demand_zone_study_v1 as study


class StudyV1Tests(unittest.TestCase):
    def test_historical_replay_cutoff_is_final_fold_end_exclusive(self):
        protocol = study.load_protocol()
        fold_ends = [
            fold["validation_end_exclusive"]
            for fold in protocol["historical_development_evaluation"]["folds"]
        ]
        cutoff = study._historical_replay_cutoff(protocol)
        self.assertEqual(cutoff, max(fold_ends))
        self.assertEqual(cutoff, "2026-01-01")
        self.assertLess(pd.Timestamp("2025-12-31"), pd.Timestamp(cutoff))
        self.assertEqual(pd.Timestamp(cutoff) - pd.Timedelta(days=1), pd.Timestamp("2025-12-31"))

    def test_historical_replay_cutoff_rejects_missing_fold_boundaries(self):
        for folds in ([], [{"name": "2025"}], [{"validation_end_exclusive": None}]):
            with self.subTest(folds=folds), self.assertRaises(ValueError):
                study._historical_replay_cutoff({"historical_development_evaluation": {"folds": folds}})

    def test_immutable_v1_0_1_archive_artifact_hashes_match_manifest(self):
        archive_dir = study.DEVELOPMENT_DIR
        manifest = json.loads((archive_dir / "run_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["protocol_version"], "1.0.1")
        self.assertEqual(
            manifest["protocol_sha256"],
            "486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07",
        )
        self.assertEqual(
            manifest["code_sha256"],
            "29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b",
        )
        for name, expected_hash in manifest["artifact_sha256"].items():
            with self.subTest(artifact=name):
                self.assertEqual(study.sha256_file(archive_dir / name), expected_hash)
        for name, expected_hash in manifest["model_artifacts_sha256"].items():
            with self.subTest(model=name):
                self.assertEqual(study.sha256_file(study.MODEL_DIR / name), expected_hash)

    def test_missing_forward_open_is_not_a_negative_label(self):

        bars = pd.DataFrame(
            {"Open": [100.0, 101.0, np.nan, 104.0], "Close": [100.0] * 4},
            index=pd.bdate_range("2025-01-01", periods=4),
        )
        result = study._target_for_index(bars, 0)
        self.assertFalse(result["label_valid"])
        self.assertIsNone(result["label"])

    def test_invalid_nonpositive_forward_open_is_not_a_negative_label(self):
        for entry, exit_ in [(0.0, 100.0), (100.0, 0.0), (-1.0, 100.0), (100.0, np.inf)]:
            bars = pd.DataFrame(
                {"Open": [100.0, entry, exit_, 104.0]},
                index=pd.bdate_range("2025-01-01", periods=4),
            )
            result = study._target_for_index(bars, 0)
            self.assertFalse(result["label_valid"])
            self.assertIsNone(result["label"])

    def test_valid_target_uses_next_two_opens_and_inclusive_threshold(self):
        bars = pd.DataFrame(
            {"Open": [100.0, 100.0, 102.0, 105.0], "Close": [100.0] * 4},
            index=pd.bdate_range("2025-01-01", periods=4),
        )
        result = study._target_for_index(bars, 0)
        self.assertTrue(result["label_valid"])
        self.assertAlmostEqual(result["hold1_ret"], 0.02)
        self.assertEqual(result["label"], 1)
        self.assertEqual(result["entry_date"], bars.index[1])
        self.assertEqual(result["exit_date"], bars.index[2])

    def test_target_maturity_purge_excludes_boundary_and_future(self):
        dates = pd.Series(pd.to_datetime(["2022-12-28", "2022-12-29", "2022-12-30", "2023-01-03"]))
        exits = pd.Series(pd.to_datetime(["2022-12-30", "2023-01-03", "2023-01-04", "2023-01-05"]))
        folds = study.make_folds(pd.DataFrame({"date": dates, "exit_date": exits}), years=(2023,))
        fold = folds[0]
        train_dates = dates[fold["train_mask"]]
        train_exits = exits[fold["train_mask"]]
        self.assertTrue((train_dates < pd.Timestamp("2023-01-01")).all())
        self.assertTrue((train_exits < pd.Timestamp("2023-01-01")).all())
        self.assertEqual(train_dates.tolist(), [pd.Timestamp("2022-12-28")])

    def test_feature_arms_are_nested_and_match_frozen_protocol(self):
        protocol = study.load_protocol()
        study.validate_feature_whitelist(protocol)
        self.assertLess(len(study.FEATURE_ARMS["A"]), len(study.FEATURE_ARMS["B"]))
        self.assertLess(len(study.FEATURE_ARMS["B"]), len(study.FEATURE_ARMS["C"]))
        self.assertLess(len(study.FEATURE_ARMS["C"]), len(study.FEATURE_ARMS["D"]))
        self.assertEqual(len(study.ESTIMATORS), 2)
        self.assertEqual(protocol["prospective_evaluation"]["minimum_events"], 2000)
        self.assertEqual(protocol["prospective_evaluation"]["maximum_duration_months"], 18)
        self.assertEqual(protocol["reproducibility"]["maximum_prospective_events"], 2000)

    def test_matrix_whitelist_has_no_identifier_or_outcome_fields(self):
        forbidden = set(study.load_protocol()["reproducibility"]["identifiers_excluded_from_X"])
        for features in study.FEATURE_ARMS.values():
            self.assertTrue(forbidden.isdisjoint(features))
            for feature in features:
                self.assertFalse(any(part in feature.lower() for part in study.BANNED_FEATURE_PATTERNS), feature)

    def test_block_bootstrap_uses_identical_paired_rows(self):
        rng = np.random.default_rng(3)
        n = 600
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        labels = rng.integers(0, 2, size=n)
        a = labels * 0.6 + rng.random(n) * 0.4
        frame = pd.DataFrame({"date": dates, "label": labels, "a": a, "b": a})
        delta = study.block_bootstrap_delta(frame, "a", "b", n_boot=25, seed=19)
        self.assertEqual(delta["delta_auc"], 0.0)
        self.assertEqual(delta["seed"], 19)
        self.assertEqual(delta["block_weeks"], 4)

    def test_ledger_appends_and_verifies_hash_chain(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "events.jsonl"
            run_id = "run-1"
            first = study.append_hash_chained_record(path, {
                "record_type": "prediction_run", "requested_signal_date": "2026-10-01",
                "run_id": run_id, "eligible_events": 1, "status": "success",
            })
            second = study.append_hash_chained_record(path, {
                "record_type": "prediction", "event_id": "abc", "event_date": "2026-10-01",
                "prediction_run_id": run_id, "prediction_run_hash": first,
            })
            self.assertNotEqual(first, second)
            result = study.verify_ledger(path)
            self.assertTrue(result["valid"])
            self.assertEqual(result["records"], 2)
            self.assertEqual(result["prediction_events"], 1)
            self.assertEqual(result["prediction_runs"], 1)
            self.assertEqual(result["incomplete_runs"], {})
            raw = path.read_text(encoding="utf-8").splitlines()
            tampered = json.loads(raw[-1])
            tampered["event_id"] = "changed"
            raw[-1] = json.dumps(tampered)
            path.write_text("\n".join(raw) + "\n", encoding="utf-8")
            with self.assertRaises(AssertionError):
                study.verify_ledger(path)

    def test_ledger_rejects_orphan_prediction(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "events.jsonl"
            study.append_hash_chained_record(path, {"record_type": "prediction", "event_id": "orphan"})
            with self.assertRaises(AssertionError):
                study.verify_ledger(path)

    def test_ledger_detects_incomplete_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "events.jsonl"
            study.append_hash_chained_record(path, {
                "record_type": "prediction_run", "requested_signal_date": "2026-10-01",
                "run_id": "partial", "eligible_events": 2, "status": "success",
            })
            result = study.verify_ledger(path)
            self.assertEqual(result["incomplete_runs"]["2026-10-01"], {"expected": 2, "logged": 0})

    def test_fit_preprocessing_is_training_fold_only(self):
        rows = pd.DataFrame({"x": [1.0, 3.0, np.nan]})
        fitted = study.fit_pipeline("LogisticRegression", ["x"], rows, np.array([0, 1, 0]))
        self.assertEqual(fitted["imputer"].statistics_[0], 2.0)
        self.assertEqual(fitted["scaler"].mean_[0], 2.0)
        validation = pd.DataFrame({"x": [10000.0]})
        self.assertEqual(study.predict_pipeline(fitted, validation).shape, (1,))

    def test_all_eight_predictions_share_identical_events_and_labels(self):
        rng = np.random.default_rng(25)
        n = 180
        labels = np.tile([0, 1], n // 2)
        rows = pd.DataFrame({name: rng.normal(size=n) for name in study.FEATURE_ARMS["D"]})
        rows["date"] = pd.date_range("2020-01-01", periods=n, freq="D")
        rows["event_id"] = [f"event-{i}" for i in range(n)]
        row_key = list(zip(rows.event_id, labels))
        prediction_keys = {}
        for estimator in study.ESTIMATORS:
            for arm, features in study.FEATURE_ARMS.items():
                model = study.fit_pipeline(estimator, features, rows, labels)
                prediction = study.predict_pipeline(model, rows)
                self.assertEqual(prediction.shape, (n,))
                prediction_keys[f"{estimator}_{arm}"] = list(zip(rows.event_id, labels))
        self.assertTrue(all(keys == row_key for keys in prediction_keys.values()))

    def test_order_block_tracker_is_prefix_invariant(self):
        dates = pd.bdate_range("2024-01-01", periods=180)
        close = np.full(len(dates), 100.0)
        open_ = close.copy()
        high, low = close + 0.1, close - 0.1
        volume = np.full(len(dates), 1000.0)
        open_[119], close[119], high[119], low[119] = 100.0, 99.5, 100.1, 99.4
        open_[120], close[120], high[120], low[120], volume[120] = 100.0, 103.0, 103.2, 99.8, 2000.0
        close[121:] = 103.0
        open_[121:] = 103.0
        high[121:] = 103.1
        low[121:] = 102.9
        bars = pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=dates)
        cutoff = 150
        full_indicators = study.calculate_stock_indicators(bars)
        full_tracker = study.CausalOrderBlockTracker(bars, full_indicators, min_bars=100, max_age_days=90)
        for idx in range(cutoff + 1):
            full_tracker.advance(idx)
        prefix = bars.iloc[:cutoff + 1].copy()
        prefix_indicators = study.calculate_stock_indicators(prefix)
        prefix_tracker = study.CausalOrderBlockTracker(prefix, prefix_indicators, min_bars=100, max_age_days=90)
        for idx in range(cutoff + 1):
            prefix_tracker.advance(idx)
        expected = full_tracker.features(float(bars.Close.iloc[cutoff]), dates[cutoff], cutoff)
        actual = prefix_tracker.features(float(prefix.Close.iloc[-1]), dates[cutoff], cutoff)
        for key in expected:
            self.assertTrue(np.isclose(expected[key], actual[key], equal_nan=True), key)
        self.assertEqual(actual["ob_bull_exists"], 1.0)

    def test_event_replay_is_prefix_invariant(self):
        dates = pd.bdate_range("2022-01-03", periods=380)
        close = np.full(len(dates), 105.0)
        open_ = close.copy()
        high = np.full(len(dates), 106.0)
        low = np.full(len(dates), 104.0)
        volume = np.full(len(dates), 1000.0)
        for pivot in (120, 200, 280):
            for offset, value in [(-2, 102.0), (-1, 101.0), (0, 99.0), (1, 101.0), (2, 102.0)]:
                low[pivot + offset] = value
            low[pivot + 3] = 100.0
            low[pivot + 15] = 100.5
        bars = pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=dates)
        markets = {name: bars.copy() for name in ("SPY", "QQQ", "IWM", "^VIX")}

        def market_features_for(source):
            return {
                "SPY": study.calculate_market_indicators(source["SPY"], "spy"),
                "QQQ": study.calculate_market_indicators(source["QQQ"], "qqq"),
                "IWM": study.calculate_market_indicators(source["IWM"], "iwm"),
                "VIX": study.calculate_market_indicators(source["^VIX"], "vix", vix=True),
            }

        cutoff = 330
        full_events = study.generate_symbol_events(
            "TEST", bars, markets, market_features_for(markets), min_date=dates[0],
            max_date_exclusive=dates[cutoff + 1], include_labels=False,
        )
        truncated_bars = bars.iloc[:cutoff + 1].copy()
        truncated_markets = {name: value.iloc[:cutoff + 1].copy() for name, value in markets.items()}
        truncated_events = study.generate_symbol_events(
            "TEST", truncated_bars, truncated_markets, market_features_for(truncated_markets),
            min_date=dates[0], include_labels=False,
        )
        self.assertTrue(full_events, "synthetic series should contain candidate zone retests")
        first_signal_date = pd.Timestamp(full_events[0]["date"])
        excluded_at_boundary = study.generate_symbol_events(
            "TEST", bars, markets, market_features_for(markets), min_date=dates[0],
            max_date_exclusive=first_signal_date, include_labels=False,
        )
        included_before_next_calendar_day = study.generate_symbol_events(
            "TEST", bars, markets, market_features_for(markets), min_date=dates[0],
            max_date_exclusive=first_signal_date + pd.Timedelta(days=1), include_labels=False,
        )
        self.assertFalse(any(pd.Timestamp(row["date"]) >= first_signal_date for row in excluded_at_boundary))
        self.assertTrue(any(pd.Timestamp(row["date"]) == first_signal_date for row in included_before_next_calendar_day))
        self.assertEqual([row["event_id"] for row in full_events], [row["event_id"] for row in truncated_events])
        for before, after in zip(full_events, truncated_events):
            self.assertEqual(before["feature_asof_date"], after["feature_asof_date"])
            for key in study.FEATURE_ARMS["D"]:
                self.assertTrue(np.isclose(before[key], after[key], equal_nan=True), (before["event_id"], key))

    def test_prospective_maturity_requires_both_time_and_matured_events(self):
        first = "2026-10-01T20:00:00+00:00"
        early_cap = study._prospective_maturity_state(
            first, 2000, 2000, now="2027-03-01T12:00:00+00:00"
        )
        self.assertFalse(early_cap["analysis_ready"])
        self.assertEqual(early_cap["status"], "event_cap_reached_waiting_for_12_month_minimum")
        twelve_months_and_two_thousand = study._prospective_maturity_state(
            first, 2000, 2000, now="2027-10-01T22:00:00+00:00"
        )
        self.assertTrue(twelve_months_and_two_thousand["analysis_ready"])
        shortfall = study._prospective_maturity_state(
            first, 2000, 1999, now="2027-10-02T12:00:00+00:00"
        )
        self.assertFalse(shortfall["analysis_ready"])
        self.assertEqual(shortfall["status"], "event_cap_reached_below_matured_minimum_after_12_months")
        after_max = study._prospective_maturity_state(
            first, 1200, 1200, now="2028-04-02T12:00:00+00:00"
        )
        self.assertFalse(after_max["analysis_ready"])
        self.assertTrue(after_max["prediction_window_closed"])

    def test_no_candidate_run_does_not_start_prospective_clock(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "events.jsonl"
            study.append_hash_chained_record(path, {
                "record_type": "prediction_run", "requested_signal_date": "2026-10-01",
                "run_id": "empty-run", "status": "no_candidate_events", "eligible_events": 0,
            })
            status = {"status": "locked_waiting_for_first_post_lock_prediction_and_fresh_data"}
            refreshed = study._refresh_status_from_ledger(status, {}, ledger_path=path)
            self.assertIsNone(refreshed.get("first_prospective_prediction_date"))
            self.assertFalse(refreshed["analysis_ready"])

    def test_universe_hash_uses_canonical_newline_delimiters(self):
        roster = ["AAPL", "MSFT"]
        expected = study.sha256_bytes(b"AAPL\nMSFT\n")
        self.assertEqual(study._universe_sha256(roster), expected)
        self.assertEqual(study._universe_sha256(list(reversed(roster))), expected)
        self.assertNotEqual(study._universe_sha256(roster), study.sha256_bytes(r"AAPL\nMSFT\n".encode()))

    def test_mature_outcomes_accept_canonical_universe_hash(self):
        today_ny = pd.Timestamp.now(tz="America/New_York").normalize().tz_localize(None)
        dates = pd.bdate_range(end=today_ny - pd.offsets.BDay(3), periods=4)
        bars = pd.DataFrame(
            {
                "Open": [99.0, 100.0, 100.0, 102.0],
                "High": [100.0, 101.0, 101.0, 103.0],
                "Low": [98.0, 99.0, 99.0, 101.0],
                "Close": [99.0, 100.0, 100.0, 102.0],
                "Volume": [1000.0] * 4,
            },
            index=dates,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "data"
            prospective_dir = root / "artifacts" / "prospective"
            data_dir.mkdir()
            prospective_dir.mkdir(parents=True)
            bars.rename_axis("Date").to_csv(data_dir / "AAL.csv", date_format="%Y-%m-%d")
            source_bars = study.read_ohlcv("AAL", data_dir)
            ticker = "AAL"
            event_date = str(dates[1].date())
            event_id = study.stable_id(ticker, event_date)
            run_id = "maturity-regression"
            lock_timestamp = (dates[0] + pd.Timedelta(hours=17)).tz_localize("UTC")
            prediction_timestamp = (dates[1] + pd.Timedelta(hours=21)).tz_localize("UTC")
            lock = {
                "protocol_id": study.load_protocol()["protocol_id"],
                "lock_timestamp_utc": lock_timestamp.isoformat(),
                "code_sha256": study.sha256_file(Path(study.__file__).resolve()),
                "protocol_sha256": study.sha256_file(study.PROTOCOL_PATH),
                "test_suite_sha256": study.sha256_file(Path(__file__).resolve()),
                "roster_source_sha256": study.sha256_file(study.ROSTER_SOURCE),
                "universe_sha256": study._universe_sha256(study.load_roster()),
                "source_data_latest_bar_date": str(dates[0].date()),
                "source_data_max_date_by_symbol": {ticker: str(dates[0].date())},
                "source_data_prefix_sha256": {ticker: study._prefix_hash(source_bars, dates[0])},
                "model_artifacts_sha256": {},
            }
            lock_path = prospective_dir / "lock.json"
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            (prospective_dir / "status.json").write_text("{}", encoding="utf-8")
            ledger_path = prospective_dir / "events.jsonl"
            run_hash = study.append_hash_chained_record(
                ledger_path,
                {
                    "record_type": "prediction_run",
                    "requested_signal_date": event_date,
                    "run_id": run_id,
                    "eligible_events": 1,
                    "status": "success",
                },
            )
            study.append_hash_chained_record(
                ledger_path,
                {
                    "record_type": "prediction",
                    "event_id": event_id,
                    "event_date": event_date,
                    "ticker": ticker,
                    "eligible_event": True,
                    "prediction_timestamp_utc": prediction_timestamp.isoformat(),
                    "prediction_run_id": run_id,
                    "prediction_run_hash": run_hash,
                },
            )

            result = study.mature_prospective_outcomes(
                data_dir=data_dir,
                artifact_dir=root / "artifacts",
            )

            self.assertEqual(result["matured_now"], 1)
            self.assertEqual(result["ledger"]["matured_outcomes"], 1)

    def test_event_id_is_ticker_session_not_zone(self):
        first = study.stable_id("AAPL", "2025-01-02")
        second = study.stable_id("AAPL", "2025-01-02")
        other_ticker = study.stable_id("MSFT", "2025-01-02")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other_ticker)


if __name__ == "__main__":
    unittest.main()
