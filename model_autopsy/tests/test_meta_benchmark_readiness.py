"""Offline readiness tests for the Meta paired benchmark.

No network is used. Fake clients return synthetic responses only; no real
credentials are read or printed.
"""
from __future__ import annotations

import json
import shutil
import types

import pytest

from model_autopsy.benchmarks import meta_paired_continuation_benchmark as bench

CAPS = {
    "max_attempts": 10,
    "max_total_tokens": 100_000,
    "max_est_cost": 1.0,
    "repeated_429_limit": 3,
}


class FakeClient:
    MAX_RETRIES = 3

    def __init__(self, response: dict):
        self.response = response
        self.calls = 0
        self.max_retries_seen = None

    def create_response(self, **kwargs):
        self.calls += 1
        self.max_retries_seen = self.MAX_RETRIES
        return dict(self.response)

    @staticmethod
    def usage(response: dict) -> dict:
        return dict(response.get("usage") or {})


def _args(**overrides):
    values = dict(pairs=2, max_attempts=40, max_total_tokens=150_000,
                  max_est_cost=1.0, repeated_429_limit=3, out="unused.json")
    values.update(overrides)
    return types.SimpleNamespace(**values)


def test_pre_registered_limits_cannot_be_raised() -> None:
    bench._validate_caps(_args())
    for field, value in (("pairs", 3), ("max_attempts", 41),
                         ("max_total_tokens", 150_001),
                         ("max_est_cost", 1.01),
                         ("repeated_429_limit", 4)):
        with pytest.raises(SystemExit) as excinfo:
            bench._validate_caps(_args(**{field: value}))
        assert "No request was made" in str(excinfo.value)


def test_new_sandbox_session_uses_distinct_databases() -> None:
    session1, engine1, dir1 = bench._new_sandbox_session()
    session2, engine2, dir2 = bench._new_sandbox_session()
    try:
        assert dir1 != dir2
        assert session1.bind.url.database != session2.bind.url.database
        from sqlalchemy import inspect
        assert "investigations" in inspect(engine1).get_table_names()
        assert "investigations" in inspect(engine2).get_table_names()
    finally:
        session1.close()
        session2.close()
        engine1.dispose()
        engine2.dispose()
        shutil.rmtree(dir1, ignore_errors=True)
        shutil.rmtree(dir2, ignore_errors=True)


def test_per_run_db_supports_real_engine_and_quality() -> None:
    from model_autopsy.backend import engine as backend_engine

    session, run_engine, run_dir = bench._new_sandbox_session()
    try:
        inv = backend_engine.create_investigation(
            session, "ml", "readiness-db-check", bench.OBJECTIVE,
            dict(bench.RUN_CFG))
        backend_engine.build_context(session, inv)
        quality = bench._quality(
            session, backend_engine, inv, "delta",
            {"status": "ok", "response_id": "r1",
             "summary": {"valid": True}, "message_text": "",
             "usage_rollup": {}},
            {"status": "ok", "response_id": "r2",
             "summary": {"valid": True}, "message_text": "",
             "usage_rollup": {}},
            "r1", request_entries=[], turn1_last_response_id="r1",
            turn2_last_response_id="r2")
        assert quality["investigation_id"] == inv.id
        assert quality["run_outcome"] == "completed"
        assert quality["investigation_complete"] is True
    finally:
        session.close()
        run_engine.dispose()
        shutil.rmtree(run_dir, ignore_errors=True)


def test_cap_is_checked_before_request() -> None:
    caps = dict(CAPS, max_attempts=1)
    ledger = bench.RequestLedger(caps)
    ledger.total_attempts = 1
    client = FakeClient({"id": "resp1", "status": "completed", "usage": {}})
    ledger.attach(client)

    with pytest.raises(bench._BenchmarkCapReached) as excinfo:
        client.create_response(model="muse-spark-1.3", input_items=[], tools=[])

    assert client.calls == 0
    assert "before request" in str(excinfo.value)
    assert ledger.blocked_before_request == 1


class FailingClient:
    def create_response(self, **kwargs):
        exc = RuntimeError("Authorization: Bearer dummy-secret-not-real")
        exc.status_code = 401
        raise exc

    @staticmethod
    def usage(response: dict) -> dict:
        return {}


