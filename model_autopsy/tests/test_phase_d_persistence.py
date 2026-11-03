"""Phase 3 — simulated offline test suite for Phase 2 persistence repairs.

Covers, with ZERO network and NO real provider key:

- durable incremental evidence: every provider request/response (full verbatim
  response payload), complete final assistant messages with response ids, usage
  rows, summary-repair records, and a durable copy of the final sandbox DB.
- atomic finalization: run_manifest.json is written with per-artifact SHA-256
  records and required-evidence flags; missing evidence is reported, never
  invented.
- safe cleanup: the volatile sandbox dir is deleted only after the durable
  manifest confirms finalized evidence; otherwise it is kept and reported.
- crash recovery: incremental evidence surviving a mid-run crash is preserved
  verbatim and marked `crashed_or_interrupted`; nothing is deleted.
- secret hygiene: no credential material is ever written.
- simulated live run: a fully faked backend + provider exercises run_live end
  to end (success path) and a mid-turn cap path, verifying the campaign report.
"""
from __future__ import annotations

import hashlib
import json
import types
from pathlib import Path

import pytest

from model_autopsy.benchmarks import bench_persistence as persistence
from model_autopsy.benchmarks import meta_paired_continuation_benchmark as bench


# ---------------------------------------------------------------------------
# Fakes for the simulated live run
# ---------------------------------------------------------------------------

class _FakeEventsRow:
    seq = 1
    kind = "assistant_message"
    title = "event"
    detail = "capability check"
    payload = {"seq": 1}
    investigation_id = property(
        lambda self: FakeEngine.current_inv_id)


class _FakeActionsRow:
    seq = 1
    tool_name = "run_sql"
    status = "ran"
    investigation_id = property(
        lambda self: FakeEngine.current_inv_id)


class _FakeHypothesisRow:
    id = "h1"
    text = "hypo"
    status = "confirmed"
    investigation_id = property(
        lambda self: FakeEngine.current_inv_id)


class _QueryStub:
    def __init__(self, rows):
        self._rows = rows

    def filter_by(self, **kwargs):
        return self

    def all(self):
        return self._rows


class _ScalarsStub:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self._rows


class FakeSession:
    """Backed by canned query results; enough surface for _quality and
    RunRecorder.dump_investigation."""

    def __init__(self):
        self.events = [_FakeEventsRow()]
        self.actions = [_FakeActionsRow()]
        self.hypotheses = [_FakeHypothesisRow()]

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    def query(self, model):
        from model_autopsy.backend.db import Action, Event, Hypothesis
        if model is Event:
            return _QueryStub(self.events)
        if model is Action:
            return _QueryStub(self.actions)
        return _QueryStub(self.hypotheses)

    def execute(self, stmt, *args, **kwargs):
        # dump_investigation selects Event, then Action, then Hypothesis.
        sql = str(stmt).lower()
        if "action" in sql:
            return _ScalarsStub(self.actions)
        if "hypothesis" in sql:
            return _ScalarsStub(self.hypotheses)
        return _ScalarsStub(self.events)


class FakeEngine:
    current_inv_id: str | None = None

    @classmethod
    def create_investigation(cls, session, domain, name, objective, cfg):
        cls.current_inv_id = name
        return types.SimpleNamespace(id=name)

    @staticmethod
    def build_context(session, inv):
        pass


def _provider_response(response_id: str, status: str = "completed") -> dict:
    return {
        "id": response_id,
        "model": "muse-spark-1.3",
        "status": status,
        "output": [{"type": "message", "content": [
            {"type": "output_text", "text":
             f"FINAL MESSAGE MARKER {response_id}"}]}],
        "usage": {"input_tokens": 100, "output_tokens": 50,
                  "input_tokens_details": {"cached_tokens": 10}},
        "_request_perf": {"latency_s": 0.01, "attempts": 1},
    }


class FakeMetaClientModule(types.ModuleType):
    """Module-like provider stand-in; the ledger wraps create_response on it.

    Scenario hooks (class attributes, reset by `_harness` before every run):
    - `status_queue`: per-call provider statuses (e.g. `["incomplete", ...]`)\n      to simulate max-output-token stops; empty means all `"completed"`.
    - `usage_override`: replacement usage dict (e.g. `{}`) to simulate a\n      provider response with missing usage accounting.
    """
    status_queue: list = []
    usage_override = None

    def __init__(self):
        super().__init__("fake_meta_client")
        self.MAX_RETRIES = 3
        self.calls: list = []
        self.requests_blocked = 0
        self.MetaUnavailable = type(
            "MetaUnavailable", (RuntimeError,), {"status_code": None})

        def create_response(**kwargs):
            if self.requests_blocked:
                raise bench._BenchmarkCapReached("cap before request")
            self.calls.append(kwargs)
            previous = bool(kwargs.get("previous_response_id"))
            status = (FakeMetaClientModule.status_queue.pop(0)
                      if FakeMetaClientModule.status_queue else "completed")
            return _provider_response("resp2" if previous else "resp1",
                                       status=status)

        self.create_response = create_response

    @staticmethod
    def usage(response):
        if FakeMetaClientModule.usage_override is not None:
            return dict(FakeMetaClientModule.usage_override)
        return {"input_tokens": 100, "output_tokens": 50,
                "input_tokens_details.cached_tokens": 10}


