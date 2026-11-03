"""Meta paired continuation benchmark (Phase D) — Model Autopsy.

Measures whether the Phase C continuation-delta change reduces ACTUAL billed
input tokens, cost, and latency on the live Meta Model API (api.meta.ai/v1,
Muse Spark) without weakening investigation quality — as a strictly capped
paired measurement:

  Condition "full":   BASELINE. Pre-Phase-C behavior: continuation turns resend
                      the FULL initial context. Constructed without changing any
                      production code: the harness patches
                      `meta_loop._continuation_delta_items` in-process so
                      continuation turns send `_initial_context_items`.
                      NOTE: the loop's own usage_rollup will still label these
                      turns context_mode "delta"; the harness condition tag is
                      the authoritative label in this report.
  Condition "delta":  CANDIDATE. Production code as-is (Phase C): continuation
                      turns send only the fresh state delta, with the existing
                      one-shot full-context fallback on chain-state failures.

Identical on both sides: model, objective, artifact, tool definitions,
instructions, temperature (0.2, production default), round limit (3), tool
budget (max_tool_calls=6), turn structure (1 fresh turn + 1 chained turn).

PROTOCOL REVISION v2 (2026-10-29, frozen)
  Frozen copy: benchmarks/phase_d_meta_protocol_revision_v2_2026-10-29.md;
  narrative record: benchmarks/RESULTS.md (same date).
  The continuation-ID defect in the summary-repair flow is corrected: after a
  repair produces a VALID summary, `run_meta_turn` returns the repaired
  response's id, so turn 2 chains from the repaired state instead of the
  response that carried the invalid summary. Without a repair (or after a
  repair that did not win) the original id is returned unchanged; if a repair
  wins but the provider supplies no usable id, no continuation id is returned
  and the turn's `continuation_state.response_id_source` says "unavailable".
  The benchmark records that audit per turn (`turn{1,2}_continuation_state`)
  and the existing latest-id checks verify the chain actually used it. Both
  conditions run the same corrected code, so the Full-vs-Delta payload
  difference (full re-sends the initial context; delta sends the state delta)
  is unchanged.

ISOLATION AND SAFETY
  - Sandbox SQLite DB via MODEL_AUTOPSY_DB_PATH (never the live app DB).
  - MODEL_API_KEY is read from the existing environment configuration (process
    env first, then model_autopsy/.env silently). The key value is NEVER
    printed, logged, written, or stored anywhere by this script.
  - Hard caps, checked before and after every provider request: total request
    ATTEMPTS (retries and fallbacks included), total provider-reported tokens,
    and an ESTIMATED cost ceiling from published pricing. The client's retry
    loop is capped to the attempts remaining, so a single in-flight call
    cannot push the total past the attempt ceiling. The run aborts when a
    ceiling is hit, or after repeated provider 429s.
  - Provider response status is recorded per request. `status: incomplete`
    and other non-completed statuses are flagged distinctly; they can never
    produce a run outcome of `completed`.
  - Failed/rejected attempts are recorded separately from successful billed
    requests; their retry count is derived from the adapter's "(after N
    attempts)" hint when present. Missing usage fields are reported as
    missing, never invented.

ACCURACY RULES
  - Token numbers are exactly what the provider reports per request.
  - Cost figures are ESTIMATES from the pricing source named in the output;
    never claimed to be actual charges.
  - Small sample: no statistical significance is ever claimed.

Modes:
  --offline   Build both condition payloads for the same investigation, verify
              the baseline patch reproduces the full-context payload
              byte-for-byte, and report sizes. Zero network, no key needed.
  (default)   Live paired measurement, strictly capped.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BENCH_DIR.parent.parent          # model_autopsy -> repo root
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the persistence layer whether this file is run as a script (cwd =
# benchmarks/) or imported as a package module under tests (no __init__.py,
# so an explicit path insert is required).
if str(BENCH_DIR) not in sys.path:
    sys.path.insert(0, str(BENCH_DIR))
try:
    from bench_persistence import (RunRecorder, delete_dir_after_verify,
                                   recover_incomplete_runs)
except ModuleNotFoundError:  # pragma: no cover - package import form
    from model_autopsy.benchmarks.bench_persistence import (
        RunRecorder, delete_dir_after_verify, recover_incomplete_runs)

# Published Standard-mode pricing, per 1M tokens
# (https://dev.meta.ai/docs/pricing-rate-limits, muse-spark-1.3 Standard).
SPARK_PRICING_USD_PER_M = {
    "cached_input": 0.15, "input": 1.25, "output": 4.25,
    "source": "https://dev.meta.ai/docs/pricing-rate-limits "
              "(muse-spark-1.3 Standard mode; estimates only)"}

OBJECTIVE = "Why does the model underperform on out-of-fold data?"
RUN_CFG = {"max_tool_calls": 6}
TURN_ROUNDS = 3
TURNS_PER_RUN = 2
# Campaign output root. Tests point this at a temp dir; live runs use the
# benchmarks directory. Never overwritten hard: each new campaign gets a
# fresh timestamped directory, and an existing one aborts the run.
CAMPAIGN_ROOT = BENCH_DIR
PRE_REGISTERED_LIMITS = {
    "pairs": 2,
    "max_attempts": 40,
    "max_total_tokens": 150_000,
    "max_est_cost": 1.0,
    "repeated_429_limit": 3,
}


def _validate_caps(args) -> None:
    """Refuse any request to raise the pre-registered spending ceilings."""
    checks = (
        ("pairs", args.pairs, 1, PRE_REGISTERED_LIMITS["pairs"]),
        ("max_attempts", args.max_attempts, 1,
         PRE_REGISTERED_LIMITS["max_attempts"]),
        ("max_total_tokens", args.max_total_tokens, 1,
         PRE_REGISTERED_LIMITS["max_total_tokens"]),
        ("max_est_cost", args.max_est_cost, 0.000001,
         PRE_REGISTERED_LIMITS["max_est_cost"]),
        ("repeated_429_limit", args.repeated_429_limit, 1,
         PRE_REGISTERED_LIMITS["repeated_429_limit"]),
    )
    for name, value, lower, upper in checks:
        if not (lower <= value <= upper):
            sys.exit(
                f"BLOCKED: {name}={value} is outside the pre-registered "
                f"range [{lower}, {upper}]. No request was made.")


# ---------------------------------------------------------------------------
# Environment bootstrap (silent — never echoes values), BEFORE backend imports
# ---------------------------------------------------------------------------

def _load_env_file(env_file: Path) -> bool:
    """Load a simple KEY=VALUE .env file without echoing any values.

    Handles a UTF-8 BOM, optional `export ` prefixes, and matching quotes.
    An empty process-environment value must not shadow a valid file value;
    a non-empty process value always wins.
    """
    try:
        text = env_file.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1].strip()
        if not key:
            continue
        if key == "MODEL_API_KEY":
            if not os.environ.get(key, "").strip():
                os.environ[key] = value
        else:
            os.environ.setdefault(key, value)
    return True


def bootstrap_env(key_required: bool) -> None:
    if not os.environ.get("MODEL_API_KEY", "").strip():
        env_file = BENCH_DIR.parent / ".env"
        if env_file.exists():
            _load_env_file(env_file)
    if key_required and not os.environ.get("MODEL_API_KEY", "").strip():
        sys.exit(
            "BLOCKED: MODEL_API_KEY (Meta Model API) is not configured in the "
            "existing environment configuration (process env or "
            "model_autopsy/.env). Nothing was charged, nothing measured. "
            "Configure the key and re-run.")
    if not os.environ.get("MODEL_AUTOPSY_DB_PATH", "").strip():
        tmp = tempfile.mkdtemp(prefix="ma-phase-d-")
        os.environ["MODEL_AUTOPSY_DB_PATH"] = str(Path(tmp) / "sandbox.db")


# ---------------------------------------------------------------------------
# Per-request ledger with hard caps (shared by both conditions)
# ---------------------------------------------------------------------------

def _attempts_hint(message: str) -> int | None:
    m = re.search(r"\(after (\d+) attempts\)", message or "")
    return int(m.group(1)) if m else None


def _sanitized_error(exc: BaseException) -> str:
    """Never persist provider bodies or exception text in benchmark results."""
    status = getattr(exc, "status_code", None)
    if status is not None:
        return f"provider error (HTTP {status}); body omitted"
    return f"{type(exc).__name__}; detail omitted"


def _est_cost(inp: int, out: int, cached: int) -> float:
    cached = min(max(cached, 0), max(inp, 0))
    uncached = inp - cached
    return round((cached * SPARK_PRICING_USD_PER_M["cached_input"]
                  + uncached * SPARK_PRICING_USD_PER_M["input"]
                  + out * SPARK_PRICING_USD_PER_M["output"]) / 1_000_000, 6)


class _BenchmarkCapReached(RuntimeError):
    """Raised when a hard benchmark cap would be violated by a request."""


class RequestLedger:
    """Wraps meta_client.create_response so every per-request provider fact
    (usage incl. cached tokens, latency, attempts, chain flag, condition) is
    captured exactly once. Rejected requests are recorded as failures; usage
    is never invented for them. Caps are checked before and after requests."""

    def __init__(self, caps: dict):
        self.caps = caps
        self.recorder = None  # durable per-run RunRecorder when set
        self.response_seq = 0
        self.entries: list[dict] = []
        self.total_input = 0
        self.total_output = 0
        self.total_cached = 0
        self.total_attempts = 0
        self.billed_ok = 0
        self.failed = 0
        self.consecutive_429 = 0
        self.stop_reason: str | None = None
        self.current_condition: str = ""
        self.current_run: str = ""
        self.current_turn: int = 0
        self.current_inv_id: str | None = None
        self.usage_missing_requests = 0
        self.cached_exceeds_input = 0
        self.blocked_before_request = 0
        self.last_response_id: str | None = None

    @property
    def est_cost(self) -> float:
        return _est_cost(self.total_input, self.total_output, self.total_cached)

    def attach(self, client_mod) -> None:
        original = client_mod.create_response
        ledger = self

        def wrapped(**kwargs):
            ledger._check_before_request()
            # Cap the client's own retry loop to the attempts still available,
            # so one in-flight request cannot push the total past the hard cap.
            prior_retries = getattr(client_mod, "MAX_RETRIES", None)
            if prior_retries is not None:
                remaining = self.caps["max_attempts"] - self.total_attempts
                client_mod.MAX_RETRIES = max(1, min(prior_retries, remaining))
            in_chars = len(json.dumps(kwargs.get("input_items") or [],
                                      sort_keys=True, default=str))
            t0 = time.perf_counter()
            try:
                resp = original(**kwargs)
            except Exception as exc:  # recorded, then re-raised unchanged
                ledger.total_attempts += _attempts_hint(str(exc)) or 1
                ledger.failed += 1
                if ledger.recorder is not None:
                    ledger.response_seq += 1
                    ledger.recorder.write("failed_permalink.jsonl", {
                        "run": ledger.current_run, "turn": ledger.current_turn,
                        "seq": ledger.response_seq,
                        "error": _sanitized_error(exc),
                        "chained": bool(kwargs.get("previous_response_id")),
                        "recorded_utc": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")})
                status = getattr(exc, "status_code", None)
                if status == 429:
                    # The client reports only the final status. Count its
                    # attempt hint as an upper bound on 429s in this call.
                    ledger.consecutive_429 += _attempts_hint(str(exc)) or 1
                else:
                    ledger.consecutive_429 = 0
                ledger.entries.append({
                    "run": ledger.current_run,
                    "turn": ledger.current_turn,
                    "condition": ledger.current_condition,
                    "chained": bool(kwargs.get("previous_response_id")),
                    "input_chars": in_chars, "ok": False,
                    "http_status": status,
                    "response_status": None,
                    "incomplete": False,
                    "attempts_hint": _attempts_hint(str(exc)),
                    "error_type": type(exc).__name__,
                    "latency_s": round(time.perf_counter() - t0, 3),
                    "error": _sanitized_error(exc)})
                ledger._check()
                if isinstance(exc, getattr(client_mod, "MetaUnavailable", ())):
                    # Keep production's status-based handling but never carry
                    # the provider body into the sandbox event log.
                    raise client_mod.MetaUnavailable(
                        _sanitized_error(exc), status_code=status) from None
                raise
            finally:
                if prior_retries is not None:
                    client_mod.MAX_RETRIES = prior_retries
            elapsed = round(time.perf_counter() - t0, 3)
            usage = client_mod.usage(resp) or {}
            perf = resp.get("_request_perf") or {}
            attempts = int(perf.get("attempts") or 1)
            missing_fields = [key for key in (
                "input_tokens", "output_tokens",
                "input_tokens_details.cached_tokens") if key not in usage]
            inp = int(usage.get("input_tokens") or 0)
            out = int(usage.get("output_tokens") or 0)
            cached = int(usage.get("input_tokens_details.cached_tokens") or 0)
            if missing_fields:
                ledger.usage_missing_requests += 1
            if cached > inp:
                ledger.cached_exceeds_input += 1
            status_text = str(resp.get("status") or "").strip().lower()
            details = resp.get("incomplete_details")
            incomplete_reason = (details.get("reason")
                                 if isinstance(details, dict) else None)
            ledger.entries.append({
                "run": ledger.current_run,
                "turn": ledger.current_turn,
                "condition": ledger.current_condition,
                "chained": bool(kwargs.get("previous_response_id")),
                "input_chars": in_chars, "ok": True,
                "model": resp.get("model"),
                "response_id": resp.get("id"),
                "response_status": resp.get("status"),
                "incomplete": status_text == "incomplete",
                "incomplete_reason": incomplete_reason,
                "status": resp.get("status"),
                "usage": usage or None,
                "usage_missing": not usage or bool(missing_fields),
                "usage_missing_fields": missing_fields,
                "attempts": attempts, "request_latency_s": elapsed,
                "instructions_chars": len(kwargs.get("instructions") or "")})
            ledger.total_input += inp
            ledger.total_output += out
            ledger.total_cached += cached
            ledger.total_attempts += attempts
            ledger.billed_ok += 1
            ledger.consecutive_429 = 0
            ledger.last_response_id = resp.get("id")
            if ledger.recorder is not None:
                ledger.response_seq += 1
                ledger.recorder.record_response(
                    ledger.current_run, ledger.current_turn,
                    ledger.response_seq, resp,
                    bool(kwargs.get("previous_response_id")),
                    investigation_id=ledger.current_inv_id)
                ledger.recorder.record_usage(
                    ledger.current_run, ledger.entries[-1],
                    investigation_id=ledger.current_inv_id)
            ledger._check()
            if ledger.stop_reason:
                raise _BenchmarkCapReached(ledger.stop_reason)
            return resp

        client_mod.create_response = wrapped

    def _check_before_request(self) -> None:
        """Refuse a new provider request once an existing total is at a cap."""
        if self.stop_reason:
            self.blocked_before_request += 1
            raise _BenchmarkCapReached(self.stop_reason)
        reason = None
        if self.total_attempts >= self.caps["max_attempts"]:
            reason = (f"attempt ceiling reached before request: "
                      f"{self.total_attempts} >= {self.caps['max_attempts']}")
        elif self.total_input + self.total_output >= self.caps["max_total_tokens"]:
            reason = (f"token ceiling reached before request: "
                      f"{self.total_input + self.total_output} >= "
                      f"{self.caps['max_total_tokens']}")
        elif self.est_cost >= self.caps["max_est_cost"]:
            reason = (f"estimated-cost ceiling reached before request: "
                      f"${self.est_cost} >= ${self.caps['max_est_cost']}")
        elif self.consecutive_429 >= self.caps["repeated_429_limit"]:
            reason = (f"repeated provider rate limits before request "
                      f"({self.consecutive_429} consecutive 429s)")
        if reason:
            self.stop_reason = reason
            self.blocked_before_request += 1
            raise _BenchmarkCapReached(reason)

    def _check(self) -> None:
        if self.stop_reason:
            return
        if self.total_attempts > self.caps["max_attempts"]:
            self.stop_reason = (f"attempt ceiling breach: "
                                f"{self.total_attempts} > {self.caps['max_attempts']}")
        elif self.total_input + self.total_output > self.caps["max_total_tokens"]:
            self.stop_reason = (
                f"token ceiling breach: {self.total_input + self.total_output} "
                f"> {self.caps['max_total_tokens']}")
        elif self.est_cost > self.caps["max_est_cost"]:
            self.stop_reason = (f"estimated-cost ceiling breach: "
                                f"${self.est_cost} > ${self.caps['max_est_cost']}")
        elif self.consecutive_429 >= self.caps["repeated_429_limit"]:
            self.stop_reason = (f"repeated provider rate limits "
                                f"({self.consecutive_429} consecutive 429s)")


# ---------------------------------------------------------------------------
# Per-run quality facts (all from RECORDED backend state, never model prose)
# ---------------------------------------------------------------------------

def _classify_run_outcome(*, turn1_status, turn2_status, summary_valid,
                          both_turns, incomplete_count,
                          status_unknown_count,
                          noncompleted_status_count=0) -> str:
    if incomplete_count:
        return "incomplete_provider_response"
    if noncompleted_status_count:
        return "provider_status_not_completed"
    if not both_turns or turn1_status != "ok" or turn2_status != "ok":
        return "turn_incomplete"
    if not summary_valid:
        return "invalid_summary"
    if status_unknown_count:
        return "provider_status_unknown"
    return "completed"


def _quality(session, engine, inv, condition, result1, result2, chain_used,
             request_entries=None, turn1_last_response_id=None,
             turn2_last_response_id=None):
    from model_autopsy.backend.db import Action, Event, Hypothesis
    final = result2 or result1
    summary_result = (final or {}).get("summary") or {}
    summary = summary_result.get("summary") or {}
    entries = request_entries or []
    successful = [e for e in entries if e.get("ok")]
    incomplete_entries = [e for e in successful if e.get("incomplete")]
    status_unknown = [e for e in successful if not e.get("response_status")]
    status_not_completed = [
        e for e in successful
        if e.get("response_status")
        and str(e.get("response_status")).strip().lower() != "completed"]
    usage_incomplete = [e for e in successful if e.get("usage_missing")]
    turn1_status = (result1 or {}).get("status")
    turn2_status = (result2 or {}).get("status")
    summary_valid = bool(summary_result.get("valid"))
    outcome = _classify_run_outcome(
        turn1_status=turn1_status, turn2_status=turn2_status,
        summary_valid=summary_valid, both_turns=result2 is not None,
        incomplete_count=len(incomplete_entries),
        status_unknown_count=len(status_unknown),
        noncompleted_status_count=len(status_not_completed))
    returned1 = (result1 or {}).get("response_id")
    returned2 = (result2 or {}).get("response_id")
    turn1_latest = (returned1 == turn1_last_response_id
                    if returned1 and turn1_last_response_id else None)
    turn2_latest = (returned2 == turn2_last_response_id
                    if returned2 and turn2_last_response_id else None)
    chain_latest = (chain_used == turn1_last_response_id
                    if chain_used and turn1_last_response_id else None)
    rows = (session.query(Event)
            .filter_by(investigation_id=inv.id).all())
    kinds: dict[str, int] = {}
    for e in rows:
        kinds[e.kind] = kinds.get(e.kind, 0) + 1
    actions = (session.query(Action)
               .filter_by(investigation_id=inv.id).all())
    return {
        "condition": condition,
        "context_strategy": ("full_resend" if condition == "full" else "delta"),
        "investigation_id": inv.id,
        "chain_used_for_turn2": chain_used,
        "turn1_status": turn1_status,
        "turn2_status": turn2_status,
        "run_outcome": outcome,
        "investigation_complete": outcome == "completed",
        "provider_response_statuses": [e.get("response_status")
                                       for e in successful],
        "incomplete_response_count": len(incomplete_entries),
        "incomplete_turn1": sum(1 for e in incomplete_entries
                                if e.get("turn") == 1),
        "incomplete_turn2": sum(1 for e in incomplete_entries
                                if e.get("turn") == 2),
        "provider_status_unknown_count": len(status_unknown),
        "provider_status_not_completed_count": len(status_not_completed),
        "usage_incomplete_request_count": len(usage_incomplete),
        "summary_repair_used_turn1":
            ((result1 or {}).get("usage_rollup") or {}).get(
                "summary_repair_attempts", 0),
        "summary_repair_used_turn2":
            ((result2 or {}).get("usage_rollup") or {}).get(
                "summary_repair_attempts", 0),
        "turn1_continuation_state": (result1 or {}).get("continuation_state"),
        "turn2_continuation_state": (result2 or {}).get("continuation_state"),
        "turn1_returned_response_id_is_latest": turn1_latest,
        "turn2_returned_response_id_is_latest": turn2_latest,
        "chain_used_is_latest_turn1_response": chain_latest,
        "summary_valid": summary_result.get("valid"),
        "summary_errors": summary_result.get("errors") or [],
        "conclusion": summary.get("conclusion"),
        "tool_calls_turn1": {
            "executed": (result1.get("usage_rollup") or {}).get("tool_calls_executed"),
            "reused": (result1.get("usage_rollup") or {}).get("tool_calls_reused"),
            "context_mode": (result1.get("usage_rollup") or {}).get("context_mode")},
        "tool_calls_turn2": {
            "executed": ((result2 or {}).get("usage_rollup") or {}).get("tool_calls_executed"),
            "reused": ((result2 or {}).get("usage_rollup") or {}).get("tool_calls_reused"),
            "context_mode": ((result2 or {}).get("usage_rollup") or {}).get("context_mode"),
            "fallback_used": ((result2 or {}).get("usage_rollup") or {}).get("fallback_used"),
            "latency_s": ((result2 or {}).get("usage_rollup") or {}).get("latency_s"),
            "api_attempts": ((result2 or {}).get("usage_rollup") or {}).get("api_attempts")},
        "event_kinds": kinds,
        "fallback_events": sum(1 for e in rows
                               if "fallback" in str(e.title or "").lower()),
        "actions": {"ran": sorted({a.tool_name for a in actions
                                   if a.status == "ran"}),
                    "ran_count": len([a for a in actions if a.status == "ran"]),
                    "failed": sorted({a.tool_name for a in actions
                                      if a.status == "failed"})},
        "hypothesis_statuses": [h.status for h in
                                (session.query(Hypothesis)
                                 .filter(Hypothesis.investigation_id == inv.id)
                                 .all())],
        "final_message_head": ((final or {}).get("message_text") or "")[:400],
    }


def _baseline_supersession_sizes(engine, meta_loop, session, inv) -> dict:
    full = json.dumps(meta_loop._initial_context_items(session, inv)[0]["content"],
                      sort_keys=True)
    delta = json.dumps(meta_loop._continuation_delta_items(session, inv)[0]["content"],
                       sort_keys=True)
    return {"full_context_chars": len(full), "delta_chars": len(delta),
            "delta_is_smaller": len(delta) < len(full)}


# ---------------------------------------------------------------------------
# Benchmark driver
# ---------------------------------------------------------------------------

def _setup_imports():
    from model_autopsy.backend import engine, config
    from model_autopsy.backend.db import SessionLocal, init_db
    from model_autopsy.backend.meta_api import client as meta_client
    from model_autopsy.backend.meta_api import loop as meta_loop
    return engine, meta_client, meta_loop, config, SessionLocal, init_db


def _new_sandbox_session():
    """Create a fresh SQLite database for exactly one benchmark run."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from model_autopsy.backend.db import Base

    run_dir = Path(tempfile.mkdtemp(prefix="ma-phase-d-run-"))
    run_engine = create_engine(
        f"sqlite:///{run_dir / 'sandbox.db'}",
        connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(run_engine)
    session = sessionmaker(
        bind=run_engine, autoflush=False, expire_on_commit=False)()
    return session, run_engine, run_dir


def run_offline() -> str:
    bootstrap_env(key_required=False)
    engine, meta_client, meta_loop, config, SessionLocal, init_db = _setup_imports()
    init_db()
    session = SessionLocal()
    try:
        inv = engine.create_investigation(
            session, "ml", "phase-d-offline-size-check", OBJECTIVE,
            dict(RUN_CFG))
        engine.build_context(session, inv)
        sizes = _baseline_supersession_sizes(engine, meta_loop, session, inv)
        patched = json.dumps(
            meta_loop._initial_context_items(session, inv)[0]["content"],
            sort_keys=True)
        original = meta_loop._continuation_delta_items
        meta_loop._continuation_delta_items = (
            lambda s, i: meta_loop._initial_context_items(s, i))
        try:
            baseline_reconstruction = json.dumps(
                meta_loop._continuation_delta_items(session, inv)[0]["content"],
                sort_keys=True)
        finally:
            meta_loop._continuation_delta_items = original
        result = {
            "mode": "offline",
            "sandbox_db": os.environ.get("MODEL_AUTOPSY_DB_PATH"),
            "payload_sizes": sizes,
            "baseline_patch_exact": (baseline_reconstruction == patched),
            "note": ("character sizes are not token counts; provider-reported "
                     "tokens require the capped live mode"),
        }
        meta_client_ref = meta_client  # noqa: F841 (import parity with live mode)
        config_model = config.meta_model_id()
        result["provider"] = {"base_url": config.meta_base_url(),
                              "model_id": config_model,
                              "key_available": bool(config.meta_api_key())}
        session.commit()
        return json.dumps(result, indent=2)
    finally:
        # New rows are transparent only to the sandbox DB, never to the live
        # application database.
        session.close()


def run_live(args) -> str:
    _validate_caps(args)
    bootstrap_env(key_required=True)
    caps = {"max_attempts": args.max_attempts,
            "max_total_tokens": args.max_total_tokens,
            "max_est_cost": args.max_est_cost,
            "repeated_429_limit": args.repeated_429_limit}
    engine, meta_client, meta_loop, config, _SessionLocal, _init_db = _setup_imports()
    client_defaults = dict(
        getattr(meta_client.create_response, "__kwdefaults__", {}) or {})

    campaign_dir = CAMPAIGN_ROOT / (
        "phase_d_meta_live_" + datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"))
    if campaign_dir.exists():
        campaign_dir = Path(str(campaign_dir) + "-2")
    if campaign_dir.exists():
        sys.exit("BLOCKED: campaign dir already exists; refusing to overwrite "
                 "existing evidence. Change --campaign-name.")
    campaign_dir.mkdir(parents=True, exist_ok=False)

    # Phase-2 crash recovery: mark any previous unfinished campaign's partial
    # runs before starting new work. Nothing is deleted; partial evidence is
    # preserved verbatim under a recovery manifest.
    recovered = recover_incomplete_runs(CAMPAIGN_ROOT)

    ledger = RequestLedger(caps)
    ledger.attach(meta_client)   # wraps BOTH conditions once, per-call-tagged

    runs: list[dict] = []
    run_db_paths: list[str] = []
    for pair in range(1, args.pairs + 1):
        for condition in ("full", "delta"):
            if ledger.stop_reason:
                runs.append({"pair": pair, "condition": condition,
                             "status": "skipped_cap",
                             "stop_reason": ledger.stop_reason})
                continue
            ledger.current_condition = condition
            ledger.current_run = f"p{pair}-{condition}"
            ledger.current_turn = 0
            ledger.current_inv_id = None
            entry_start = len(ledger.entries)
            ledger.response_seq = 0
            baseline_patch = condition == "full"
            original_delta_items = meta_loop._continuation_delta_items
            if baseline_patch:
                meta_loop._continuation_delta_items = (
                    lambda s, i: meta_loop._initial_context_items(s, i))
            result1 = None
            result2 = None
            chain_used = None
            chain1 = None
            turn1_last_id = None
            turn2_last_id = None
            session = None
            run_engine = None
            run_dir = None
            recorder = None
            finalize_manifest = None
            try:
                session, run_engine, run_dir = _new_sandbox_session()
                run_db_paths.append(str(run_dir / "sandbox.db"))
                ledger.recorder = recorder = RunRecorder(
                    campaign_dir, "run-" + run_dir.name.replace("ma-phase-d-run-", ""))
                inv = engine.create_investigation(
                    session, "ml", f"phase-d-p{pair}-{condition}",
                    OBJECTIVE, dict(RUN_CFG))
                engine.build_context(session, inv)
                ledger.current_inv_id = inv.id
                ledger.current_turn = 1
                ledger.last_response_id = None
                result1 = meta_loop.run_meta_turn(
                    session, inv, max_rounds=TURN_ROUNDS)
                turn1_last_id = ledger.last_response_id
                # Production now returns the repaired response id when a
                # summary repair succeeded (protocol revision v2); the latest
                # id check above records whether the chain honoured it.
                chain1 = result1.get("response_id")
                recorder.record_assistant(
                    ledger.current_run, 1, -1,
                    (result1 or {}).get("message_text") or "",
                    (result1 or {}).get("response_id"),
                    (result1 or {}).get("status"),
                    investigation_id=inv.id)
                session.commit()
                if ledger.stop_reason is None and chain1:
                    chain_used = str(chain1)
                    ledger.current_turn = 2
                    ledger.last_response_id = None
                    result2 = meta_loop.run_meta_turn(
                        session, inv, max_rounds=TURN_ROUNDS,
                        previous_response_id=chain_used)
                    turn2_last_id = ledger.last_response_id
                    recorder.record_assistant(
                        ledger.current_run, 2, -1,
                        (result2 or {}).get("message_text") or "",
                        (result2 or {}).get("response_id"),
                        (result2 or {}).get("status"),
                        investigation_id=inv.id)
                session.commit()
                run_entries = ledger.entries[entry_start:]
                quality = _quality(
                    session, engine, inv, condition,
                    result1, result2, chain_used,
                    request_entries=run_entries,
                    turn1_last_response_id=turn1_last_id,
                    turn2_last_response_id=turn2_last_id)
                # ---- Phase-2 durable repair-record + final DB copy ----
                for turn_no, result in ((1, result1), (2, result2)):
                    for repair in (result or {}).get("repairs") or []:
                        recorder.record_repair(ledger.current_run, turn_no,
                                               repair,
                                               investigation_id=inv.id)
                recorder.dump_investigation(session, inv.id, engine, None)
                recorder.dump_sandbox_db(run_dir / "sandbox.db")
                recorder.context_items["outcome"] = quality.get("run_outcome")
                final_outcome = {
                    "run_outcome": quality.get("run_outcome"),
                    "summary_valid": quality.get("summary_valid"),
                    "final_message_head": quality.get("final_message_head"),
                    "repair_attempted": any(
                        (r or {}).get("repairs")
                        for r in (result1, result2)),
                }
                ledger.recorder.status = "finalized"
                finalize_manifest = ledger.recorder.finalize(
                    run=ledger.current_run,
                    campaign=campaign_dir.name,
                    outcome=final_outcome)
                quality["preservation"] = {
                    "manifest": finalize_manifest.get("status"),
                    "required_evidence_present": finalize_manifest.get(
                        "required_evidence_present"),
                    "artifacts": sorted(
                        finalize_manifest.get("artifacts") or {}),
                    "finalized_utc": finalize_manifest.get("finalized_utc"),
                    "run_dir": str(recorder.dir),
                }
                runs.append(quality)
            except _BenchmarkCapReached as exc:
                if session is not None:
                    session.rollback()
                if ledger.stop_reason is None:
                    ledger.stop_reason = str(exc)
                if recorder is not None:
                    recorder.status = "interrupted"
                    finalize_manifest = recorder.finalize(
                        run=ledger.current_run,
                        campaign=campaign_dir.name,
                        outcome={}, reason=f"cap reached: {exc}")
                runs.append({
                    "pair": pair, "condition": condition,
                    "status": "stopped_cap",
                    "stop_reason": str(exc),
                    "turn1_status": (result1 or {}).get("status"),
                    "chain_used_for_turn2": chain_used,
                    "preservation": finalize_manifest})
            except Exception as exc:  # Phase-2 R4/R5: any unexpected failure
                # preserves the partial state already on disk and marks the
                # run interrupted with an explicit reason instead of losing
                # the evidence or crashing the campaign. The next recovery
                # scan finds an explicit manifest, never a silent leftover.
                if session is not None:
                    session.rollback()
                if recorder is not None:
                    if recorder.status == "in_progress":
                        recorder.status = "interrupted"
                    finalize_manifest = recorder.finalize(
                        run=ledger.current_run,
                        campaign=campaign_dir.name,
                        outcome={},
                        reason=(f"run failed: {type(exc).__name__}: "
                                f"{str(exc)[:150]}"))
                runs.append({
                    "pair": pair, "condition": condition,
                    "status": (f"failed: {type(exc).__name__}: "
                               f"{str(exc)[:200]}"),
                    "turn1_status": (result1 or {}).get("status"),
                    "chain_used_for_turn2": chain_used,
                    "preservation": finalize_manifest})
            finally:
                meta_loop._continuation_delta_items = original_delta_items
                # Phase-2 R5: delete the volatile sandbox dir ONLY when the
                # durable manifest (in the campaign dir) confirms finalized
                # evidence; otherwise keep it and report explicitly.
                ledger.recorder = None
                # Release every handle the sandbox DB file before any deletion
                # attempt: on Windows an open SQLite connection blocks rmtree.
                if session is not None:
                    session.close()
                if run_engine is not None:
                    run_engine.dispose()
                if run_dir is not None:
                    manifest_path = (
                        campaign_dir / f"run-{run_dir.name.replace(
                            'ma-phase-d-run-', '')}" / "run_manifest.json"
                        if recorder is not None else None)
                    if manifest_path is not None and manifest_path.exists():
                        keep = delete_dir_after_verify(
                            run_dir, manifest_path=manifest_path,
                            reason_if_kept=("preservation incomplete "
                                            "(missing required evidence)"))
                    else:
                        keep = {"kept": True,
                                "reason": "run never finalized; "
                                          "sandbox preserved with its DB"}
                    if keep.get("kept"):
                        runs.append({"pair": pair,
                                     "condition": condition,
                                     "status": "preservation_kept_sandbox",
                                     "sandbox_dir": str(run_dir),
                                     "reason": keep.get("reason")})

    report = {
        "mode": "live_paired",
        "protocol": {"revision": "v2", "frozen": "2026-10-29",
                     "continuation_id_correction": True},
        "generated_utc":
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "campaign_dir": str(campaign_dir),
        "crash_recovery": {"scanned": True,
                           "recovered_runs": recovered,
                           "policy": "never delete; mark and preserve"},
        "preservation": {
            "mode": "durable", "recorder": "bench_persistence.RunRecorder",
            "finalized": sum(
                1 for r in runs if (r.get("preservation") or {}).get(
                    "manifest") == "finalized")},
        "sandbox_db": "per-run temporary SQLite databases",
        "sandbox_db_shared_across_runs": False,
        "sandbox_db_paths": run_db_paths,
        "run_isolation": ("one fresh sandbox SQLite database per run; "
                          "live app DB never opened"),
        "provider": {"base_url": config.meta_base_url(),
                     "model_id": config.meta_model_id()},
        "scenario": {"objective": OBJECTIVE, "run_cfg": RUN_CFG,
                     "turn_rounds": TURN_ROUNDS, "turns_per_run": TURNS_PER_RUN,
                     "temperature": client_defaults.get("temperature"),
                     "temperature_note": ("client default; identical both "
                                          "conditions"),
                     "max_output_tokens": client_defaults.get(
                         "max_output_tokens"),
                     "max_output_tokens_note": ("client default; identical "
                                                "both conditions"),
                     "summary_repair_max_output_tokens": getattr(
                         meta_loop, "_SUMMARY_REPAIR_TOKENS", None)},
        "caps": caps,
        "pre_registered_limits": PRE_REGISTERED_LIMITS,
        "pricing_estimate_source": SPARK_PRICING_USD_PER_M,
        "totals": {"billed_requests": ledger.billed_ok,
                   "failed_requests": ledger.failed,
                   "total_attempts": ledger.total_attempts,
                   "input_tokens": ledger.total_input,
                   "output_tokens": ledger.total_output,
                   "cached_input_tokens": ledger.total_cached,
                   "uncached_input_tokens": max(
                       ledger.total_input - ledger.total_cached, 0),
                   "total_provider_tokens": (ledger.total_input
                                              + ledger.total_output),
                   "usage_incomplete_requests": ledger.usage_missing_requests,
                   "token_totals_complete": ledger.usage_missing_requests == 0,
                   "cached_exceeds_input": ledger.cached_exceeds_input,
                   "blocked_before_request": ledger.blocked_before_request,
                   "incomplete_responses": sum(
                       1 for e in ledger.entries if e.get("incomplete")),
                   "estimated_cost_usd": ledger.est_cost,
                   "stop_reason": ledger.stop_reason},
        "runs": runs,
        "per_request_ledger": ledger.entries,
    }
    out_path = Path(args.out)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return json.dumps({"written": str(out_path), "summary": report["totals"],
                       "runs": runs}, indent=2, default=str)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--offline", action="store_true",
                    help="sizes only; no network, no key required")
    ap.add_argument("--pairs", type=int, default=2,
                    help="paired investigations per condition (small by design)")
    ap.add_argument("--max-attempts", type=int, default=40)
    ap.add_argument("--max-total-tokens", type=int, default=150000)
    ap.add_argument("--max-est-cost", type=float, default=1.0,
                    help="USD ceiling on the ESTIMATED cost")
    ap.add_argument("--repeated-429-limit", type=int, default=3)
    ap.add_argument("--out", default=str(BENCH_DIR / "phase_d_meta_results.json"))
    args = ap.parse_args()
    print(run_offline() if args.offline else run_live(args))


if __name__ == "__main__":
    main()