class RateLimitedClient:
    def create_response(self, **kwargs):
        exc = RuntimeError("HTTP 429: rate limited (after 3 attempts)")
        exc.status_code = 429
        raise exc

    @staticmethod
    def usage(response: dict) -> dict:
        return {}


def test_429_attempts_count_toward_consecutive_limit() -> None:
    ledger = bench.RequestLedger(CAPS)
    client = RateLimitedClient()
    ledger.attach(client)

    with pytest.raises(RuntimeError):
        client.create_response(model="muse-spark-1.3", input_items=[], tools=[])

    assert ledger.consecutive_429 == 3
    assert "repeated provider rate limits" in ledger.stop_reason


class FakeMetaUnavailable(RuntimeError):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class MetaFailingClient:
    MetaUnavailable = FakeMetaUnavailable

    def create_response(self, **kwargs):
        raise FakeMetaUnavailable(
            "HTTP 401: Authorization: Bearer dummy-secret-not-real", 401)

    @staticmethod
    def usage(response: dict) -> dict:
        return {}


def test_meta_exception_is_sanitized_before_production_sees_it() -> None:
    ledger = bench.RequestLedger(CAPS)
    client = MetaFailingClient()
    ledger.attach(client)

    with pytest.raises(FakeMetaUnavailable) as excinfo:
        client.create_response(model="muse-spark-1.3", input_items=[], tools=[])

    assert excinfo.value.status_code == 401
    assert "dummy-secret-not-real" not in str(excinfo.value)
    assert ledger.entries[-1]["error"] == "provider error (HTTP 401); body omitted"


def test_error_text_is_not_persisted_raw() -> None:
    ledger = bench.RequestLedger(CAPS)
    client = FailingClient()
    ledger.attach(client)

    with pytest.raises(RuntimeError):
        client.create_response(model="muse-spark-1.3", input_items=[], tools=[])

    entry = ledger.entries[-1]
    assert entry["http_status"] == 401
    assert entry["error_type"] == "RuntimeError"
    assert entry["error"] == "provider error (HTTP 401); body omitted"
    assert "dummy-secret-not-real" not in json.dumps(ledger.entries)


def test_remaining_attempts_cap_the_client_retry_loop() -> None:
    ledger = bench.RequestLedger(dict(CAPS, max_attempts=40))
    ledger.total_attempts = 39
    client = FakeClient({
        "id": "resp1", "status": "completed",
        "usage": {"input_tokens": 1, "output_tokens": 1,
                  "input_tokens_details.cached_tokens": 0},
    })
    ledger.attach(client)

    client.create_response(model="muse-spark-1.3", input_items=[], tools=[])

    assert client.max_retries_seen == 1
    assert client.MAX_RETRIES == 3
    assert ledger.total_attempts == 40
    with pytest.raises(bench._BenchmarkCapReached):
        client.create_response(model="muse-spark-1.3", input_items=[], tools=[])
    assert client.calls == 1


def test_incomplete_and_missing_usage_are_recorded() -> None:
    ledger = bench.RequestLedger(CAPS)
    ledger.current_run = "p1-full"
    ledger.current_turn = 1
    client = FakeClient({
        "id": "resp1",
        "status": "incomplete",
        "incomplete_details": {"reason": "max_output_tokens"},
        "usage": {"input_tokens": 100,
                  "input_tokens_details.cached_tokens": 40},
    })
    ledger.attach(client)

    client.create_response(model="muse-spark-1.3", input_items=[], tools=[])

    entry = ledger.entries[-1]
    assert entry["incomplete"] is True
    assert entry["incomplete_reason"] == "max_output_tokens"
    assert entry["usage_missing"] is True
    assert entry["usage_missing_fields"] == ["output_tokens"]
    assert ledger.usage_missing_requests == 1
    assert ledger.total_input == 100
    assert ledger.total_cached == 40


def test_cached_tokens_are_not_double_counted() -> None:
    # cached 400*0.15 + uncached 600*1.25 + output 100*4.25, per 1M.
    assert bench._est_cost(1000, 100, 400) == pytest.approx(0.001235)
    # cached cannot exceed input; the excess is clamped, not charged twice.
    assert bench._est_cost(100, 0, 200) == pytest.approx(0.000015)