class FakeMetaLoop:
    """Mirrors the two-turn shape of run_meta_turn as a self-contained mini
    loop over the (ledger-wrapped) client."""

    _SUMMARY_REPAIR_TOKENS = 1200
    current_client = None
    turn_cap_exception = None
    # When False the fake returns a malformed (invalid) structured summary,
    # exercising the harness's invalid-summary preservation path.
    summary_valid = True

    @staticmethod
    def _continuation_delta_items(session, inv):
        return []

    @staticmethod
    def _initial_context_items(session, inv):
        return []

    @staticmethod
    def run_meta_turn(session, inv, max_rounds=3, previous_response_id=None):
        client = FakeMetaLoop.current_client
        turn_cap = FakeMetaLoop.turn_cap_exception
        FakeMetaLoop.turn_cap_exception = None
        if turn_cap is not None:
            client.create_response(model="m", input_items=[], tools=[])
            raise turn_cap("attempt ceiling reached mid-run")
        resp = client.create_response(model="m", input_items=[], tools=[],
                                      previous_response_id=previous_response_id)
        response_id = str(resp.get("id"))
        valid = bool(FakeMetaLoop.summary_valid)
        return {
            "status": "ok",
            "response_id": response_id,
            "message_text": ("FINAL MESSAGE MARKER " + response_id +
                             " complete analysis") if valid else (
                                 "truncated prose without any summary block"),
            "summary": ({"valid": True, "summary": {"conclusion": "ok"}}
                          if valid else
                          {"valid": False, "summary": None,
                           "errors": ["no investigation_summary block"]}),
            "usage_rollup": {"summary_repair_attempts": 0},
            "continuation_state": {"attempted": False, "valid": None,
                                   "response_id_source": "original"},
            "repairs": [],
        }


# ---------------------------------------------------------------------------
# Helper: common monkeypatching harness for run_live
# ---------------------------------------------------------------------------

def _harness(monkeypatch, tmp_path, pairs=1, cap_exc=None):
    campaign_root = tmp_path / "campaigns"
    campaign_root.mkdir(exist_ok=True)
    monkeypatch.setattr(bench, "CAMPAIGN_ROOT", campaign_root)
    # Reset every scenario hook so tests never leak state into each other.
    FakeMetaClientModule.status_queue = []
    FakeMetaClientModule.usage_override = None
    FakeMetaLoop.summary_valid = True
    FakeMetaLoop.turn_cap_exception = None
    if cap_exc is not None:
        FakeMetaLoop.turn_cap_exception = cap_exc
    fake_config = types.SimpleNamespace(
        meta_base_url=lambda: "https://api.meta.ai/v1",
        meta_model_id=lambda: "muse-spark-1.3")

    def _setup():
        client = FakeMetaClientModule()
        loop = FakeMetaLoop()
        FakeMetaLoop.current_client = client
        return FakeEngine(), client, loop, fake_config, FakeSession, (
            lambda: None)

    monkeypatch.setattr(bench, "_setup_imports", _setup)
    monkeypatch.setattr(bench, "bootstrap_env", lambda key_required=False: None)
    out_path = tmp_path / "report.json"
    args = types.SimpleNamespace(
        pairs=pairs, max_attempts=40, max_total_tokens=150_000,
        max_est_cost=1.0, repeated_429_limit=3, out=str(out_path))
    return args, out_path, campaign_root


# ---------------------------------------------------------------------------
# Unit tests: recorder + finalization + cleanup guard + recovery + redaction
# ---------------------------------------------------------------------------

def _make_sqlite_db(base: Path) -> Path:
    import sqlite3
    path = base / "tiny.db"
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE t (a INTEGER)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()
    return path


def test_recorder_records_incremental_evidence(tmp_path: Path) -> None:
    rec = persistence.RunRecorder(tmp_path / "cs", "run-a")
    resp = _provider_response("resp1")
    rec.record_response("p1-full", 1, 1, resp, chained=False,
                        investigation_id="inv-1")
    rec.record_assistant("p1-full", 1, -1, "COMPLETE FINAL TEXT", "resp1",
                         "completed", investigation_id="inv-1")
    rec.record_usage("p1-full", {"run": "p1-full", "ok": True,
                                 "usage": {"input_tokens": 100}},
                     investigation_id="inv-1")
    rec.record_repair("p1-full", 1, {"attempted": True, "valid": True},
                      investigation_id="inv-1")
    ok = rec.dump_sandbox_db(_make_sqlite_db(tmp_path))
    assert ok
    rec.dump_investigation(FakeSession(), "inv-1", None, None)
    rec.status = "finalized"
    manifest = rec.finalize(run="p1-full", campaign="cs", outcome={})

    assert manifest["status"] == "finalized"
    assert all(manifest["required_evidence_present"].values())
    for artifact, digest in manifest["artifacts"].items():
        artifact_path = Path(rec.dir) / artifact
        assert artifact_path.exists()
        actual = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        assert actual == digest, artifact


def test_final_assistant_message_written_verbatim_not_truncated(
        tmp_path: Path) -> None:
    rec = persistence.RunRecorder(tmp_path / "cs", "run-b")
    long_text = "X" * 2000 + "|TAIL-MARKER|"
    rec.record_assistant("p1", 1, -1, long_text, "resp1", "completed",
                         investigation_id="inv-1")
    lines = (Path(rec.dir) / "assistant_messages.jsonl").read_text(
        encoding="utf-8").strip().splitlines()
    record = json.loads(lines[0])
    assert record["text"].startswith("XXXX")
    assert record["text"].endswith("|TAIL-MARKER|")


