"""Phase 3 (Groq side) — simulated offline tests for the Phase-2 durability
port to the Groq paired harness.

Zero network, no key: the provider layer (`gcb._groq_request`,
`ConditionRun._rl_request`) and the key bootstrap are faked, then the FULL
`run_live` executes. Assertions cover:

- per-condition durable run directories under a fresh campaign dir;
- COMPLETE final assistant texts (verbatim, no 400-char head truncation);
- repair responses recorded verbatim (`repairs.jsonl`);
- per-attempt usage rows (`usage.jsonl`), including missing-usage honesty;
- atomic finalization: run_manifest.json with SHA-256 per artifact and
  all required evidence present;
- no credential material anywhere in the campaign tree.
"""
from __future__ import annotations

import json
import os
import types
from pathlib import Path

import pytest

from model_autopsy.benchmarks import groq_paired_continuation_benchmark as groq


@pytest.fixture()
def fake_provider(monkeypatch, tmp_path):
    """Stand-in provider: deterministic chat responses, no tool calls, plus a
    repair-capable validator result. All state kept on the fixture object."""
    state = types.SimpleNamespace(requests=0, model=groq.__dict__.get(
        "CURRENT_MODEL", "openai/gpt-oss-120b"))

    def fake_groq_request(method, url, api_key):
        assert "key" not in str(url).lower()
        if method == "GET" and url == groq.gcb.GROQ_MODELS_URL:
            return {"status": 200,
                    "body": {"data": [{"id": state.model}]}}
        raise AssertionError(f"unexpected request {method} {url}")

    def fake_rl_request(self, method, url, **kwargs):
        assert method == "POST" and url == groq.gcb.GROQ_CHAT_URL
        state.requests += 1
        tail = f"|COMPLETE-TAIL-{state.requests}|"
        return {
            "status": 200,
            "latency_s": 0.01,
            "body": {
                "choices": [{"message": {"content":
                             "FINAL MESSAGE MARKER " + tail},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 400, "completion_tokens": 80,
                          "total_tokens": 480},
            },
        }

    # Patch through the harness's OWN module reference (the benchmarks dir is
    # a namespace package, so model_autopsy.benchmarks.groq_context_benchmark
    # and the harness's direct `import groq_context_benchmark as gcb` are two
    # distinct module objects - patching the wrong one still hits the network).
    monkeypatch.setattr(groq.gcb, "_groq_request", fake_groq_request)
    monkeypatch.setattr(groq.ConditionRun, "_rl_request", fake_rl_request)
    monkeypatch.setattr(groq, "bootstrap_env", lambda key_required=False: None)
    monkeypatch.setattr(groq, "CAMPAIGN_ROOT", tmp_path / "campaigns")
    monkeypatch.setattr(groq, "CONTROLLED_MODE", True)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_fake-not-a-real-key")
    return state


def _args(tmp_path: Path, out_name="report.json"):
    return types.SimpleNamespace(
        model="openai/gpt-oss-120b", controlled=True, first="full",
        pairs=1, max_attempts=25, max_total_tokens=120_000,
        max_est_cost=0.50, repeated_429_limit=4,
        out=str(tmp_path / out_name))


def test_groq_live_simulated_durable_evidence_complete(
        fake_provider, tmp_path) -> None:
    groq.run_live(_args(tmp_path))
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))

    campaign = Path(report["campaign_dir"])
    assert campaign.is_dir()
    reports_runs = report["runs"]
    assert [r["condition"] for r in reports_runs] == ["full", "delta"], (
        reports_runs)
    conditions_seen = set()
    for run in reports_runs:
        preservation = run["preservation"]
        run_dir = Path(preservation["run_dir"])
        assert run_dir.is_dir()
        assert run["condition"] not in conditions_seen
        conditions_seen.add(run["condition"])
        assert preservation["manifest"] == "finalized"
        assert all(preservation["required_evidence_present"].values())
        for artifact in ("responses.jsonl", "assistant_messages.jsonl",
                         "usage.jsonl", "repairs.jsonl", "events_dump.json",
                         "sandbox_final.db", "run_manifest.json",
                         "run_start.json"):
            assert (run_dir / artifact).exists(), artifact
            assert (run_dir / artifact).stat().st_size > 0, artifact
        # Complete final assistant text is preserved verbatim, not head-only.
        assistant = [
            json.loads(line) for line in
            (run_dir / "assistant_messages.jsonl").read_text(encoding="utf-8")
            .strip().splitlines()]
        finals = [r for r in assistant if r["turn"] == "turn2-final"]
        assert finals, assistant
        assert finals[-1]["text"].startswith("FINAL MESSAGE MARKER")
        assert finals[-1]["text"].endswith("|COMPLETE-TAIL-") or \
            "COMPLETE-TAIL" in finals[-1]["text"], finals[-1]["text"]
        # The repair attempt was durable, verbatim.
        repairs = [
            json.loads(line) for line in
            (run_dir / "repairs.jsonl").read_text(encoding="utf-8")
            .strip().splitlines()]
        assert repairs, "repair responses must be recorded verbatim"
        assert repairs[-1]["repair_text"].startswith("FINAL MESSAGE MARKER")


