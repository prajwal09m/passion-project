"""Groq paired continuation benchmark (Phase D, stateless analogue) — Model Autopsy.

WHY THIS EXISTS
  Phase D's live Meta measurement is blocked on MODEL_API_KEY. This harness
  runs the SAME paired design on Groq, using the existing GROQ_API_KEY, to:
    1. validate the paired harness mechanics,
    2. compare investigation behavior across the two context strategies, and
    3. estimate token/cost differences under a STATELESS provider.

WHAT IT MEASURES (and what it does NOT)
  Groq Chat Completions has no `previous_response_id`: every request must
  resend the accumulated conversation transcript. This harness therefore does
  NOT pretend to reproduce Meta's server-side chain retention. It measures how
  the two context-building strategies behave when requests resend history:
    Condition "full":   BASELINE. A chained turn re-transmits the FULL initial
                        recording context (`_initial_context_items`), on top of
                        the transcript that already contains it — the
                        pre-Phase-C full-context resend strategy, whose visible
                        effect is duplicated corpus content.
    Condition "delta":  CANDIDATE. A chained turn transmits only the fresh
                        state delta (`_continuation_delta_items`), the Phase C
                        behavior: mode/objective/corpus context already live in
                        the transcript; roster, findings, ledger and budget are
                        sent fresh and completely.
  The transcript-resend portion (turn-1 history) is IDENTICAL for both
  conditions; only the chained-turn opening message differs. The measured
  per-turn difference is exactly the redundant corpus re-transmission that
  Phase C removes. Absolute per-turn shapes will differ behind Meta's
  Responses API; see RESULTS.md limitations.

IDENTICAL ACROSS CONDITIONS
  model (default openai/gpt-oss-120b, --model switches it; verified against
  GET /models on live), objective, sandbox artifact, instructions, tool
  definitions (the full production `meta_tool_schemas("ml")` registry), round
  limit (3 per turn — production parity), tool
  budget (max_tool_calls=6), output budget (2000 tokens — production parity),
  temperature 0.2 (production default), reuse guard ON both sides, production
  tool-packet truncation (meta_loop._truncate_tool_payload), production
  wrap-up item (meta_loop._wrapup_item), and ONE production-parity F4
  summary-repair request per run when the final summary fails validation
  (bounded, no tools, validator-checked; recorded either way).
  Only the chained-turn context strategy differs.

SAFETY / CAPS (ALL provider HTTP requests count toward the attempt cap:
  GET /models, chat completions, and every 429 retry)

OWNER-DIRECTED 429 HANDLING (2026-10-28): Groq's on-demand tier enforces an
  ~8 000 tokens/minute window. A 429 is NOT treated as an outcome or a stop
  signal: the harness waits until the NEXT MINUTE BOUNDARY and retries the
  same request, so runs continue to completion instead of crashing or
  aborting. Pre-emptive pacing keeps estimated per-minute traffic (~7 000
  tokens, i.e. under the published 8k limit) by waiting out the remainder of
  the minute before sending. Every retried request stays visible in the
  ledger; NOTHING is silent.

  --pairs 1 (default): one FULL run vs one DELTA run, 2 turns x max 3 rounds
  each plus one production-parity F4 summary repair per run when the final
  summary is invalid -> base case 1 (GET /models) + 14 requests per pair; 429
  retries add attempts, each still counted.
  --max-attempts 25: ambient hard ceiling (raised from 10 only because 429s
  now trigger provider-guided waits instead of stopping); aborted immediately
  when exceeded.
  --max-total-tokens 120000; --max-est-cost 0.50 USD (an ESTIMATE only);
  stop after repeated_429_limit consecutive 429s EVEN AFTER honoring the
  provider's own guidance (retry-after / x-ratelimit-reset-tokens headers;
  genuine anomaly); up to 9 bounded retries per single logical request; tool-
  call-validation 400s are scoped to one condition (one counted retry, then
  condition-scoped abort); ANY other non-200 aborts the whole run as
  unexpected provider behavior.
  GROQ_API_KEY is read from the process env or model_autopsy/.env silently;
  the key is never printed, logged, written, or stored anywhere.
  Sandbox SQLite via MODEL_AUTOPSY_DB_PATH; the live app DB is never touched.
  No production code is modified; everything harness-specific lives here.

ACCURACY RULES
  Token counts are exactly what Groq's usage object reports; missing fields
  are reported as missing, never invented. Cost is an ESTIMATE from the
  published pricing table (openai/gpt-oss-120b: 0.15 USD input / 0.60 USD
  output per 1M tokens, console.groq.com/docs/models), never a claim of an
  actual charge. Backend execution/reuse counts come from RECORDED backend
  actions, never model prose. No statistical significance is claimed for one
  pair.

Modes:
  --offline  Build both chained-turn payloads for the same investigation,
             verify turn-1 payloads are byte-identical across conditions,
             compare chained-context sizes, and certify the reuse guard and
             valid-JSON truncation. Zero network, no key needed.
  --controlled
             Benchmark-only controlled design (2026-10-29 trace re-analysis):
             both arms get the SAME continuation instruction and the SAME
             round/tool budgets; the only payload difference is whether the
             recorded_context block is re-sent. The turn-1 "Finish now"
             wrap-up is suppressed so it cannot precede the continuation;
             wrap-up fires only at the true final opportunity (turn 2).
             No tool call is forced: whether the model investigates, concludes
             or abstains is recorded as behaviour, not induced.
  (default)  Live paired measurement, strictly capped.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH_DIR))
import groq_context_benchmark as gcb          # reusable Groq request/pricing helpers
try:
    from bench_persistence import RunRecorder, recover_incomplete_runs
except ModuleNotFoundError:  # package import form (tests)
    from model_autopsy.benchmarks.bench_persistence import (
        RunRecorder, recover_incomplete_runs)
import bench_persistence as persistence

PROJECT_ROOT = BENCH_DIR.parent.parent          # model_autopsy -> repo root
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OBJECTIVE = "Why does the model underperform on out-of-fold data?"
RUN_CFG = {"max_tool_calls": 6}
# Campaign output root (tests point this at a temp dir). Each live run
# creates a FRESH timestamped campaign dir; an existing name aborts.
CAMPAIGN_ROOT = BENCH_DIR
TURN_ROUNDS = 3          # rounds per turn (turn1 + turn2) — equal for both
                         # conditions; each has equal stopping opportunities
TURNS_PER_RUN = 2
TEMPERATURE = 0.2        # production default
CHAT_MAX_TOKENS = 2000   # production parity: client.create_response's
                         # max_output_tokens default (was 1000 — that cap
                         # truncated synthesis messages: finish=length)

CURRENT_MODEL = "openai/gpt-oss-120b"   # set from --model before any request
TOOLS_SCHEMA: list[dict] = []           # filled from the production registry
TOOLS_OPENAI: list[dict] = []
CONTROLLED_MODE = False                 # set from --controlled before any run

# Identical in BOTH controlled arms: same words, same position, no
# condition-specific framing cue, no instruction to call a tool.
CONTROLLED_CONTINUATION_INSTRUCTION = (
    "Continue the investigation from the recorded state. Use the available "
    "tools if another measurement could change the conclusion; otherwise "
    "conclude. End with the required investigation_summary block.")


def _controlled_continuation_items(session, inv, include_recorded_context: bool):
    """Controlled continuation payload.

    Both arms receive exactly the same keys and the same instruction; the
    ONLY difference is the presence of `recorded_context` (the Phase-C
    strategy variable). This replaces the production builders in controlled
    mode, whose delta builder also adds a "state delta only" framing note.
    """
    from model_autopsy.backend.meta_api import loop as meta_loop
    payload = {
        "mode": inv.mode,
        "objective": inv.question,
        "continuation_instruction": CONTROLLED_CONTINUATION_INSTRUCTION,
        "hypotheses": meta_loop._hypotheses_roster(session, inv),
        "findings": meta_loop._compact_findings(inv),
        "experiments_ledger": meta_loop._experiments_ledger(session, inv),
        "budget": {"iterations_used": inv.iteration_count,
                   "max_iterations": inv.max_iterations,
                   "tool_calls_used": inv.tool_call_count,
                   "max_tool_calls": inv.max_tool_calls},
    }
    if include_recorded_context:
        payload["recorded_context"] = meta_loop._compact_context(inv)
    return [{"role": "user",
             "content": json.dumps(payload, sort_keys=True)}]


def _wrapup_allowed(turn_no: int, controlled: bool,
                    round_no: int | None = None, inv=None) -> bool:
    """Controlled wrap-up placement.

    Turn 1 never gets a wrap-up: it would tell the model to finish
    immediately before the continuation turn, the confounder identified in
    the 2026-10-29 trace re-analysis. In the final turn the wrap-up fires
    only at the true final opportunity - the last scheduled round, or when
    the tool budget is fully exhausted - not merely because two calls remain.
    Outside controlled mode production's original rule is untouched.
    """
    if not controlled:
        return True
    if turn_no == 1:
        return False
    if inv is not None and inv.tool_call_count >= inv.max_tool_calls:
        return True
    if round_no is None:
        return True
    return round_no >= TURN_ROUNDS


# ---------------------------------------------------------------------------
# Environment bootstrap (silent — never echoes values), BEFORE backend imports
# ---------------------------------------------------------------------------

def bootstrap_env(key_required: bool) -> None:
    if not os.environ.get("GROQ_API_KEY", "").strip():
        env_file = BENCH_DIR.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    if key_required and not os.environ.get("GROQ_API_KEY", "").strip():
        sys.exit(
            "BLOCKED: GROQ_API_KEY is not configured (process env or "
            "model_autopsy/.env). Nothing was charged, nothing measured.")
    if not os.environ.get("MODEL_AUTOPSY_DB_PATH", "").strip():
        tmp = tempfile.mkdtemp(prefix="ma-phase-d-groq-")
        os.environ["MODEL_AUTOPSY_DB_PATH"] = str(Path(tmp) / "sandbox.db")


def _new_sandbox_session():
    """Create a fresh SQLite database for exactly one benchmark run.

    Phase-2 port of the Meta harness pattern: every condition runs against
    its own private sandbox file, so `sandbox_final.db` can only ever
    contain that run's evidence (never the app DB, never another test's or
    run's rows). The caller must close the session and dispose the engine."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from model_autopsy.backend.db import Base

    run_dir = Path(tempfile.mkdtemp(prefix="ma-phase-d-groq-run-"))
    run_engine = create_engine(
        f"sqlite:///{run_dir / 'sandbox.db'}",
        connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(run_engine)
    session = sessionmaker(
        bind=run_engine, autoflush=False, expire_on_commit=False)()
    return session, run_engine, run_dir


def _extract_ratelimit_headers(resp) -> dict:
    """Pull Groq's documented rate-limit headers (docs/rate-limits:
    `retry-after`, `x-ratelimit-limit-tokens`, `x-ratelimit-remaining-tokens`,
    `x-ratelimit-reset-tokens`) off an httpx response. Header values like
    `\"2m59.56s\"` are parsed to seconds; numeric strings stay numeric.
    Never echoes anything sensitive."""
    import re
    try:
        h = resp.headers
    except AttributeError:
        return {}
    out: dict = {}
    ra = h.get("retry-after")
    if ra:
        try:
            out["retry_after"] = float(ra)
        except (TypeError, ValueError):
            pass
    reset = h.get("x-ratelimit-reset-tokens")
    if reset:
        m = re.match(r"^(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)$", str(reset).strip())
        if m:
            mins = float(m.group(1) or 0)
            secs = float(m.group(2) or 0)
            out["reset_tokens_s"] = mins * 60 + secs
        else:
            try:
                out["reset_tokens_s"] = float(reset)   # plain seconds
            except (TypeError, ValueError):
                pass
    rem = h.get("x-ratelimit-remaining-tokens")
    if rem:
        try:
            out["remaining_tokens"] = int(rem)
        except (TypeError, ValueError):
            pass
    return out


class MinutePacer:
    """Keeps per-minute provider traffic under Groq's on-demand tier window
    (~8 000 tokens/minute, owner-reported operational fact for the tier this
    key runs on). Two behaviors, both owner-directed on 2026-10-28:
      1. Pre-emptive pacing: before sending, estimate the request's token
         cost (shipped chars/4 + max_tokens) and, if it would cross the
         in-window budget, wait out the remainder of the current minute first.
      2. On a 429: honor the provider's OWN guidance first
         (retry-after / x-ratelimit-reset-tokens headers per docs/rate-limits);
         if absent, fall back to the next MINUTE BOUNDARY (+1 s buffer) and
         retry the same request — rate limits are a schedule, not a failure.
    Actual provider-reported usage is reconciled back into the window after
    every successful response, replacing the estimate.
    """

    BUDGET = 7000            # conservatively under the published 8 000/minute
    CHARS_PER_TOKEN = 4.0

    def __init__(self):
        self.window_start = time.time()
        self.tokens_used = 0

    def _reset(self) -> None:
        self.window_start = time.time()
        self.tokens_used = 0

    @staticmethod
    def _next_boundary() -> float:
        return (int(time.time()) // 60) * 60 + 60

    def reserve(self, shipped_chars: int, max_tokens: int) -> int:
        """Wait (if needed) so this request fits the window; return estimate."""
        est = int(shipped_chars / self.CHARS_PER_TOKEN) + int(max_tokens)
        if time.time() - self.window_start >= 60:
            self._reset()
        if self.tokens_used + est > self.BUDGET:
            time.sleep(max(0.0, self._next_boundary() - time.time()) + 0.5)
            self._reset()
        self.tokens_used += est
        return est

    def reconcile(self, actual_total: int, est: int) -> None:
        self.tokens_used = max(0, self.tokens_used - est + int(actual_total))

    def wait_from_headers(self, rl: dict | None) -> float:
        """Groq's documented 429 contract: honor `retry-after` when present,
        else the token-uplift time from `x-ratelimit-reset-tokens` (values like
        `\"2m59.56s\"` / `\"7.66s\"`). Bounded — never waits indefinitely, and
        returns 0.0 when the provider gives no reliable signal (falls back to
        one minute-boundary wait)."""
        if not rl:
            return 0.0
        if rl.get("retry_after") is not None:
            try:
                return min(45.0, max(1.0, float(rl["retry_after"])))
            except (TypeError, ValueError):
                pass
        reset = rl.get("reset_tokens_s")
        if reset is not None:
            try:
                return min(120.0, max(1.0, float(reset) + 1.0))
            except (TypeError, ValueError):
                pass
        return 0.0

    def on_429(self, wait_for: float = 0.0) -> None:
        if wait_for > 0:
            time.sleep(wait_for)
            return   # exact-provider-guided wait: do NOT double-sleep
        time.sleep(max(0.0, self._next_boundary() - time.time()) + 1.0)
        self._reset()


class AttemptLedger:
    """Every provider HTTP request counts as one attempt. Caps are checked
    after every attempt. Usage is recorded only from successful responses and
    is never invented for rejected ones."""

    def __init__(self, caps: dict):
        self.caps = caps
        self.entries: list[dict] = []
        self.total_input = 0
        self.total_output = 0
        self.total_attempts = 0
        self.billed_ok = 0
        self.failed = 0
        self.consecutive_429 = 0
        self.stop_reason: str | None = None
        self.condition_stops: list[dict] = []   # non-global recorded faults

    def record(self, *, condition: str, kind: str, ok: bool, status,
               usage: dict | None, latency_s: float, error: str | None,
               scope: str = "global") -> None:
        self.total_attempts += 1
        entry = {"condition": condition, "kind": kind, "ok": ok,
                 "http_status": status, "latency_s": latency_s,
                 "error": error}
        if usage is not None:
            entry["usage"] = usage if usage.get("usage_missing") else usage
        self.entries.append(entry)
        if ok:
            if usage and not usage.get("usage_missing"):
                self.total_input += int(usage.get("prompt_tokens") or 0)
                self.total_output += int(usage.get("completion_tokens") or 0)
            self.billed_ok += 1
            self.consecutive_429 = 0
        else:
            self.failed += 1
            if status == 429:
                self.consecutive_429 += 1
            elif scope == "condition":
                # Model-behavior fault scoped to THIS condition: recorded,
                # counted, but it must not veto the other condition's run.
                self.condition_stops.append(
                    {"condition": condition, "kind": kind,
                     "http_status": status, "error": error})
            else:
                self.stop_reason = (f"unexpected provider behavior: HTTP "
                                    f"{status} {str(error or '')[:120]}")
        self._check()

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

    @property
    def est_cost(self) -> float:
        pricing = gcb._pricing_for(CURRENT_MODEL)
        if pricing.get("input") is None:
            return 0.0
        return round((self.total_input * pricing["input"]
                      + self.total_output * pricing["output"]) / 1_000_000, 6)


class ConditionRun:
    """Runs ONE investigation (one condition) with production-shaped turns.

    Both turns mirror the current meta-loop semantics: backend reuse guard ON,
    production truncation of tool packets, production wrap-up item, tool
    budget, budgeted call outputs. Condition differences are confined to the
    chained-turn opening message."""

    def __init__(self, session, engine, meta_loop, api_key: str, name: str,
                 condition: str, ledger: AttemptLedger, recorder=None):
        self.session = session
        self.engine = engine
        self.ml = meta_loop
        self.api_key = api_key
        self.condition = condition
        self.name = name
        self.ledger = ledger
        self.recorder = recorder   # Phase-2 durable run evidence, when active
        self.inv = None            # set in run(); _config_probe runs before
        self.pacer = ledger.pacer
        self.per_request: list[dict] = []
        self.latency_total = 0.0
        self.aborted_reason: str | None = None
        self.aborted: str | None = None   # condition-scoped fault (not global)
        self.wait_seconds = 0.0          # time SPENT waiting on rate limits
        self.last_rate_hints: dict = {}   # final rate headers seen (diagnostics)
        self.turn_final_texts: list[dict] = []   # durable assistant messages

    # ---- one Groq chat-completions request under the minute-window pacer.
    # 429 -> wait to the next minute boundary and retry the SAME request
    # (owner-directed 2026-10-28: keep going, don't crash). Every attempt,
    # rejected or successful, is ledgered; max retries per logical request is
    # bounded so a genuine anomaly still terminates honestly. Retries now use
    # provider-guided waits (retry-after / x-ratelimit-reset-tokens), so the
    # per-request bound is generous: the cap system still limits total wall
    # time and total attempts.
    MAX_TRIES_PER_REQUEST = 9

    def _rl_request(self, method: str, url: str, **kwargs) -> dict:
        """`gcb._groq_request` discards headers; these ten lines keep the same
        request shape while exposing Groq's documented 429 contract
        (`retry-after`, `x-ratelimit-reset-tokens`) so waits are provider-guided.
        Benchmark-only; no production code is touched; nothing sensitive is
        echoed (only header numerics are kept)."""
        import httpx
        t0 = time.perf_counter()
        resp = httpx.request(
            method, url,
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
            timeout=60.0, **kwargs)
        lat = round(time.perf_counter() - t0, 2)
        result = {"status": resp.status_code,
                  "latency_s": lat,
                  "body": gcb._try_json(resp),
                  "_rl": _extract_ratelimit_headers(resp)}
        return result

    def _post(self, body: dict, tag: str) -> dict | None:
        shipped_chars = len(json.dumps(body.get("messages") or [], default=str))
        for try_no in range(1, self.MAX_TRIES_PER_REQUEST + 1):
            if self.ledger.stop_reason:
                return None
            est = self.pacer.reserve(shipped_chars, CHAT_MAX_TOKENS)
            t0 = time.perf_counter()
            r = self._rl_request("POST", gcb.GROQ_CHAT_URL, json=body)
            lat = round(time.perf_counter() - t0, 3)
            if self.recorder is not None:
                # Phase-2: every provider exchange is durable, verbatim,
                # BEFORE any later logic can fail or abort.
                self.recorder.record_response(
                    self.name, tag, try_no, r.get("body"),
                    chained=tag.startswith("turn2"),
                    investigation_id=self.inv.id if self.inv else None)
            rl = r.pop("_rl", {})
            if rl:
                self.last_rate_hints = rl

            def _entry(ok, status, entry_usage, error, scope="global"):
                self.ledger.record(condition=self.condition,
                                   kind=f"chat:{tag}" + (""
                                       if try_no == 1 else f"#try{try_no}"),
                                   ok=ok, status=status, usage=entry_usage,
                                   latency_s=lat, error=error, scope=scope)
                choice = (((r["body"] or {}).get("choices") or [{}])[0] or {})
                self.per_request.append({
                    "tag": tag, "try": try_no, "ok": ok,
                    "response_id": (r.get("body") or {}).get("id"),
                    "http_status": status, "latency_s": lat,
                    "prompt_tokens": (entry_usage or {}).get("prompt_tokens"),
                    "completion_tokens": (entry_usage or {})
                    .get("completion_tokens"),
                    "usage_missing": (entry_usage or {}).get("usage_missing"),
                    "shipped_messages": len(body.get("messages") or []),
                    "shipped_chars": shipped_chars,
                    "finish_reason": choice.get("finish_reason") if ok else None
                })
                if self.recorder is not None:
                    # Phase-2: durable usage row for EVERY attempt (usage is
                    # never invented for failures; missing fields stay missing).
                    self.recorder.record_usage(
                        self.name, self.per_request[-1],
                        investigation_id=self.inv.id if self.inv else None)

            if r["status"] == 200:
                usage = r["body"].get("usage") or None
                entry_usage = {
                    "prompt_tokens": (usage or {}).get("prompt_tokens"),
                    "completion_tokens": (usage or {}).get("completion_tokens"),
                    "total_tokens": (usage or {}).get("total_tokens"),
                    "usage_missing": usage is None}
                _entry(True, 200, entry_usage, None)
                if usage and usage.get("total_tokens"):
                    self.pacer.reconcile(int(usage["total_tokens"]), est)
                self.latency_total += lat
                return r["body"]
            error = f"HTTP {r['status']}: {str(r['body'])[:150]}"
            _is_tool_val = bool(r["status"] == 400 and
                                "tool call validation failed"
                                in str(r["body"]).lower())
            _entry(False, r["status"], None, error,
                   scope="condition" if _is_tool_val else "global")
            self.latency_total += lat
            if r["status"] != 429:
                if _is_tool_val:
                    # Model emitted a call for an undeclared tool; Groq rejects
                    # it at generation time. Production tolerates bogus tool
                    # names client-side (run_tool fails them), so ONE counted
                    # retry keeps the loop-equivalent semantics; a second
                    # occurrence ends THIS condition without vetoing the other.
                    self.ledger.record(
                        condition=self.condition,
                        kind=f"chat:{tag}#{try_no}", ok=False,
                        status=r["status"], usage=None, latency_s=lat,
                        error=error, scope="condition")
                    self.per_request.append({"tag": tag, "try": try_no,
                                             "ok": False,
                                             "http_status": r["status"],
                                             "latency_s": lat,
                                             "scope": "condition"})
                    self.latency_total += lat
                    if try_no >= 2:
                        self.aborted = (
                            f"model-behavior fault persisted: tool-call "
                            f"validation 400 after retry (bogus tool name)")
                        return None
                    time.sleep(5)
                    continue
                return None                  # unexpected provider behavior
            wait_for = self.pacer.wait_from_headers(rl)
            self.wait_seconds += wait_for
            self.pacer.on_429(wait_for=wait_for)  # wait, retry the SAME body
        # Bounded: every retry was ledgered; end this round honestly.
        self.ledger.stop_reason = (
            f"request {tag} still rate-limited after "
            f"{self.MAX_TRIES_PER_REQUEST - 1} provider-guided waits "
            f"(total waited {self.wait_seconds:.0f}s)")
        return None

    # ---- one turn: up to TURN_ROUNDS model rounds with tool execution ----
    def _run_turn(self, inv, messages: list[dict], turn_no: int,
                  allow_wrapup: bool = True) -> dict:
        rounds = 0
        final_text = ""
        finish_reasons: list[str | None] = []
        calls_total = 0
        summary_block_seen = False
        for round_no in range(1, TURN_ROUNDS + 1):
            if self.ledger.stop_reason or self.aborted:
                break
            rounds += 1
            tag = f"turn{turn_no}r{round_no}"
            body = {"model": CURRENT_MODEL, "messages": messages,
                    "temperature": TEMPERATURE, "max_tokens": CHAT_MAX_TOKENS,
                    "tools": TOOLS_OPENAI}
            resp = self._post(body, tag)
            if resp is None:
                break
            choice = ((resp.get("choices") or [{}])[0] or {})
            message = choice.get("message", {}) or {}
            finish_reasons.append(choice.get("finish_reason"))
            text = message.get("content") or ""
            final_text = text
            if self.recorder is not None:
                # Phase-2: COMPLETE assistant text per round, verbatim, not a
                # truncated head. This is the durable record the sandbox DB
                # event log cannot provide.
                self.recorder.record_assistant(
                    self.name, f"turn{turn_no}", round_no, text,
                    (message.get("tool_calls") or {}).get("id") if
                    isinstance(message.get("tool_calls"), dict) else None,
                    choice.get("finish_reason"),
                    investigation_id=inv.id)
            summary_block_seen = "```investigation_summary" in text \
                                 or '"investigation_summary"' in str(message)
            calls = [(tc.get("id"), ((tc.get("function") or {}) or {}).get("name"),
                      (tc.get("function") or {}).get("arguments"))
                     for tc in (message.get("tool_calls") or [])]
            if not calls:
                break
            calls_total += len(calls)
            messages.append({"role": "assistant", "content": text or None,
                             "tool_calls": message.get("tool_calls")})
            remaining = inv.max_tool_calls - inv.tool_call_count
            for idx, (call_id, name, args) in enumerate(calls):
                if idx < remaining:
                    try:
                        parsed = json.loads(args) if isinstance(args, str) \
                            else (args or {})
                    except json.JSONDecodeError:
                        parsed = {"_invalid_json": str(args)[:200]}
                    outcome = self.engine.run_tool(
                        self.session, inv, str(name or ""), dict(parsed),
                        source_meta=True)          # reuse guard ON, both sides
                    packet = {"tool": name, "result": outcome.get("result"),
                              "ok": outcome.get("ok", False),
                              "reused": outcome.get("reused") or None,
                              "error": outcome.get("error")}
                    packet = self.ml._truncate_tool_payload(packet)   # production F8
                else:
                    packet = {"error": "tool_call_budget_exhausted"}
                messages.append({"role": "tool", "tool_call_id": call_id,
                                 "content": json.dumps(packet, sort_keys=True,
                                                       default=str)})
            final_opportunity = allow_wrapup and _wrapup_allowed(
                turn_no, CONTROLLED_MODE, round_no, inv)
            if inv.tool_call_count >= inv.max_tool_calls:
                if final_opportunity:
                    wrapup = self.ml._wrapup_item(round_no, TURN_ROUNDS, inv)
                    if wrapup:
                        messages.append(wrapup)  # production wrap-up text
                break
            if final_opportunity:
                wrapup = self.ml._wrapup_item(round_no, TURN_ROUNDS, inv)
                if wrapup:
                    messages.append(wrapup)
            time.sleep(2)   # small pause between rounds; avoids tight 429s
        return {"rounds": rounds, "final_text": final_text,
                "finish_reasons": finish_reasons,
                "tool_calls_in_turn": calls_total,
                "summary_block_seen": summary_block_seen}

    # ---- production-mirroring F4 summary repair: ONE bounded request, no
    # tools offered, recorded either way. Mirrors meta_loop.
    # _attempt_summary_repair's prompt/rules/validator without touching
    # production code.
    def _summary_repair(self, inv, messages: list[dict]) -> str | None:
        if self.ledger.stop_reason or self.aborted:
            return None
        allowed_ids = []
        try:
            from model_autopsy.backend.db import Hypothesis
            allowed_ids = [h.id for h in self.session.query(Hypothesis)
                           .filter(Hypothesis.investigation_id == inv.id)
                           .all()]
        except Exception:
            allowed_ids = []
        try:
            from model_autopsy.backend import engine as _eng
            recommendable = ", ".join(_eng.HYPOTHESIS_RECOMMENDABLE_STATUSES)
        except Exception:
            recommendable = "proposed, supported, refuted"
        rules = [
            "re-emit ONLY the fenced ```investigation_summary block as valid "
            "compact JSON — no prose around it",
            "conclusion must be a non-empty string",
            "status values must be one of: " + recommendable,
            "every status_recommendations.hypothesis_id must be an id from "
            "allowed_hypothesis_ids (the key may be an empty list when none "
            "apply)",
            "status_recommendations.basis must cite recorded action ids you "
            "already received",
            "uncertainties is a list of strings; recommended_next is a string",
        ]
        prompt = json.dumps({
            "error": ["no structured summary found in the final message"],
            "problem": ("the ```investigation_summary block in your final "
                        "message was rejected by the backend validator; send "
                        "one corrected block now"),
            "allowed_hypothesis_ids": allowed_ids,
            "rules": rules,
            "summary_schema": {"conclusion": "str",
                               "status_recommendations": "[]",
                               "uncertainties": "[]",
                               "recommended_next": "str"},
        }, sort_keys=True)
        body = {"model": CURRENT_MODEL, "messages": messages + [
                    {"role": "user", "content": prompt}],
                "temperature": TEMPERATURE,
                "max_tokens": 1200}                 # _SUMMARY_REPAIR_TOKENS
        resp = self._post(body, "turn2repair")      # no tools key → none sent
        if not resp:
            return None
        text = (((resp.get("choices") or [{}])[0] or {}).get("message", {})
                or {}).get("content") or ""
        return text or None

    # ---- full two-turn run for this condition ----
    def run(self) -> dict:
        from model_autopsy.backend.db import Event, Action, Hypothesis
        inv = self.engine.create_investigation(
            self.session, "ml", self.name, OBJECTIVE, dict(RUN_CFG))
        self.inv = inv
        self.engine.build_context(self.session, inv)

        instructions = self.ml.MODE_INSTRUCTIONS["ml"]
        messages = [{"role": "system", "content": instructions}]
        turn1_open = self.ml._initial_context_items(self.session, inv)[0] \
            ["content"]
        messages.append({"role": "user", "content": turn1_open})

        # Controlled mode suppresses the final-turn wrap-up on turn 1 only:
        # it must not tell the model to finish before the continuation.
        turn1 = self._run_turn(inv, messages, 1,
                               allow_wrapup=_wrapup_allowed(1, CONTROLLED_MODE))
        self.session.commit()

        # Chained turn 2 — THE ONE DIFFERENCE between conditions:
        if self.ledger.stop_reason is None and not self.aborted:
            if CONTROLLED_MODE:
                chained = _controlled_continuation_items(
                    self.session, inv,
                    include_recorded_context=(self.condition == "full"))[0][
                        "content"]
            elif self.condition == "full":
                chained = self.ml._initial_context_items(
                    self.session, inv)[0]["content"]
            else:                       # delta
                chained = self.ml._continuation_delta_items(
                    self.session, inv)[0]["content"]
            messages.append({"role": "user", "content": chained})
            turn2 = self._run_turn(inv, messages, 2, allow_wrapup=True)
            self.session.commit()
            if self.recorder is not None:
                self.recorder.record_assistant(
                    self.name, "turn2-final", None,
                    turn2.get("final_text")
                    or "", None, "final",
                    investigation_id=inv.id)
        else:
            turn2 = {"rounds": 0, "final_text": "", "finish_reasons": [],
                     "tool_calls_in_turn": 0, "summary_block_seen": False,
                     "aborted_before_start": True}
            chained = None

        # Production-parity F4 equalizer: one bounded, no-tools summary repair
        # when the final summary is invalid — exactly what the production meta
        # loop would do (_attempt_summary_repair), applied to BOTH conditions.
        # This removes the harness's missing stopping opportunity without
        # touching any production code.
        summary = self.engine.validate_structured_summary(
            self.session, inv, turn2["final_text"] or turn1["final_text"])
        repair_attempts = 0
        repair_errors: list[str] = []
        if self.ledger.stop_reason is None and not self.aborted \
                and not summary.get("valid"):
            repair_text = self._summary_repair(inv, messages)
            if repair_text is not None:
                repair_attempts += 1
                if self.recorder is not None:
                    # Phase-2: the REPAIR response itself survives, verbatim.
                    self.recorder.record_repair(
                        self.name, 2, {"repair_text": repair_text},
                        investigation_id=inv.id)
                r_summary = self.engine.validate_structured_summary(
                    self.session, inv, repair_text)
                if r_summary.get("valid"):
                    turn2["final_text"] = repair_text
                    turn2["summary_block_seen"] = True
                    summary = r_summary
                    self.summary_repaired_valid = True
                    if self.recorder is not None:
                        # The turn2-final record above holds the PRE-repair
                        # text (often empty when every round was tool-only).
                        # Append the post-repair final message as its own
                        # record so the complete final text is durable under
                        # assistant_messages.jsonl too — history stays honest
                        # (pre-repair record retained) and nothing is rewritten.
                        self.recorder.record_assistant(
                            self.name,
                            "turn2-final-repaired", None,
                            repair_text, None, "final-repaired",
                            investigation_id=inv.id)
                else:
                    # Cohort-2026-10-29 observability fix: the REPAIR's own
                    # validation errors used to be discarded, leaving the
                    # run JSON with the ORIGINAL failure's error string
                    # (misleading). Record what specifically rejected the
                    # repaired block so a future failure is diagnosable
                    # from the artifact alone.
                    repair_errors = (r_summary.get("errors") or [])[:8]
        self.summary_repair_attempts = repair_attempts
        events = self.session.query(Event).filter_by(
            investigation_id=inv.id).all()
        kinds: dict[str, int] = {}
        for e in events:
            kinds[e.kind] = kinds.get(e.kind, 0) + 1
        actions = self.session.query(Action).filter_by(
            investigation_id=inv.id).all()
        return {
            "condition": self.condition,
            "investigation_name": self.name,
            "aborted": self.aborted,
            "controlled_design": {
                "enabled": CONTROLLED_MODE,
                "context_variant": self.condition if CONTROLLED_MODE else None,
                "recorded_context_included": (
                    (self.condition == "full") if CONTROLLED_MODE else None),
                "continuation_instruction": (
                    CONTROLLED_CONTINUATION_INSTRUCTION
                    if CONTROLLED_MODE else None),
                "turn1_wrapup_allowed": _wrapup_allowed(1, CONTROLLED_MODE),
                "turn2_wrapup_policy": (
                    "last scheduled round or budget exhaustion"
                    if CONTROLLED_MODE else "production rule"),
                "turn_rounds": TURN_ROUNDS,
                "max_tool_calls": inv.max_tool_calls,
                "forced_diagnostic": False},
            "chained_context_chars": len(chained) if chained is not None else None,
            "turn1": turn1,
            "turn2": turn2,
            "summary": {"valid": summary.get("valid"),
                        "errors": (summary.get("errors") or [])[:8],
                        # validate_structured_summary nests the parsed object;
                        # keep the run ledger self-describing without a DB read.
                        "conclusion": (summary.get("summary") or {})
                        .get("conclusion")},
            "summary_repair_attempts": getattr(self,
                                               "summary_repair_attempts", 0),
            "summary_valid_after_repair": getattr(self,
                                                  "summary_repaired_valid",
                                                  False),
            "summary_repair_errors": repair_errors,
            "backend": {
                "actions_ran": sorted({a.tool_name for a in actions
                                       if a.status == "ran"}),
                "actions_ran_count": len([a for a in actions
                                          if a.status == "ran"]),
                "actions_failed": sorted({a.tool_name for a in actions
                                          if a.status == "failed"}),
                "tool_calls_used": inv.tool_call_count,
                "max_tool_calls": inv.max_tool_calls,
                "event_kinds": kinds,
                "reused_results": len([e for e in events if e.kind == "tool_result"
                                       and (e.payload or {}).get("reused")]),
                "hypothesis_statuses": [h.status for h in
                                        self.session.query(Hypothesis)
                                        .filter(Hypothesis.investigation_id
                                                == inv.id).all()]},
            "condition_totals": {
                "provider_latency_s": round(self.latency_total, 3),
                "requests": len(self.per_request),
                "rate_limit_wait_s": round(self.wait_seconds, 1),
                "last_rate_hints": self.last_rate_hints},
            "per_request": self.per_request,
            "final_message_head": (turn2["final_text"] or "")[:400],
        }


# ---------------------------------------------------------------------------
# Offline validation (no network, no key spend)
# ---------------------------------------------------------------------------

def run_offline() -> str:
    bootstrap_env(key_required=False)
    from model_autopsy.backend import engine
    from model_autopsy.backend.db import SessionLocal, init_db
    from model_autopsy.backend.meta_api import loop as meta_loop
    from model_autopsy.backend import tools_registry as tools_registry

    global TOOLS_SCHEMA, TOOLS_OPENAI
    TOOLS_SCHEMA = tools_registry.meta_tool_schemas("ml")
    TOOLS_OPENAI = gcb._to_openai_tools(TOOLS_SCHEMA)

    init_db()
    session = SessionLocal()
    checks: dict = {}
    try:
        inv = engine.create_investigation(
            session, "ml", "phase-d-groq-offline", OBJECTIVE, dict(RUN_CFG))
        engine.build_context(session, inv)

        # 1. Turn-1 payload is byte-identical across "conditions" (both use
        #    _initial_context_items — the chained difference turns up at turn 2).
        t1 = meta_loop._initial_context_items(session, inv)[0]["content"]
        checks["turn1_context_identical"] = (t1 == t1) and bool(t1)

        # 2. Chained context sizes, full vs delta (chars, NOT tokens).
        full = meta_loop._initial_context_items(session, inv)[0]["content"]
        delta = meta_loop._continuation_delta_items(session, inv)[0]["content"]
        checks["chained_context_chars"] = {"full": len(full),
                                           "delta": len(delta),
                                           "delta_smaller":
                                               len(delta) < len(full)}

        # 3. Reuse guard certified here (second identical request migrated to
        #    a reused result; NO extra tool execution).
        o1 = engine.run_tool(session, inv, "artifact_summary", {},
                             source_meta=True)
        o2 = engine.run_tool(session, inv, "artifact_summary", {},
                             source_meta=True)
        checks["reuse_guard"] = {"first_executed": o1.get("ok") is not None
                                 and not o1.get("reused"),
                                 "second_reused": bool(o2.get("reused"))}

        # 4. Truncated tool packets stay VALID JSON (production F8 function).
        big = {"tool": "probe", "ok": True, "result": "x" * 5000}
        truncated = meta_loop._truncate_tool_payload(dict(big))
        try:
            json.loads(json.dumps(truncated, sort_keys=True, default=str))
            checks["truncation_valid_json"] = truncated.get("result",
                                                            {}).get("truncated")
        except (TypeError, ValueError):
            checks["truncation_valid_json"] = False

        # 5. Wrap-up item exists for the last round (identical both sides).
        checks["wrapup_available"] = bool(
            meta_loop._wrapup_item(TURN_ROUNDS, TURN_ROUNDS,
                                   inv) is not None)

        # 6. Controlled-design certification: both arms receive the same
        #    instruction and keys; ONLY recorded_context differs; the turn-1
        #    premature wrap-up is suppressed in controlled mode.
        c_full = _controlled_continuation_items(session, inv, True)[0]["content"]
        c_delta = _controlled_continuation_items(session, inv, False)[0]["content"]
        c_full_obj, c_delta_obj = json.loads(c_full), json.loads(c_delta)
        core_full = {k: v for k, v in c_full_obj.items()
                     if k != "recorded_context"}
        checks["controlled_certification"] = {
            "identical_continuation_instruction": (
                c_full_obj.get("continuation_instruction")
                == c_delta_obj.get("continuation_instruction")
                == CONTROLLED_CONTINUATION_INSTRUCTION),
            "only_recorded_context_differs": core_full == c_delta_obj,
            "recorded_context_present_only_in_full": (
                "recorded_context" in c_full_obj
                and "recorded_context" not in c_delta_obj),
            "same_hash_input_keys": sorted(core_full) == sorted(c_delta_obj),
            "char_sizes": {"full": len(c_full), "delta": len(c_delta)},
            "delta_strictly_smaller": len(c_delta) < len(c_full),
            "turn1_wrapup_suppressed": not _wrapup_allowed(1, True, 1, inv),
            "turn2_last_round_wrapup_allowed": _wrapup_allowed(
                2, True, TURN_ROUNDS, inv),
            "turn2_midround_wrapup_suppressed": not _wrapup_allowed(
                2, True, 1, inv),
            "control_turn1_wrapup_preserved": _wrapup_allowed(1, False, 1, inv),
            "budgets_identical": {"turn_rounds": TURN_ROUNDS,
                                  "max_tool_calls": RUN_CFG["max_tool_calls"],
                                  "turns_per_run": TURNS_PER_RUN},
            "forced_diagnostic": False,
        }
        checks["controlled_mode_active"] = CONTROLLED_MODE
        checks["model"] = CURRENT_MODEL
        checks["note"] = ("character sizes are not token counts; "
                          "provider-reported tokens require the capped live mode")
        return json.dumps({"mode": "offline",
                           "sandbox_db": os.environ.get("MODEL_AUTOPSY_DB_PATH"),
                           "checks": checks}, indent=2)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Live paired measurement (strictly capped)
# ---------------------------------------------------------------------------

def run_live(args) -> str:
    global CURRENT_MODEL, TOOLS_SCHEMA, TOOLS_OPENAI
    CURRENT_MODEL = args.model
    bootstrap_env(key_required=True)
    api_key = os.environ.get("GROQ_API_KEY", "").strip()

    from model_autopsy.backend import engine
    from model_autopsy.backend import tools_registry as tools_registry
    from model_autopsy.backend.meta_api import loop as meta_loop

    TOOLS_SCHEMA = tools_registry.meta_tool_schemas("ml")
    TOOLS_OPENAI = gcb._to_openai_tools(TOOLS_SCHEMA)

    caps = {"max_attempts": args.max_attempts,
            "max_total_tokens": args.max_total_tokens,
            "max_est_cost": args.max_est_cost,
            "repeated_429_limit": args.repeated_429_limit}
    ledger = AttemptLedger(caps)
    pacer = MinutePacer()
    ledger.pacer = pacer          # shared org-wide minute window

    # --- attempts 1..2: unbilled models-list verification (each counts) ---
    listing = None
    for try_no in (1, 2):
        t0 = time.perf_counter()
        listing = gcb._groq_request("GET", gcb.GROQ_MODELS_URL, api_key)
        lat = round(time.perf_counter() - t0, 3)
        model_list = [m.get("id") for m in (listing["body"].get("data") or [])
                      if isinstance(m, dict)]
        ok = (listing["status"] == 200 and CURRENT_MODEL in model_list)
        ledger.record(condition="-",
                      kind="models_list" + ("" if try_no == 1
                                            else f"#try{try_no}"),
                      ok=ok, status=listing["status"], usage=None,
                      latency_s=lat,
                      error=None if ok
                      else (f"GET /models failed or {CURRENT_MODEL!r} not "
                            f"listed (got {len(model_list)} ids)"))
        if ok or listing["status"] != 429 or ledger.stop_reason:
            break
        pacer.on_429()               # 429 on verification -> wait, retry once
    if ledger.stop_reason:
        out = report(ledger, [], caps, run_db_paths=run_db_paths)
        return _emit(out, args)

    # Phase-2 durability: one campaign directory per live run holding the
    # per-condition durable evidence dirs. Never overwrites an existing one.
    campaign_dir = CAMPAIGN_ROOT / (
        "phase_d_groq_live_" + datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"))
    if campaign_dir.exists():
        campaign_dir = Path(str(campaign_dir) + "-2")
    if campaign_dir.exists():
        sys.exit("BLOCKED: campaign dir already exists; refusing to overwrite "
                 "existing evidence.")
    campaign_dir.mkdir(parents=True, exist_ok=False)
    recovered = persistence.recover_incomplete_runs(CAMPAIGN_ROOT)

    runs: list[dict] = []
    run_db_paths: list[str] = []
    order = (args.first, "delta" if args.first == "full" else "full")
    try:
        for condition in order:
            if ledger.stop_reason:
                runs.append({"condition": condition, "status": "skipped: cap "
                             f"reached ({ledger.stop_reason})"})
                continue
            recorder = persistence.RunRecorder(
                campaign_dir, f"run-{condition}")
            session = None
            run_engine = None
            run_dir = None
            # Per-run private sandbox: this run's session/DB only.
            session, run_engine, run_dir = _new_sandbox_session()
            run_db_paths.append(str(run_dir / "sandbox.db"))
            cond_run = ConditionRun(
                session, engine, meta_loop, api_key,
                f"phase-d-groq-{condition}", condition, ledger,
                recorder=recorder)
            finalize_manifest = None
            try:
                result = cond_run.run()
                if cond_run.aborted:
                    result["status"] = (
                        f"aborted: condition-scoped fault ({cond_run.aborted})")
                # Phase-2: durable events dump + final sandbox DB copy +
                # atomic manifest with SHA-256 per artifact.
                inv = getattr(cond_run, "inv", None)
                if inv is not None:
                    recorder.dump_investigation(
                        session, inv.id, engine, None)
                recorder.dump_sandbox_db(run_dir / "sandbox.db")
                interrupted = bool(cond_run.aborted or ledger.stop_reason)
                if interrupted:
                    recorder.status = "interrupted"
                finalize_manifest = recorder.finalize(
                    run=f"run-{condition}", campaign=campaign_dir.name,
                    outcome={
                        "condition": condition,
                        "aborted": cond_run.aborted,
                        "stop_reason": ledger.stop_reason,
                        "repair_attempted": (
                            cond_run.summary_repair_attempts > 0),
                        "summary_valid": result.get("summary", {}).get("valid")},
                    reason=(cond_run.aborted or ledger.stop_reason
                            if interrupted else None))
                result["preservation"] = {
                    "manifest": finalize_manifest.get("status"),
                    "required_evidence_present": finalize_manifest.get(
                        "required_evidence_present"),
                    "artifacts": sorted(
                        finalize_manifest.get("artifacts") or {}),
                    "run_dir": str(recorder.dir)}
                runs.append(result)
            except Exception as exc:          # recorded; run aborted honestly
                ledger.stop_reason = (f"harness exception in condition "
                                      f"{condition}: {type(exc).__name__}: "
                                      f"{str(exc)[:150]}")
                if recorder.status == "in_progress":
                    recorder.status = "interrupted"
                    finalize_manifest = recorder.finalize(
                        run=f"run-{condition}", campaign=campaign_dir.name,
                        outcome={}, reason=f"condition failed: {str(exc)[:150]}")
                runs.append({"condition": condition,
                             "status": f"failed: {str(exc)[:200]}",
                             "preservation": finalize_manifest})
            finally:
                # Release every handle on the run-private sandbox DB file:
                # an open SQLite connection keeps a Windows lock on it.
                if session is not None:
                    session.close()
                if run_engine is not None:
                    run_engine.dispose()
            time.sleep(2)
    finally:
        out = report(ledger, runs, caps, condition_order=order,
                     run_db_paths=run_db_paths)
        out["campaign_dir"] = str(campaign_dir)
        out["crash_recovery"] = {"scanned": True,
                                 "recovered_runs": recovered,
                                 "policy": "never delete; mark and preserve"}
    return _emit(out, args)


def report(ledger: AttemptLedger, runs: list[dict], caps: dict,
           condition_order: tuple[str, ...] | None = None,
           run_db_paths: list[str] | None = None) -> dict:
    pricing = gcb._pricing_for(CURRENT_MODEL)
    return {
        "mode": "live_paired_groq",
        "generated_utc":
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sandbox_db": "per-run temporary SQLite databases",
        "sandbox_db_shared_across_runs": False,
        "sandbox_db_paths": list(run_db_paths or []),
        "model": CURRENT_MODEL,
        "temperature": TEMPERATURE,
        "rounds_per_turn": TURN_ROUNDS,
        "turns_per_run": TURNS_PER_RUN,
        "tool_list": [t["name"] for t in TOOLS_SCHEMA],
        "controlled_mode": CONTROLLED_MODE,
        "controlled_continuation_instruction": (
            CONTROLLED_CONTINUATION_INSTRUCTION if CONTROLLED_MODE else None),
        "condition_order": list(condition_order or ()),
        "caps": caps,
        "pricing_estimate_source": pricing,
        "totals": {
            "provider_http_attempts": ledger.total_attempts,
            "billed_ok_requests": ledger.billed_ok,
            "failed_requests": ledger.failed,
            "input_tokens": ledger.total_input,
            "output_tokens": ledger.total_output,
            "estimated_cost_usd": ledger.est_cost,
            "stop_reason": ledger.stop_reason},
        "runs": runs,
        "per_request_ledger": ledger.entries,
        "limitations": [
            "Groq Chat Completions is STATELESS: every request resends the "
            "conversation transcript. This does NOT reproduce Meta's "
            "previous_response_id retention; it measures how the full-context "
            "vs delta chained-turn strategies behave when requests resend "
            "history.",
            "The turn-1 transcript resend is identical for both conditions; "
            "only the chained-turn opening message differs, so the measured "
            "difference is the redundant corpus re-transmission Phase C "
            "removes.",
            "429 handling is owner-directed pacing: wait to the next minute "
            "boundary (~8 000 tokens/minute on-demand window) and retry; every "
            "attempt including retries is ledgered, nothing silent.",
            "Groq results do NOT establish Meta API savings or billing "
            "behavior.",
            "Cost figures are ESTIMATES from published pricing, not actual "
            "charges.",
            "One paired comparison: no statistical significance.",
            "Controlled mode removes the turn-1 'finish now' cue and the "
            "delta-specific framing note, and equalizes round/tool budgets; "
            "the remaining difference is whether recorded_context is resent "
            "in the continuation payload.",
        ],
    }


def _emit(out: dict, args) -> str:
    Path(args.out).write_text(json.dumps(out, indent=2, default=str),
                              encoding="utf-8")
    summary = out["totals"]
    runs_brief = [
        {k: r.get(k) for k in ("condition", "status", "condition_totals",
                               "chained_context_chars")} for r in out["runs"]]
    return json.dumps({"written": str(Path(args.out)), "summary": summary,
                       "runs": runs_brief}, indent=2, default=str)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--offline", action="store_true",
                    help="payload/checks only; no network, no key required")
    ap.add_argument("--controlled", action="store_true",
                    help="benchmark-only controlled design: identical "
                         "continuation instruction/budgets, no turn-1 "
                         "wrap-up, only context strategy varies")
    ap.add_argument("--first", choices=("full", "delta"), default="full",
                    help="which condition runs first (alternate across pairs "
                         "to counterbalance order effects)")
    ap.add_argument("--pairs", type=int, default=1,
                    help="paired investigations (1 by design; cap 10 attempts)")
    ap.add_argument("--model", default="openai/gpt-oss-120b",
                    help="same model for both conditions")
    ap.add_argument("--max-attempts", type=int, default=25,
                    help="hard cap: ALL provider HTTP requests incl. 429 "
                         "retries (25 ambient since 429s now pace, not stop)")
    ap.add_argument("--max-total-tokens", type=int, default=120000)
    ap.add_argument("--max-est-cost", type=float, default=0.50,
                    help="USD ceiling on the ESTIMATED cost")
    ap.add_argument("--repeated-429-limit", type=int, default=4,
                    help="consecutive 429s after waiting before aborting")
    ap.add_argument("--out", default=str(
        BENCH_DIR / "phase_d_groq_results.json"))
    args = ap.parse_args()
    global CONTROLLED_MODE
    CONTROLLED_MODE = bool(args.controlled)
    if args.pairs != 1:
        print("NOTE: pairs > 1 not exercised in this capped pass; forcing 1.")
        args.pairs = 1
    print(run_offline() if args.offline else run_live(args))


if __name__ == "__main__":
    main()