def test_recorder_never_writes_credential_material(tmp_path: Path) -> None:
    rec = persistence.RunRecorder(tmp_path / "cs", "run-c")
    bad = "Authorization: Bearer sk-proj-abc123def456 key api_key=supersecret"
    rec.record_response("r", 1, 1, {"note": bad}, chained=False,
                        investigation_id="inv-1")
    written = (Path(rec.dir) / "responses.jsonl").read_text(encoding="utf-8")
    assert "sk-proj-" not in written
    assert "supersecret" not in written
    assert "[REDACTED]" in written


def test_finalize_reports_missing_evidence_never_invents(
        tmp_path: Path) -> None:
    rec = persistence.RunRecorder(tmp_path / "cs", "run-d")
    rec.record_response("r", 1, 1, _provider_response("resp1"),
                        chained=False, investigation_id="inv-1")
    rec.record_usage("r", {"ok": True}, investigation_id="inv-1")
    rec.record_assistant("r", 1, -1, "txt", "resp1", "completed",
                         investigation_id="inv-1")
    # NO events dump and NO sandbox copy exist yet.
    manifest = rec.finalize(run="r", campaign="cs", outcome={})
    missing = [k for k, ok in manifest["required_evidence_present"].items()
               if not ok]
    assert set(missing) == {"events_dump", "sandbox_final.db"}


def test_sandbox_deleted_only_after_verified_preservation(
        tmp_path: Path) -> None:
    rec = persistence.RunRecorder(tmp_path / "cs", "run-e")
    sandbox = tmp_path / "sandbox-dir"
    sandbox.mkdir()
    (sandbox / "sandbox.db").write_bytes(b"sqlite-placeholder")
    rec.dump_sandbox_db(sandbox / "sandbox.db")
    rec.record_response("r", 1, 1, _provider_response("resp1"),
                        chained=False, investigation_id="inv-1")
    rec.record_usage("r", {"ok": True}, investigation_id="inv-1")
    rec.record_assistant("r", 1, -1, "t", "resp1", "completed",
                         investigation_id="inv-1")
    rec.dump_sandbox_db(sandbox / "sandbox.db")  # durable final DB copy
    first = rec.finalize(run="r", campaign="cs", outcome={})
    assert not all(first["required_evidence_present"].values())
    keep = persistence.delete_dir_after_verify(
        sandbox, manifest_path=Path(rec.dir) / "run_manifest.json")
    assert keep["kept"] is True
    assert sandbox.exists()

    # After the missing events dump is added, verified deletion happens.
    rec.dump_investigation(FakeSession(), "inv", None, None)
    second = rec.finalize(run="r", campaign="cs", outcome={})
    assert all(second["required_evidence_present"].values())
    result = persistence.delete_dir_after_verify(
        sandbox, manifest_path=Path(rec.dir) / "run_manifest.json")
    assert result == {"kept": False, "reason": None}
    assert not sandbox.exists()
    # Durable evidence survives the sandbox deletion.
    assert (Path(rec.dir) / "run_manifest.json").exists()
    assert (Path(rec.dir) / "sandbox_final.db").exists()