def test_run_outcome_marks_incomplete_provider_responses() -> None:
    assert bench._classify_run_outcome(
        turn1_status="ok", turn2_status="ok", summary_valid=True,
        both_turns=True, incomplete_count=0,
        status_unknown_count=0) == "completed"
    assert bench._classify_run_outcome(
        turn1_status="ok", turn2_status="ok", summary_valid=True,
        both_turns=True, incomplete_count=1,
        status_unknown_count=0) == "incomplete_provider_response"
    assert bench._classify_run_outcome(
        turn1_status="ok", turn2_status="ok", summary_valid=True,
        both_turns=True, incomplete_count=0,
        status_unknown_count=0,
        noncompleted_status_count=1) == "provider_status_not_completed"
    assert bench._classify_run_outcome(
        turn1_status="ok", turn2_status=None, summary_valid=True,
        both_turns=False, incomplete_count=0,
        status_unknown_count=0) == "turn_incomplete"
    assert bench._classify_run_outcome(
        turn1_status="ok", turn2_status="ok", summary_valid=False,
        both_turns=True, incomplete_count=0,
        status_unknown_count=0) == "invalid_summary"


class _EmptyQuery:
    def filter_by(self, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return []


class _FakeSession:
    def query(self, model):
        return _EmptyQuery()


def test_quality_records_repair_chain_mismatch() -> None:
    inv = types.SimpleNamespace(id="inv1")
    result1 = {
        "status": "ok", "response_id": "resp_before_repair",
        "summary": {"valid": True}, "message_text": "",
        "usage_rollup": {"summary_repair_attempts": 1},
    }
    result2 = {
        "status": "ok", "response_id": "resp2",
        "summary": {"valid": True}, "message_text": "",
        "usage_rollup": {"summary_repair_attempts": 0},
    }
    entries = [
        {"ok": True, "incomplete": False, "response_status": "completed",
         "turn": 1, "usage_missing": False},
        {"ok": True, "incomplete": False, "response_status": "completed",
         "turn": 2, "usage_missing": False},
    ]

    quality = bench._quality(
        _FakeSession(), None, inv, "full", result1, result2,
        "resp_before_repair", request_entries=entries,
        turn1_last_response_id="resp_after_repair",
        turn2_last_response_id="resp2")

    assert quality["summary_repair_used_turn1"] == 1
    assert quality["turn1_returned_response_id_is_latest"] is False
    assert quality["chain_used_is_latest_turn1_response"] is False
    assert quality["run_outcome"] == "completed"


def test_run_live_stops_and_reports_cap_without_request(
        monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(bench, "CAMPAIGN_ROOT", tmp_path / "campaigns")
    class FakeSession:
        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    class FakeEngine:
        def create_investigation(self, *args, **kwargs):
            return types.SimpleNamespace(id="inv1")

        def build_context(self, *args, **kwargs):
            pass

    class FakeMetaClient:
        MAX_RETRIES = 3

        def create_response(self, **kwargs):
            raise AssertionError("no request expected")

        @staticmethod
        def usage(response):
            return {}

    class FakeMetaLoop:
        _SUMMARY_REPAIR_TOKENS = 1200

        @staticmethod
        def _continuation_delta_items(session, inv):
            return []

        @staticmethod
        def _initial_context_items(session, inv):
            return []

        @staticmethod
        def run_meta_turn(*args, **kwargs):
            raise bench._BenchmarkCapReached(
                "attempt ceiling reached before request: 40 >= 40")

    fake_config = types.SimpleNamespace(
        meta_base_url=lambda: "https://api.meta.ai/v1",
        meta_model_id=lambda: "muse-spark-1.3")
    monkeypatch.setattr(bench, "bootstrap_env", lambda key_required=False: None)
    monkeypatch.setattr(
        bench, "_setup_imports",
        lambda: (FakeEngine(), FakeMetaClient(), FakeMetaLoop(), fake_config,
                 FakeSession, lambda: None))
    out_path = tmp_path / "report.json"
    args = types.SimpleNamespace(
        pairs=1, max_attempts=40, max_total_tokens=150_000,
        max_est_cost=1.0, repeated_429_limit=3, out=str(out_path))

    bench.run_live(args)

    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["runs"][0]["status"] == "stopped_cap"
    assert "attempt ceiling" in report["totals"]["stop_reason"]
    assert report["totals"]["billed_requests"] == 0
    assert report["totals"]["total_attempts"] == 0
    assert report["sandbox_db_shared_across_runs"] is False
    assert len(report["sandbox_db_paths"]) == 1


def test_quality_marks_repaired_continuation_as_latest() -> None:
    """Protocol v2: a repaired turn reports the repaired id, the chain uses it,
    and _quality records that audit instead of a legacy mismatch."""
    inv = types.SimpleNamespace(id="inv1")
    repaired_state = {"attempted": True, "valid": True,
                      "response_id_source": "repair"}
    result1 = {
        "status": "ok", "response_id": "resp_after_repair",
        "summary": {"valid": True}, "message_text": "",
        "usage_rollup": {"summary_repair_attempts": 1},
        "continuation_state": repaired_state,
    }
    result2 = {
        "status": "ok", "response_id": "resp2",
        "summary": {"valid": True}, "message_text": "",
        "usage_rollup": {"summary_repair_attempts": 0},
        "continuation_state": {"attempted": False, "valid": None,
                               "response_id_source": "original"},
    }
    entries = [
        {"ok": True, "incomplete": False, "response_status": "completed",
         "turn": 1, "usage_missing": False},
        {"ok": True, "incomplete": False, "response_status": "completed",
         "turn": 2, "usage_missing": False},
    ]

    quality = bench._quality(
        _FakeSession(), None, inv, "delta", result1, result2,
        "resp_after_repair", request_entries=entries,
        turn1_last_response_id="resp_after_repair",
        turn2_last_response_id="resp2")

    assert quality["summary_repair_used_turn1"] == 1
    assert quality["turn1_returned_response_id_is_latest"] is True
    assert quality["chain_used_is_latest_turn1_response"] is True
    assert quality["turn1_continuation_state"] == repaired_state
    assert quality["turn2_continuation_state"]["response_id_source"] == "original"
    assert quality["context_strategy"] == "delta"
    assert quality["run_outcome"] == "completed"


def test_offline_benchmark_preserves_payload_difference(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """The continuation-id fix must not change the intended Full-vs-Delta
    payload difference: baseline reconstruction stays byte-exact and the delta
    payload stays smaller. Offline only; a dummy key is used."""
    monkeypatch.setenv("MODEL_API_KEY", "offline-placeholder-not-a-real-key")

    report = json.loads(bench.run_offline())

    assert report["mode"] == "offline"
    assert report["baseline_patch_exact"] is True
    assert report["payload_sizes"]["delta_is_smaller"] is True
    assert report["payload_sizes"]["delta_chars"] < \
        report["payload_sizes"]["full_context_chars"]
    assert "offline-placeholder-not-a-real-key" not in json.dumps(report)


def test_quality_does_not_mark_incomplete_run_complete() -> None:
    inv = types.SimpleNamespace(id="inv1")
    result1 = {
        "status": "ok", "response_id": "resp1",
        "summary": {"valid": True}, "message_text": "",
        "usage_rollup": {},
    }
    result2 = {
        "status": "ok", "response_id": "resp2",
        "summary": {"valid": True}, "message_text": "",
        "usage_rollup": {},
    }
    entries = [
        {"ok": True, "incomplete": True, "response_status": "incomplete",
         "turn": 1, "usage_missing": False},
        {"ok": True, "incomplete": False, "response_status": "completed",
         "turn": 2, "usage_missing": False},
    ]

    quality = bench._quality(
        _FakeSession(), None, inv, "delta", result1, result2,
        "resp1", request_entries=entries,
        turn1_last_response_id="resp1",
        turn2_last_response_id="resp2")

    assert quality["run_outcome"] == "incomplete_provider_response"
    assert quality["investigation_complete"] is False
    assert quality["incomplete_turn1"] == 1