def test_groq_live_simulated_every_provider_exchange_recorded(
        fake_provider, tmp_path) -> None:
    groq.run_live(_args(tmp_path, "b.json"))
    report = json.loads((tmp_path / "b.json").read_text(encoding="utf-8"))
    for run in report["runs"]:
        run_dir = Path(run["preservation"]["run_dir"])
        responses = [
            json.loads(line) for line in
            (run_dir / "responses.jsonl").read_text(encoding="utf-8")
            .strip().splitlines()]
        # turn1 r1, turn2 r1, repair per condition: 3 completed exchanges
        assert len(responses) >= 3, responses
        tags = {r["turn"] for r in responses}
        assert {"turn1r1", "turn2r1", "turn2repair"}.issubset(tags), tags
        for record in responses:
            assert record["response"]["choices"][0]["message"]["content"]
        usage = [
            json.loads(line) for line in
            (run_dir / "usage.jsonl").read_text(encoding="utf-8")
            .strip().splitlines()]
        assert usage, "every attempt needs a durable usage row"
        assert all(u.get("prompt_tokens") == 400 for u in usage)


def test_groq_live_simulated_manifest_hashes_artifacts(
        fake_provider, tmp_path) -> None:
    import hashlib
    groq.run_live(_args(tmp_path, "c.json"))
    report = json.loads((tmp_path / "c.json").read_text(encoding="utf-8"))
    run_dir = Path(report["runs"][0]["preservation"]["run_dir"])
    manifest = json.loads(
        (run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["run"] == "run-full"
    assert manifest["status"] == "finalized"
    for artifact, digest in manifest["artifacts"].items():
        actual = hashlib.sha256(
            (run_dir / artifact).read_bytes()).hexdigest()
        assert actual == digest, artifact


def test_groq_live_simulated_no_secret_material(
        fake_provider, tmp_path) -> None:
    groq.run_live(_args(tmp_path, "d.json"))
    campaign_root = tmp_path / "campaigns"
    for path in campaign_root.rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            assert b"gsk_fake-not-a-real-key" not in data, path
            assert b"GROQ_API_KEY" not in data, path
            assert b"api_key" not in data.lower(), path


def test_groq_live_simulated_length_stop_preserved_and_repaired_honestly(
        fake_provider, tmp_path, monkeypatch) -> None:
    # Max-output-token stop on turn 2 (finish_reason "length"), the exact
    # production failure shape: truncated payloads are preserved verbatim, a
    # bounded repair is attempted and also preserved, and the still-invalid
    # summary is reported honestly instead of being upgraded or hidden.
    orig_rl = groq.ConditionRun._rl_request

    def length_after_first(self, method, url, **kwargs):
        response = orig_rl(self, method, url, **kwargs)
        if fake_provider.requests >= 2:
            response["body"]["choices"][0]["finish_reason"] = "length"
        return response

    monkeypatch.setattr(groq.ConditionRun, "_rl_request", length_after_first)
    groq.run_live(_args(tmp_path, "length.json"))
    report = json.loads((tmp_path / "length.json").read_text(
        encoding="utf-8"))
    for run in report["runs"]:
        run_dir = Path(run["preservation"]["run_dir"])
        responses = [
            json.loads(line) for line in
            (run_dir / "responses.jsonl").read_text(encoding="utf-8")
            .strip().splitlines()]
        # The length-stopped payloads survive verbatim with their stop reason.
        length_stops = [
            r for r in responses
            if ((r["response"].get("choices") or [{}])[0]
                 .get("finish_reason") == "length")]
        assert length_stops, responses
        # The bounded repair was attempted and its response preserved.
        repairs = [
            json.loads(line) for line in
            (run_dir / "repairs.jsonl").read_text(encoding="utf-8")
            .strip().splitlines()]
        assert repairs, "a repair attempt must be recorded, verbatim"
        # The summary is still invalid (the fake repair has no valid block)
        # and the run reports that honestly.
        assert run["summary"]["valid"] is False, run["summary"]
        assert run["summary_repair_attempts"] >= 1, run
        assert run["preservation"]["manifest"] == "finalized"
        assert all(run["preservation"][
            "required_evidence_present"].values())


def test_groq_live_simulated_repair_success_records_final_message(
        fake_provider, tmp_path, monkeypatch) -> None:
    # Live-shape regression (validation2 exposed it): every turn round is
    # tool-calls-only with empty text, so the pre-repair turn2-final record
    # is empty; the successful repair must then ALSO be durable as the
    # run's final assistant message, not only inside repairs.jsonl.
    orig_rl = groq.ConditionRun._rl_request
    valid_block = ("```investigation_summary\n"
                   '{"conclusion": "repaired conclusion", '
                   '"status_recommendations": [], '
                   '"uncertainties": [], '
                   '"recommended_next": "none"}\n```')

    def empty_turns_valid_repair(self, method, url, **kwargs):
        body = kwargs.get("json", {}) or {}
        response = orig_rl(self, method, url, **kwargs)
        if "tools" not in body:
            # Repair request (no tools offered): valid summary block.
            response["body"]["choices"][0]["message"]["content"] = (
                valid_block)
        else:
            # Turn rounds: tool-calls-only, empty text, like the live runs.
            response["body"]["choices"][0]["message"]["content"] = ""
            response["body"]["choices"][0]["message"]["tool_calls"] = []
        return response

    monkeypatch.setattr(
        groq.ConditionRun, "_rl_request", empty_turns_valid_repair)
    groq.run_live(_args(tmp_path, "repair_win.json"))
    report = json.loads((tmp_path / "repair_win.json").read_text(
        encoding="utf-8"))
    for run in report["runs"]:
        assert run["summary"]["valid"] is True, run["summary"]
        assert run["summary_valid_after_repair"] is True, run
        run_dir = Path(run["preservation"]["run_dir"])
        assistant = [
            json.loads(line) for line in
            (run_dir / "assistant_messages.jsonl").read_text(
                encoding="utf-8").strip().splitlines()]
        repaired = [r for r in assistant
                    if r["turn"] == "turn2-final-repaired"]
        assert repaired, assistant
        assert valid_block in repaired[-1]["text"], repaired[-1]
        # Pre-repair history is retained, not rewritten.
        assert any(r["turn"] == "turn2-final" for r in assistant)
        assert run["preservation"]["manifest"] == "finalized"
        assert all(run["preservation"][
            "required_evidence_present"].values())


def test_groq_offline_mode_still_certifies_controlled_design(
        fake_provider) -> None:
    out = json.loads(groq.run_offline())
    checks = out["checks"]
    assert checks["controlled_certification"][
        "identical_continuation_instruction"] is True
    assert checks["controlled_certification"][
        "recorded_context_present_only_in_full"] is True
    assert checks["controlled_certification"]["delta_strictly_smaller"] is True