def test_recovery_marks_crashed_run_and_preserves_verbatim(
        tmp_path: Path) -> None:
    campaign = tmp_path / "phase_d_meta_live_test"
    run_dir = campaign / "run-crashed"
    run_dir.mkdir(parents=True)
    (run_dir / "run_start.json").write_text('{"run": "run-crashed"}\n')
    (run_dir / "responses.jsonl").write_text(
        "phony evidence line A\nphony evidence line B\n")
    before = (run_dir / "responses.jsonl").read_text(encoding="utf-8")

    recovered = persistence.recover_incomplete_runs(tmp_path)

    assert recovered == [str(run_dir)]
    manifest = json.loads(
        (run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "interrupted"
    assert "nothing" in manifest["recovery_note"].lower()
    assert (run_dir / "responses.jsonl").read_text(encoding="utf-8") == before
    assert manifest["artifacts"]["responses.jsonl"] == hashlib.sha256(
        (run_dir / "responses.jsonl").read_bytes()).hexdigest()
    # Idempotent: re-running recovery does not re-mark a recovered run.
    assert persistence.recover_incomplete_runs(tmp_path) == []


def test_recovery_ignores_historical_and_stray_dirs(
        tmp_path: Path) -> None:
    campaign = tmp_path / "phase_d_meta_live_hist"
    campaign.mkdir()
    stray = campaign / "ancient_evidence_dump"
    stray.mkdir()
    (stray / "assistant_text.json").write_text("historical artifact content")
    assert persistence.recover_incomplete_runs(tmp_path) == []
    assert "# run_manifest" not in (stray / "assistant_text.json").read_text()


# ---------------------------------------------------------------------------
# Simulated live run: success path
# ---------------------------------------------------------------------------

def test_simulated_live_full_success_preserves_everything(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    args, out_path, campaign_root = _harness(monkeypatch, tmp_path, pairs=1)
    summary = json.loads(bench.run_live(args))
    report = json.loads(out_path.read_text(encoding="utf-8"))

    runs = report["runs"]
    assert [r["condition"] for r in runs] == ["full", "delta"], runs
    assert all(r.get("status") != "stopped_cap" for r in runs)
    for run in runs:
        preservation = run["preservation"]
        assert preservation["manifest"] == "finalized"
        assert all(preservation["required_evidence_present"].values())
        run_dir = Path(preservation["run_dir"])
        assert run_dir.is_dir()
        for artifact in ("responses.jsonl", "assistant_messages.jsonl",
                         "usage.jsonl", "sandbox_final.db",
                         "events_dump.json", "run_manifest.json"):
            assert (run_dir / artifact).exists(), artifact
        manifest = json.loads(
            (run_dir / "run_manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "finalized"
        assistant_records = [
            json.loads(line) for line in
            (run_dir / "assistant_messages.jsonl").read_text(
                encoding="utf-8").strip().splitlines()]
        finals = [rec for rec in assistant_records if rec["turn"] == 2]
        assert finals, assistant_records
        assert finals[-1]["text"].startswith("FINAL MESSAGE MARKER")
        assert "complete analysis" in finals[-1]["text"]
        assert finals[-1]["response_id"].startswith("resp")
    # Sandbox dirs are deleted only because preservation verified first.
    for db_path in report["sandbox_db_paths"]:
        assert not Path(db_path).exists()
        assert not Path(db_path).parent.exists()
    assert report["preservation"]["mode"] == "durable"
    assert report["crash_recovery"]["scanned"] is True
    assert report["totals"]["failed_requests"] == 0
    assert report["totals"]["billed_requests"] > 0
    assert report["totals"]["total_provider_tokens"] > 0
    assert report["totals"]["token_totals_complete"] is True
    assert report["totals"]["stop_reason"] is None
    assert summary["summary"]["billed_requests"] > 0


def test_simulated_live_full_response_payload_is_verbatim(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    args, out_path, campaign_root = _harness(monkeypatch, tmp_path, pairs=1)
    bench.run_live(args)
    campaign = next(Path(campaign_root).iterdir())
    responses = list(campaign.glob("run-*/responses.jsonl"))
    assert responses, list(campaign.iterdir())
    records = [json.loads(line)
               for line in responses[0].read_text(encoding="utf-8")
               .strip().splitlines()]
    assert records, "no provider request recorded"
    for record in records:
        response = record["response"]
        assert response["id"].startswith("resp")
        assert response["usage"]["input_tokens"] == 100
        assert response["_request_perf"]["attempts"] == 1


def test_simulated_live_no_secret_material_in_campaign(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_API_KEY", "sk-proj-very-secret-key-value")
    args, out_path, campaign_root = _harness(monkeypatch, tmp_path, pairs=1)
    bench.run_live(args)
    for path in Path(campaign_root).rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            assert b"sk-proj-very-secret-key-value" not in data, path
            assert b"MODEL_API_KEY" not in data, path


def test_simulated_live_report_structure(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    args, out_path, _cs = _harness(monkeypatch, tmp_path, pairs=1)
    bench.run_live(args)
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["protocol"]["continuation_id_correction"] is True
    assert report["sandbox_db_shared_across_runs"] is False
    # 2 turns per run, both conditions chain over previous_response_id.
    ledger = report["per_request_ledger"]
    assert len(ledger) == 4, ledger
    chained = [entry for entry in ledger if entry.get("chained")]
    assert len(chained) == 2, ledger
    assert {entry["condition"] for entry in chained} == {"full", "delta"}
    assert all(entry["turn"] == 2 for entry in chained)
    assert all(e.get("usage_missing") is not None or e.get("ok")
               for e in ledger)


# ---------------------------------------------------------------------------
# Simulated live run: mid-turn cap path (a crash-adjacent abort)
# ---------------------------------------------------------------------------

class _CapReached(Exception):
    pass


def test_simulated_live_midrun_cap_archives_interrupted_state(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class _Cap(bench._BenchmarkCapReached):
        pass

    args, out_path, campaign_root = _harness(
        monkeypatch, tmp_path, pairs=1, cap_exc=_Cap)
    bench.run_live(args)
    report = json.loads(out_path.read_text(encoding="utf-8"))
    statuses = [r.get("status") for r in report["runs"]]
    assert "stopped_cap" in statuses, statuses
    # Interrupted run dir: no finalize, but incremental evidence is present.
    campaign = next(Path(campaign_root).iterdir())
    run_dirs = list(campaign.glob("run-*"))
    assert run_dirs, list(campaign.iterdir())
    interrupted = list(campaign.glob("run-*/responses.jsonl"))
    assert interrupted, list(campaign.iterdir())
    assert all(
        (rd / "run_start.json").exists() for rd in run_dirs if rd.is_dir())
    # No sandbox deletion on the interrupted run dir: dir retained.
    db_dir = Path(report["sandbox_db_paths"][0]).parent
    assert db_dir.exists(), "sandbox must be retained on interrupted runs"
    # The harness itself wrote an explicit interrupted manifest listing the
    # partial evidence (atomic finalization works on the abort path too).
    for run_dir in run_dirs:
        manifest_path = run_dir / "run_manifest.json"
        assert manifest_path.exists(), run_dir
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["status"] == "interrupted", manifest
        assert manifest["reason"].startswith("cap reached"), manifest
        assert (run_dir / "responses.jsonl").exists(), run_dir
        assert (run_dir / "usage.jsonl").exists(), run_dir
        # A later recovery pass finds no unmarked leftovers (already marked),
        # and it would still protect a true crash case (unit-tested above).
        assert persistence.recover_incomplete_runs(campaign_root) == []


# ---------------------------------------------------------------------------
# Simulated live run: provider-side failure preservation (Phase 3 gaps)
# ---------------------------------------------------------------------------

def _run_dir_for(report: dict, condition: str) -> Path:
    for run in report["runs"]:
        if run.get("condition") == condition and "preservation" in run:
            return Path(run["preservation"]["run_dir"])
    raise AssertionError(f"no preserved run dir for {condition}: {report}")


def test_simulated_live_incomplete_first_response_preserved_not_completed(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # First provider call (full, turn 1) stops at the output limit, exactly
    # the 2026-10-29 production failure shape: status "incomplete".
    args, out_path, _ = _harness(monkeypatch, tmp_path, pairs=1)
    FakeMetaClientModule.status_queue = ["incomplete"]
    bench.run_live(args)
    report = json.loads(out_path.read_text(encoding="utf-8"))
    by_condition = {r["condition"]: r for r in report["runs"]
                    if "preservation" in r}
    full = by_condition["full"]
    assert full["run_outcome"] == "incomplete_provider_response"
    assert full["investigation_complete"] is False
    assert full["incomplete_turn1"] == 1
    # The incomplete payload itself is durable and verbatim.
    responses = [
        json.loads(line) for line in
        (_run_dir_for(report, "full") / "responses.jsonl")
        .read_text(encoding="utf-8").strip().splitlines()]
    assert any(r["response"]["status"] == "incomplete" for r in responses)
    assert any(r["response"]["id"].startswith("resp") for r in responses)
    # Preservation is complete even though the investigation is not: the
    # manifest is finalized, all required evidence present, nothing invented.
    assert all(full["preservation"]["required_evidence_present"].values())
    # The unaffected run still completes honestly.
    assert by_condition["delta"]["run_outcome"] == "completed"


def test_simulated_live_incomplete_second_response_preserved_not_completed(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Second provider call (full, turn 2) stops at the output limit.
    args, out_path, _ = _harness(monkeypatch, tmp_path, pairs=1)
    FakeMetaClientModule.status_queue = ["completed", "incomplete"]
    bench.run_live(args)
    report = json.loads(out_path.read_text(encoding="utf-8"))
    by_condition = {r["condition"]: r for r in report["runs"]
                    if "preservation" in r}
    full = by_condition["full"]
    assert full["run_outcome"] == "incomplete_provider_response"
    assert full["investigation_complete"] is False
    assert full["incomplete_turn2"] == 1
    responses = [
        json.loads(line) for line in
        (_run_dir_for(report, "full") / "responses.jsonl")
        .read_text(encoding="utf-8").strip().splitlines()]
    chained = [r for r in responses if r["chained"]]
    assert chained and all(
        r["response"]["status"] == "incomplete" for r in chained)
    assert all(full["preservation"]["required_evidence_present"].values())
    assert by_condition["delta"]["run_outcome"] == "completed"


def test_simulated_live_malformed_summary_preserved_not_accepted(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    args, out_path, _ = _harness(monkeypatch, tmp_path, pairs=1)
    FakeMetaLoop.summary_valid = False
    bench.run_live(args)
    report = json.loads(out_path.read_text(encoding="utf-8"))
    by_condition = {r["condition"]: r for r in report["runs"]
                    if "preservation" in r}
    for condition in ("full", "delta"):
        run = by_condition[condition]
        assert run["run_outcome"] == "invalid_summary", run
        assert run["investigation_complete"] is False
        assert run["summary_valid"] is False
        assert run["summary_errors"], run
        # The malformed final text is preserved verbatim, not discarded and
        # not upgraded into a valid result.
        assistant = [
            json.loads(line) for line in
            (_run_dir_for(report, condition) / "assistant_messages.jsonl")
            .read_text(encoding="utf-8").strip().splitlines()]
        assert any("without any summary block" in rec["text"]
                   for rec in assistant), assistant
        assert all(run["preservation"]["required_evidence_present"].values())


def test_simulated_live_missing_usage_recorded_honestly(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Provider responses with no usage block: recorded as missing, never
    # invented, and totals stay at zero instead of being fabricated.
    args, out_path, _ = _harness(monkeypatch, tmp_path, pairs=1)
    FakeMetaClientModule.usage_override = {}
    bench.run_live(args)
    report = json.loads(out_path.read_text(encoding="utf-8"))
    ledger = report["per_request_ledger"]
    assert ledger, report
    assert all(entry.get("usage_missing") is True for entry in ledger)
    for entry in ledger:
        assert entry.get("usage") is None, entry
    assert report["totals"]["total_provider_tokens"] == 0
    assert report["totals"]["token_totals_complete"] is False
    # The honest usage rows are still durable per run.
    for condition in ("full", "delta"):
        usage_rows = [
            json.loads(line) for line in
            (_run_dir_for(report, condition) / "usage.jsonl")
            .read_text(encoding="utf-8").strip().splitlines()]
        assert usage_rows, condition
        assert all(row.get("usage_missing") is True for row in usage_rows)


def test_simulated_live_commit_failure_preserves_partial_and_marks_interrupted(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # A database commit failure mid-run: the evidence already on disk
    # survives, the run is marked interrupted with an explicit reason, the
    # volatile sandbox is kept, and nothing is silently lost or invented.
    args, out_path, campaign_root = _harness(monkeypatch, tmp_path, pairs=1)
    real_new = bench._new_sandbox_session
    state = {"commits": 0}

    def failing_new():
        session, run_engine, run_dir = real_new()
        session_cls = type(session)
        orig_commit = session_cls.commit

        def commit(self):
            state["commits"] += 1
            if state["commits"] == 2:
                raise RuntimeError("simulated database commit failure")
            return orig_commit(self)

        monkeypatch.setattr(session_cls, "commit", commit)
        return session, run_engine, run_dir

    monkeypatch.setattr(bench, "_new_sandbox_session", failing_new)
    bench.run_live(args)  # must not raise: failure is recorded, not silent
    report = json.loads(out_path.read_text(encoding="utf-8"))
    failed = [r for r in report["runs"]
              if str(r.get("status", "")).startswith("failed:")]
    assert failed, report["runs"]
    assert "commit" in failed[0]["status"], failed[0]
    preservation = failed[0]["preservation"]
    assert preservation["status"] == "interrupted", preservation
    assert "commit" in (preservation["reason"] or ""), preservation
    # The interrupted manifest lives in the run's durable directory; find
    # it by its explicit interrupted status (the failure manifest carries no
    # run_dir pointer by design — only finalized quality records do).
    run_dir = None
    for candidate in Path(campaign_root).glob("*/*/run_manifest.json"):
        manifest = json.loads(candidate.read_text(encoding="utf-8"))
        if (manifest.get("status") == "interrupted"
                and "commit" in (manifest.get("reason") or "")):
            run_dir = candidate.parent
    assert run_dir is not None, "interrupted run dir must exist"
    # Partial evidence from before the failure is on disk, verbatim.
    responses = [
        json.loads(line) for line in
        (run_dir / "responses.jsonl").read_text(
            encoding="utf-8").strip().splitlines()]
    assert responses, "turn-1 evidence must survive the commit failure"
    assert all(r["response"]["id"].startswith("resp") for r in responses)
    # Missing post-failure evidence is reported, never invented ...
    missing = [k for k, ok in
               preservation["required_evidence_present"].items() if not ok]
    assert missing, preservation
    # ... the volatile sandbox is kept for forensics ...
    sandbox_parent = Path(report["sandbox_db_paths"][0]).parent
    assert sandbox_parent.exists(), "sandbox must be kept, not deleted"
    # ... and a later recovery scan finds no unmarked leftovers.
    assert persistence.recover_incomplete_runs(campaign_root) == []


def test_dump_failure_reports_missing_evidence_and_keeps_sandbox(
        tmp_path: Path) -> None:
    # A failed sandbox-DB copy (snapshot creation failure) is reported as
    # missing evidence; the cleanup guard then refuses to delete anything.
    rec = persistence.RunRecorder(tmp_path / "cs", "run-dumpfail")
    assert rec.dump_sandbox_db(
        tmp_path / "does-not-exist" / "sandbox.db") is False
    rec.record_response("r", 1, 1, _provider_response("resp1"),
                        chained=False, investigation_id="inv-1")
    rec.record_usage("r", {"ok": True}, investigation_id="inv-1")
    rec.record_assistant("r", 1, -1, "t", "resp1", "completed",
                         investigation_id="inv-1")
    manifest = rec.finalize(run="r", campaign="cs", outcome={})
    assert manifest["required_evidence_present"]["sandbox_final.db"] is False
    sandbox = tmp_path / "sandbox-dir"
    sandbox.mkdir()
    keep = persistence.delete_dir_after_verify(
        sandbox, manifest_path=Path(rec.dir) / "run_manifest.json")
    assert keep["kept"] is True
    assert sandbox.exists()


# ---------------------------------------------------------------------------
# Phase 2 regression tests for audit RC1-RC6 + R2/R5/R6 linkage & guard gaps
# ---------------------------------------------------------------------------

def _full_evidence(rec, inv_id: str = "inv-1") -> None:
    """Record a complete evidence set: response + assistant + usage +
    events dump + sandbox DB copy (no repair, no finalize)."""
    import sqlite3
    rec.record_response("r", 1, 1, _provider_response("resp1"),
                        chained=False, investigation_id=inv_id)
    rec.record_assistant("r", 1, -1, "complete final text", "resp1",
                         "completed", investigation_id=inv_id)
    rec.record_usage("r", {"run": "r", "ok": True,
                           "response_id": "resp1",
                           "usage": {"input_tokens": 100}},
                     investigation_id=inv_id)
    rec.dump_investigation(FakeSession(), inv_id, None, None)
    src = rec.dir.parent / f"sandbox-{rec.run_id}.db"
    if src.exists():
        src.unlink()
    conn = sqlite3.connect(str(src))
    conn.execute("CREATE TABLE t (a INTEGER)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()
    assert rec.dump_sandbox_db(src) is True


def test_rc2_rc3_rows_carry_investigation_turn_round_and_response_id(
        tmp_path: Path) -> None:
    # RC2/RC3 + req 2: every row links investigation/turn/round; assistant
    # and usage rows link the provider response id; raw payloads survive
    # verbatim (only secret-shaped values redacted).
    rec = persistence.RunRecorder(tmp_path / "cs", "run-link")
    payload = _provider_response("resp-link")
    rec.record_response("p1-full", 2, 3, payload, chained=True,
                        investigation_id="inv-9")
    rec.record_assistant("p1-full", 2, -1, "text", "resp-link",
                         "completed", investigation_id="inv-9")
    rec.record_usage("p1-full", {"response_id": "resp-link", "ok": True},
                     investigation_id="inv-9")
    rec.record_repair("p1-full", 2, {"repair_text": "fixed"},
                      investigation_id="inv-9")
    rows = (Path(rec.dir) / "responses.jsonl").read_text(
        encoding="utf-8").strip().splitlines()
    stored = json.loads(rows[0])
    assert stored["investigation_id"] == "inv-9"
    assert (stored["turn"], stored["round"]) == (2, 3)
    assert stored["response"] == payload
    assist = json.loads((Path(rec.dir) / "assistant_messages.jsonl")
                         .read_text(encoding="utf-8").strip().splitlines()[0])
    assert (assist["investigation_id"], assist["turn"], assist["round"],
            assist["response_id"]) == ("inv-9", 2, -1, "resp-link")
    usage = json.loads((Path(rec.dir) / "usage.jsonl").read_text(
        encoding="utf-8").strip().splitlines()[0])
    assert (usage["investigation_id"], usage["response_id"]) == (
        "inv-9", "resp-link")
    repair = json.loads((Path(rec.dir) / "repairs.jsonl").read_text(
        encoding="utf-8").strip().splitlines()[0])
    assert (repair["investigation_id"], repair["turn"]) == ("inv-9", 2)


def test_rc3_raw_payload_preserved_verbatim(tmp_path: Path) -> None:
    # RC3: the complete provider payload (output blocks, usage, perf) is
    # durable verbatim, not a summary or a truncated head.
    rec = persistence.RunRecorder(tmp_path / "cs", "run-raw")
    payload = _provider_response("resp-raw")
    payload["output"].append({"type": "extra", "blob": "x" * 5000})
    rec.record_response("r", 1, 1, payload, chained=False,
                        investigation_id="inv-1")
    stored = json.loads((Path(rec.dir) / "responses.jsonl").read_text(
        encoding="utf-8").strip().splitlines()[0])["response"]
    assert stored == payload
    assert stored["usage"]["input_tokens"] == 100
    assert stored["output"][-1]["blob"] == "x" * 5000


def test_rc3_redaction_covers_headers_and_metadata(tmp_path: Path) -> None:
    # Req 3: credential/secret-shaped request metadata is redacted; the
    # surrounding record structure survives.
    rec = persistence.RunRecorder(tmp_path / "cs", "run-redact")
    rec.record_response("r", 1, 1, {
        "id": "resp1",
        "request_headers": {
            "Authorization": "Bearer sk-proj-abc123",
            "Content-Type": "application/json"},
        "params": {"api_key": "gsk_supersecret", "model": "m"},
        "note": "token sk-proj-xyz in prose"},
        chained=False, investigation_id="inv-1")
    written = (Path(rec.dir) / "responses.jsonl").read_text(encoding="utf-8")
    assert "sk-proj-abc123" not in written
    assert "gsk_supersecret" not in written
    assert "sk-proj-xyz" not in written
    assert "[REDACTED]" in written
    stored = json.loads(written.strip().splitlines()[0])["response"]
    assert stored["request_headers"]["Content-Type"] == "application/json"
    assert stored["params"]["model"] == "m"
    assert stored["id"] == "resp1"


def test_rc5_repair_attempted_requires_repairs_artifact(
        tmp_path: Path) -> None:
    # Req 5: repairs.jsonl is required when a repair was attempted (and
    # only then); late-arriving repairs promote incomplete -> finalized.
    rec = persistence.RunRecorder(tmp_path / "cs", "run-rep")
    _full_evidence(rec)
    manifest = rec.finalize(run="r", campaign="cs",
                            outcome={"repair_attempted": True})
    assert manifest["required_evidence_present"]["repairs"] is False
    assert manifest["status"] == "incomplete_preservation"
    rec.record_repair("r", 2, {"repair_text": "fixed"},
                      investigation_id="inv-1")
    manifest2 = rec.finalize(run="r", campaign="cs",
                             outcome={"repair_attempted": True})
    assert manifest2["required_evidence_present"]["repairs"] is True
    assert manifest2["status"] == "finalized"
    # A run with no repair attempt never requires repairs.jsonl.
    rec2 = persistence.RunRecorder(tmp_path / "cs", "run-norep")
    _full_evidence(rec2)
    manifest3 = rec2.finalize(run="r", campaign="cs", outcome={})
    assert "repairs" not in manifest3["required_evidence_present"]
    assert manifest3["status"] == "finalized"


def test_rc5_hash_mismatch_blocks_sandbox_deletion(tmp_path: Path) -> None:
    # Req 5: presence is not preservation; bytes that changed after
    # finalize keep the sandbox alive with an explicit reason.
    rec = persistence.RunRecorder(tmp_path / "cs", "run-hash")
    _full_evidence(rec)
    manifest = rec.finalize(run="r", campaign="cs", outcome={})
    assert manifest["status"] == "finalized"
    sandbox = tmp_path / "sandbox-dir"
    sandbox.mkdir()
    with open(Path(rec.dir) / "responses.jsonl", "a",
               encoding="utf-8") as fh:
        fh.write("CORRUPTION")
    keep = persistence.delete_dir_after_verify(
        sandbox, manifest_path=Path(rec.dir) / "run_manifest.json")
    assert keep["kept"] is True
    assert "hash mismatch" in keep["reason"]
    assert sandbox.exists()


def test_rc7_no_silent_overwrite_of_existing_run(tmp_path: Path) -> None:
    # Req 7: constructing a recorder over an existing run dir raises
    # instead of silently overwriting; existing bytes are untouched.
    rec = persistence.RunRecorder(tmp_path / "cs", "run-once")
    rec.record_response("r", 1, 1, _provider_response("resp1"),
                        chained=False, investigation_id="inv-1")
    before = (Path(rec.dir) / "responses.jsonl").read_bytes()
    with pytest.raises(RuntimeError):
        persistence.RunRecorder(tmp_path / "cs", "run-once")
    assert (Path(rec.dir) / "responses.jsonl").read_bytes() == before


def test_rc6_interrupted_status_never_overwritten(tmp_path: Path) -> None:
    # Req 6: an explicit interrupted run keeps that status even when all
    # evidence later arrives; incomplete_preservation still promotes.
    rec = persistence.RunRecorder(tmp_path / "cs", "run-int")
    _full_evidence(rec)
    rec.status = "interrupted"
    manifest = rec.finalize(run="r", campaign="cs",
                            outcome={}, reason="cap reached")
    assert manifest["status"] == "interrupted"
    assert all(manifest["required_evidence_present"].values())


def test_rc1_rc4_snapshot_independent_of_later_source_mutation(
        tmp_path: Path) -> None:
    # RC1/RC4: the durable sandbox copy is a snapshot, not a reference;
    # later source-DB writes never leak into preserved evidence.
    import sqlite3
    rec = persistence.RunRecorder(tmp_path / "cs", "run-snap")
    src = tmp_path / "sandbox.db"
    conn = sqlite3.connect(str(src))
    conn.execute("CREATE TABLE t (a INTEGER)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()
    assert rec.dump_sandbox_db(src) is True
    conn = sqlite3.connect(str(src))
    conn.execute("INSERT INTO t VALUES (2)")
    conn.commit()
    conn.close()
    dst = sqlite3.connect(str(Path(rec.dir) / "sandbox_final.db"))
    assert [r[0] for r in dst.execute("SELECT a FROM t").fetchall()] == [1]
    dst.close()
    assert [r[0] for r in sqlite3.connect(str(src)).execute(
        "SELECT a FROM t").fetchall()] == [1, 2]


def test_rc6_recovery_covers_groq_prefix_and_never_deletes(
        tmp_path: Path) -> None:
    # Req 6: crash recovery covers both live harnesses and only ADDS a
    # manifest; dirs that already finalized are untouched.
    for campaign_name in ("phase_d_meta_live_x", "phase_d_groq_live_x"):
        run_dir = tmp_path / campaign_name / "run-leftover"
        run_dir.mkdir(parents=True)
        (run_dir / "run_start.json").write_text('{"run": "x"}\n')
        (run_dir / "responses.jsonl").write_text('{"a": 1}\n')
    done_dir = tmp_path / "phase_d_meta_live_x" / "run-done"
    done_dir.mkdir(parents=True)
    (done_dir / "run_manifest.json").write_text('{"status": "finalized"}')
    recovered = persistence.recover_incomplete_runs(tmp_path)
    assert len(recovered) == 2
    for campaign_name in ("phase_d_meta_live_x", "phase_d_groq_live_x"):
        manifest = json.loads(
            (tmp_path / campaign_name / "run-leftover" / "run_manifest.json")
            .read_text(encoding="utf-8"))
        assert manifest["status"] == "interrupted"
    assert json.loads((done_dir / "run_manifest.json").read_text(
        encoding="utf-8"))["status"] == "finalized"


def test_rc1_subprocess_termination_leaves_recoverable_evidence(
        tmp_path: Path) -> None:
    # RC1/RC6: a hard kill mid-run (no finalize, no cleanup) leaves
    # incremental evidence that recovery marks interrupted, verbatim.
    import os
    import subprocess
    import sys
    project_root = Path(persistence.__file__).resolve().parents[2]
    campaign = tmp_path / "phase_d_meta_live_kill"
    script = (
        "from model_autopsy.benchmarks import bench_persistence as p;"
        "from pathlib import Path;"
        "import sys,os;"
        "rec=p.RunRecorder(Path(sys.argv[1]),sys.argv[2]);"
        "rec.record_response('r',1,1,{'id':'resp-k','text':'x'*100},"
        "chained=False,investigation_id='inv-k');"
        "rec.record_usage('r',{'response_id':'resp-k'},"
        "investigation_id='inv-k');"
        "os._exit(137)")
    proc = subprocess.run(
        [sys.executable, "-c", script, str(campaign), "run-killed"],
        cwd=str(project_root), capture_output=True, text=True, timeout=60)
    assert proc.returncode != 0
    run_dir = campaign / "run-killed"
    assert (run_dir / "responses.jsonl").exists()
    assert not (run_dir / "run_manifest.json").exists()
    before = (run_dir / "responses.jsonl").read_bytes()
    recovered = persistence.recover_incomplete_runs(tmp_path)
    assert recovered == [str(run_dir)]
    manifest = json.loads((run_dir / "run_manifest.json").read_text(
        encoding="utf-8"))
    assert manifest["status"] == "interrupted"
    assert (run_dir / "responses.jsonl").read_bytes() == before
    assert "resp-k" in before.decode("utf-8")


def test_simulated_live_usage_rows_link_provider_response_ids(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Req 2 end to end: every durable usage row from a live (simulated)
    # run carries the provider response id and investigation id, and each
    # id matches a row in responses.jsonl.
    args, out_path, campaign_root = _harness(monkeypatch, tmp_path, pairs=1)
    bench.run_live(args)
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["runs"], "expected simulated runs"
    for run in report["runs"]:
        run_dir = Path(run["preservation"]["run_dir"])
        resp_ids = {json.loads(line)["response"]["id"]
                    for line in (run_dir / "responses.jsonl").read_text(
                        encoding="utf-8").strip().splitlines()}
        assert resp_ids, run
        for line in (run_dir / "usage.jsonl").read_text(
                encoding="utf-8").strip().splitlines():
            usage = json.loads(line)
            assert usage["investigation_id"], run
            assert usage.get("response_id") in resp_ids, (run, usage)
        for line in (run_dir / "assistant_messages.jsonl").read_text(
                encoding="utf-8").strip().splitlines():
            assist = json.loads(line)
            assert assist["investigation_id"], run
            if assist["turn"] in (1, 2):
                assert assist["response_id"] in resp_ids, (run, assist)
